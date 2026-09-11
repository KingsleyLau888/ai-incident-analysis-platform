"""R04（2026-09-11 复核）：带锁整条链路。

- 页面壳（/ 与 /dev-tools）不含数据、无锁放行——浏览器必须先拿到页面
  才能输入钥匙，随后的数据请求由 JS 附上 X-API-Key；
- 数据/写入接口带锁：无钥匙 401、对钥匙放行（门禁不因页面壳放行而弱化）；
- 日志 handler 传 api_key 后每个请求携带 X-API-Key（否则带锁平台上
  日志被 401 全丢，凭据链必须在业务侧闭合）。
"""

import logging

import httpx
import pytest

from integrations.python_logging_handler import IncidentPlatformHandler


KEY = "chain-key-999"


# ── 页面壳与数据接口的门禁边界 ──────────────────────────────────────────

def test_page_shells_open_without_key_when_locked(client, monkeypatch):
    """上锁后页面壳仍可加载（否则浏览器没法输入钥匙）；数据接口 401。"""
    monkeypatch.setenv("AUTH_API_KEY", KEY)
    assert client.get("/").status_code == 200
    assert client.get("/dev-tools").status_code == 200
    assert client.get("/health").status_code == 401
    assert client.get("/features").status_code == 401
    assert client.get("/services").status_code == 401
    assert client.get("/events").status_code == 401


def test_data_endpoints_still_require_key_when_locked(client, monkeypatch):
    """页面壳放行不代表门禁弱化：数据与写入必须带对钥匙。"""
    monkeypatch.setenv("AUTH_API_KEY", KEY)
    assert client.post("/services", json={"name": "r04-nokey"}).status_code == 401
    headers = {"X-API-Key": KEY}
    assert client.get("/services", headers=headers).status_code == 200
    assert (
        client.post("/services", json={"name": "r04-with-key"}, headers=headers)
        .status_code
        == 201
    )


# ── handler 凭据链 ──────────────────────────────────────────────────────

class _CapturingPlatform:
    """记录收到的请求与请求头（MockTransport 注入）。"""

    def __init__(self, service_id: int = 7):
        self.service_id = service_id
        self.requests: list[httpx.Request] = []

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if request.method == "GET":
            return httpx.Response(
                200, json=[{"id": self.service_id, "name": "fake-service"}]
            )
        return httpx.Response(201, json={})

    def client_factory(self) -> httpx.Client:
        return httpx.Client(
            base_url="http://platform.test",
            transport=httpx.MockTransport(self.handle),
        )


def _record() -> logging.LogRecord:
    return logging.LogRecord(
        name="test", level=logging.ERROR, pathname="", lineno=0,
        msg="boom", args=(), exc_info=None,
    )


@pytest.mark.parametrize("async_mode", [True, False])
def test_handler_attaches_api_key_to_every_request(async_mode):
    fake = _CapturingPlatform()
    handler = IncidentPlatformHandler(
        "http://platform.test",
        "fake-service",
        async_mode=async_mode,
        client_factory=fake.client_factory,
        api_key="demo-secret",
    )
    handler.emit(_record())
    handler.close()
    posts = [r for r in fake.requests if r.method == "POST"]
    assert posts, "handler 应至少发出一次日志写入"
    for request in fake.requests:
        assert request.headers.get("X-API-Key") == "demo-secret"


def test_handler_without_key_sends_no_api_key_header():
    fake = _CapturingPlatform()
    handler = IncidentPlatformHandler(
        "http://platform.test",
        "fake-service",
        async_mode=False,
        client_factory=fake.client_factory,
    )
    handler.emit(_record())
    handler.close()
    assert fake.requests, "无钥匙模式下仍应正常发送"
    assert all("X-API-Key" not in r.headers for r in fake.requests)
