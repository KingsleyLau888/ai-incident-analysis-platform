"""API key access control（F16）：演示/真实数据的边界开关。

- `AUTH_API_KEY` 未设置或空白 → 演示模式，所有接口照旧开放（本地使用不变）；
- 设置后 → 全部接口（含 /health）都要求请求头 `X-API-Key` 与钥匙一致，否则 401。
- 比较用 `secrets.compare_digest`（防时序猜测），错误信息不回显钥匙内容。
"""

import os
import secrets

from fastapi import Header, HTTPException, status

API_KEY_ENV = "AUTH_API_KEY"
API_KEY_HEADER = "X-API-Key"


def auth_enabled() -> bool:
    """门锁是否启用：环境变量存在且非空白。"""
    return bool(os.getenv(API_KEY_ENV, "").strip())


def verify_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """FastAPI 依赖：门锁启用时校验请求头钥匙；未启用时放行。"""
    expected = os.getenv(API_KEY_ENV, "").strip()
    if not expected:
        return  # 演示模式：不装锁，行为与历史一致
    if x_api_key is None or not secrets.compare_digest(x_api_key, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
        )
