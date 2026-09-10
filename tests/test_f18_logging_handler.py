"""F18：日志接入异步缓冲（业务线程不等待网络、有界队列、丢弃可观测、原始事件时间）。

用 httpx.MockTransport 注入假服务端，覆盖：异步 emit 不阻塞、批处理送达与原始
timestamp、队列满丢弃计数、网络失败不阻塞且可观测、close 排空、服务解析一次、
同步模式旧行为保留。
"""

import json
import logging
import time
from datetime import UTC, datetime

import httpx

from integrations.python_logging_handler import IncidentPlatformHandler


class _FakePlatform:
    """记录请求、可注入延迟/故障的假平台（MockTransport 处理器）。"""

    def __init__(self, service_id: int = 7, delay: float = 0.0, fail: bool = False):
        self.service_id = service_id
        self.delay = delay
        self.fail = fail
        self.posts: list[dict] = []
        self.service_gets = 0

    def handle(self, request: httpx.Request) -> httpx.Response:
        if self.delay:
            time.sleep(self.delay)
        if self.fail:
            raise httpx.ConnectError("platform down")
        if request.method == "GET":
            self.service_gets += 1
            return httpx.Response(
                200, json=[{"id": self.service_id, "name": "fake-service"}]
            )
        self.posts.append(json.loads(request.content))
        return httpx.Response(201, json={})

    def client_factory(self) -> httpx.Client:
        return httpx.Client(
            base_url="http://platform.test",
            transport=httpx.MockTransport(self.handle),
        )


def _record(message: str, created: float) -> logging.LogRecord:
    record = logging.LogRecord(
        name="test", level=logging.ERROR, pathname="", lineno=0,
        msg=message, args=(), exc_info=None,
    )
    record.created = created
    return record


def _handler(fake: _FakePlatform, **kwargs) -> IncidentPlatformHandler:
    handler = IncidentPlatformHandler(
        "http://platform.test", "fake-service", client_factory=fake.client_factory, **kwargs
    )
    handler.setFormatter(logging.Formatter("%(message)s"))
    return handler


def test_async_emit_does_not_block_caller_on_slow_platform():
    fake = _FakePlatform(delay=0.3)
    handler = _handler(fake)
    try:
        start = time.monotonic()
        for _ in range(3):
            handler.emit(_record("boom", time.time()))
        elapsed = time.monotonic() - start
        # 平台每条要 0.3s：同步发送至少 0.9s；异步 emit 只入队，应远快于网络耗时
        assert elapsed < 0.1
        handler.close()
        assert len(fake.posts) == 3
    finally:
        handler.close()


def test_async_emit_sends_original_event_time_not_receive_time():
    fake = _FakePlatform()
    handler = _handler(fake)
    try:
        event_time = datetime(2026, 6, 7, 12, 30, 0, tzinfo=UTC)
        handler.emit(_record("slow event", event_time.timestamp()))
        handler.close()
        sent = fake.posts[0]
        assert sent["level"] == "ERROR"
        assert sent["message"] == "slow event"
        assert sent["timestamp"] == event_time.isoformat()  # 原始发生时间
    finally:
        handler.close()


def test_queue_overflow_drops_with_observable_stats():
    fake = _FakePlatform(delay=0.1)  # 慢平台让队列积压
    handler = _handler(fake, queue_size=2, flush_interval=0.05)
    try:
        for index in range(5):
            handler.emit(_record(f"boom {index}", time.time()))
        stats = handler.stats()
        assert stats["mode"] == "async"
        assert stats["dropped"] >= 1  # 有界缓冲丢弃可观测（F18）
        handler.close()
    finally:
        handler.close()


def test_network_failure_does_not_block_and_is_observable():
    fake = _FakePlatform(fail=True)
    handler = _handler(fake)
    try:
        start = time.monotonic()
        for _ in range(3):
            handler.emit(_record("boom", time.time()))
        assert time.monotonic() - start < 0.1  # 平台不可用也不拖业务
        handler.close()
        stats = handler.stats()
        assert stats["sent"] == 0
        assert stats["dropped"] == 3
        assert stats["last_error"] is not None
    finally:
        handler.close()


def test_close_drains_queued_records():
    fake = _FakePlatform()
    handler = _handler(fake)
    for index in range(4):
        handler.emit(_record(f"queued {index}", time.time()))
    handler.close()
    assert len(fake.posts) == 4  # close 先排空再停
    assert handler.stats()["queued"] == 0
    assert handler._worker is None or not handler._worker.is_alive()


def test_service_resolved_once_across_batches():
    fake = _FakePlatform()
    handler = _handler(fake, batch_size=1, flush_interval=0.01)
    try:
        for index in range(3):
            handler.emit(_record(f"msg {index}", time.time()))
        deadline = time.monotonic() + 3
        while len(fake.posts) < 3 and time.monotonic() < deadline:
            time.sleep(0.02)
        handler.close()
        assert fake.service_gets == 1  # 服务 id 解析一次后缓存（连接复用批次）
        assert all(post["service_id"] == 7 for post in fake.posts)
    finally:
        handler.close()


def test_sync_mode_keeps_legacy_immediate_behavior():
    fake = _FakePlatform()
    handler = _handler(fake, async_mode=False)
    try:
        handler.emit(_record("sync message", time.time()))
        assert len(fake.posts) == 1  # 立即送达，无需 close/等待
        assert handler.stats()["mode"] == "sync"
    finally:
        handler.close()


def test_sync_mode_failure_is_swallowed_and_counted():
    fake = _FakePlatform(fail=True)
    handler = _handler(fake, async_mode=False)
    try:
        handler.emit(_record("sync failure", time.time()))  # 不抛异常
        assert handler.stats()["dropped"] == 1
        assert handler.stats()["last_error"] is not None
    finally:
        handler.close()
