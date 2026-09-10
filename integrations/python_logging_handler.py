"""Python logging handler that forwards records to the incident platform.

F18：默认异步批处理——`emit()` 只把记录放入有界队列（满则丢弃并计数），
后台单线程用复用连接发送；业务线程绝不等待网络，最坏只写内存。
同步模式（`async_mode=False`）保留旧行为（每条即时发送、网络异常吞掉），
供短生命周期 Demo 使用。

发送体带 `timestamp` = 记录原始发生时间（record.created），
平台侧 F04 会将其归一为 UTC 并与送达时间（received_at）区分。
"""

from __future__ import annotations

import logging
import queue
import threading
import time
from datetime import UTC, datetime

import httpx


class IncidentPlatformHandler(logging.Handler):
    """Forward Python log records to the platform's ``POST /logs`` endpoint.

    async_mode=True（默认，F18）：
      - emit 不阻塞调用线程（有界队列 + 后台发送线程 + 复用连接）；
      - 队列满或发送失败 → 丢弃并计数（`stats()` 可观测）；
      - `close()` 时尽量排空队列后停止发送线程。
    async_mode=False：每条同步发送，与旧版行为一致（Demo 轻量）。
    """

    def __init__(
        self,
        platform_url: str,
        service_name: str,
        *,
        timeout: float = 2.0,
        level: int = logging.NOTSET,
        async_mode: bool = True,
        queue_size: int = 1000,
        batch_size: int = 20,
        flush_interval: float = 0.5,
        client_factory: object | None = None,
    ) -> None:
        super().__init__(level=level)
        self.platform_url = platform_url.rstrip("/")
        self.service_name = service_name
        self.timeout = timeout
        self.async_mode = async_mode
        self.batch_size = max(1, batch_size)
        self.flush_interval = flush_interval
        # client_factory 供测试注入 MockTransport；生产用复用连接的默认客户端
        self._client_factory = client_factory or (
            lambda: httpx.Client(timeout=self.timeout, trust_env=False)
        )

        self._service_id: int | None = None
        self._service_lock = threading.Lock()
        self._queue: queue.Queue = queue.Queue(maxsize=queue_size)
        self._stop_event = threading.Event()
        self._worker: threading.Thread | None = None
        self._closed = False
        self._dropped = 0
        self._sent = 0
        self._last_error: str | None = None

        if async_mode:
            self._worker = threading.Thread(
                target=self._drain_loop, name="incident-log-forwarder", daemon=True
            )
            self._worker.start()

    # ── emit 路径（调用线程，只做轻活） ────────────────────────────────────────

    def emit(self, record: logging.LogRecord) -> None:
        try:
            payload = {
                "level": record.levelname,
                "message": self.format(record),
                # F18：带原始发生时间（F04 归一 UTC；服务端另记 received_at）
                "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            }
        except Exception:
            self.handleError(record)
            return

        if not self.async_mode:
            try:
                with self._make_client() as client:
                    self._send_one(client, payload)
            except Exception as exc:
                self._record_failure(str(exc))
                self.handleError(record)
            return

        try:
            self._queue.put_nowait(payload)
        except queue.Full:
            # 有界缓冲：宁可丢弃并计数，也不阻塞业务线程（F18）
            self._dropped += 1

    # ── 后台发送线程 ──────────────────────────────────────────────────────────

    def _drain_loop(self) -> None:
        client = self._make_client()
        try:
            while True:
                try:
                    payload = self._queue.get(timeout=0.2)
                except queue.Empty:
                    # 停止事件置位且队列已空 → 正常退出（close() 排空完成）
                    if self._stop_event.is_set():
                        break
                    continue
                batch = [payload]
                deadline = time.monotonic() + self.flush_interval
                while len(batch) < self.batch_size and time.monotonic() < deadline:
                    try:
                        batch.append(self._queue.get(timeout=0.1))
                    except queue.Empty:
                        break
                self._send_batch(client, batch)
                if self._stop_event.is_set() and self._queue.empty():
                    break
        finally:
            client.close()

    def _send_batch(self, client: httpx.Client, batch: list[dict]) -> None:
        for payload in batch:
            try:
                self._send_one(client, payload)
            except Exception as exc:
                self._record_failure(str(exc))

    def _send_one(self, client: httpx.Client, payload: dict) -> None:
        service_id = self._resolve_service_id(client)
        response = client.post(
            f"{self.platform_url}/logs",
            json={**payload, "service_id": service_id},
        )
        response.raise_for_status()
        self._sent += 1

    def _resolve_service_id(self, client: httpx.Client) -> int:
        if self._service_id is not None:
            return self._service_id
        with self._service_lock:
            if self._service_id is not None:
                return self._service_id
            services_response = client.get(f"{self.platform_url}/services")
            services_response.raise_for_status()
            for service in services_response.json():
                if service["name"] == self.service_name:
                    self._service_id = service["id"]
                    return self._service_id
            create_response = client.post(
                f"{self.platform_url}/services",
                json={"name": self.service_name},
            )
            create_response.raise_for_status()
            self._service_id = create_response.json()["id"]
            return self._service_id

    def _make_client(self) -> httpx.Client:
        return self._client_factory()

    def _record_failure(self, error: str) -> None:
        self._dropped += 1
        self._last_error = error[:200]

    # ── 生命周期与观测 ────────────────────────────────────────────────────────

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._worker is not None:
            # 置位停止事件：worker 排空队列后才退出（有界等待，不无限阻塞）
            self._stop_event.set()
            self._worker.join(timeout=max(self.timeout + 2.0, 5.0))
        super().close()

    def stats(self) -> dict:
        """丢弃/发送可观测（F18）：queued/sent/dropped/last_error。"""
        return {
            "mode": "async" if self.async_mode else "sync",
            "queued": self._queue.qsize(),
            "sent": self._sent,
            "dropped": self._dropped,
            "last_error": self._last_error,
        }
