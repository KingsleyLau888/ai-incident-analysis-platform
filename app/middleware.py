"""请求保护中间件（F16）：单次请求体大小上限 + 写入频率限流。

配置（按请求读取，便于测试与运行期调整）：
- `MAX_REQUEST_BODY_BYTES`：请求体上限，默认 1_000_000（1MB）；<=0 表示不限。
- `WRITE_RATE_LIMIT_PER_MINUTE`：每 IP 每分钟非读取请求数，默认 600；<=0 表示不限。

单进程内存实现：限流状态随进程重启清零，多 worker 各算各的（与 F02/F03 同边界，
多进程部署需外部存储方案，见基线 F16 遗留）。不信任 X-Forwarded-For，只看直连 IP。
"""

import os
import threading
import time
from collections import defaultdict, deque

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

MAX_BODY_ENV = "MAX_REQUEST_BODY_BYTES"
RATE_ENV = "WRITE_RATE_LIMIT_PER_MINUTE"

DEFAULT_MAX_BODY = 1_000_000
DEFAULT_RATE = 600

_READ_METHODS = {"GET", "HEAD", "OPTIONS"}


def max_body_bytes() -> int:
    try:
        return int(os.getenv(MAX_BODY_ENV, str(DEFAULT_MAX_BODY)))
    except ValueError:
        return DEFAULT_MAX_BODY


def write_rate_per_minute() -> int:
    try:
        return int(os.getenv(RATE_ENV, str(DEFAULT_RATE)))
    except ValueError:
        return DEFAULT_RATE


class RequestSizeLimitMiddleware:
    """请求体大小上限：Content-Length 快速拒绝 + 按实际字节数兜底（F16）。"""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        limit = max_body_bytes()
        if limit > 0:
            for key, value in scope.get("headers", []):
                if key == b"content-length":
                    try:
                        if int(value) > limit:
                            await _send_json(
                                scope, receive, send, 413,
                                f"Request body too large (max {limit} bytes).",
                            )
                            return
                    except ValueError:
                        pass
                    break
            # 兜底：无/伪造 Content-Length 时按实际读到的字节数计数，超限在
            # 读取处抛 413（HTTPException 会穿透端点、由 FastAPI 转成 413 响应）
            received = 0

            async def limited_receive() -> dict:
                nonlocal received
                message = await receive()
                if message["type"] == "http.request":
                    received += len(message.get("body", b""))
                    if received > limit:
                        raise HTTPException(
                            status_code=413,
                            detail=f"Request body too large (max {limit} bytes).",
                        )
                return message

            await self.app(scope, limited_receive, send)
            return
        await self.app(scope, receive, send)


class WriteRateLimitMiddleware:
    """每 IP 每分钟写入次数限流：非读取方法计数，超限 429 + Retry-After（F16）。"""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        if scope.get("method", "GET") in _READ_METHODS:
            await self.app(scope, receive, send)
            return
        limit = write_rate_per_minute()
        if limit > 0:
            client = scope.get("client")[0] if scope.get("client") else "unknown"
            now = time.monotonic()
            with self._lock:
                hits = self._hits[client]
                while hits and now - hits[0] > 60:
                    hits.popleft()
                if len(hits) >= limit:
                    retry_after = max(1, int(60 - (now - hits[0])))
                    await _send_json(
                        scope, receive, send, 429,
                        "Too many requests. Please slow down.",
                        extra_headers={"Retry-After": str(retry_after)},
                    )
                    return
                hits.append(now)
        await self.app(scope, receive, send)


def apply_request_protection(app: FastAPI) -> None:
    """给应用挂上大小与频率两道保护（先挂者靠内层）。"""
    app.add_middleware(RequestSizeLimitMiddleware)
    app.add_middleware(WriteRateLimitMiddleware)


async def _send_json(
    scope: Scope,
    receive: Receive,
    send: Send,
    status_code: int,
    detail: str,
    extra_headers: dict[str, str] | None = None,
) -> None:
    response = JSONResponse({"detail": detail}, status_code=status_code)
    for name, value in (extra_headers or {}).items():
        response.headers[name] = value
    await response(scope, receive, send)
