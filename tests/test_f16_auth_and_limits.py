"""F16：接入密钥（可选门锁）+ 请求大小上限 + 写入频率限流。

验收（对应基线 F16）：未授权拒绝（401）、错误信息不输出凭据、
写入大小与频率有限额（413/429）。
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.routes import router
from app.database import Base, get_db


@pytest.fixture()
def protected_client() -> TestClient:
    """带大小/频率保护中间件的测试客户端（模拟 create_app 的挂载方式）。"""
    from app.middleware import apply_request_protection

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app = FastAPI()
    apply_request_protection(app)
    app.include_router(router)
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client


# ── 门锁开关 ─────────────────────────────────────────────────────────────────


def test_auth_off_by_default_keeps_everything_open(client: TestClient):
    # 不设置 AUTH_API_KEY：演示模式，读写都照旧可用
    assert client.get("/health").status_code == 200
    assert client.post("/services", json={"name": "open-service"}).status_code == 201


def test_auth_on_rejects_missing_key(client: TestClient, monkeypatch):
    monkeypatch.setenv("AUTH_API_KEY", "secret-123")
    assert client.get("/health").status_code == 401
    assert client.get("/services").status_code == 401
    assert client.post("/services", json={"name": "locked-service"}).status_code == 401


def test_auth_on_rejects_wrong_key(client: TestClient, monkeypatch):
    monkeypatch.setenv("AUTH_API_KEY", "secret-123")
    response = client.get("/health", headers={"X-API-Key": "wrong-key"})
    assert response.status_code == 401


def test_auth_on_accepts_correct_key(client: TestClient, monkeypatch):
    monkeypatch.setenv("AUTH_API_KEY", "secret-123")
    headers = {"X-API-Key": "secret-123"}
    assert client.get("/health", headers=headers).status_code == 200
    assert (
        client.post("/services", json={"name": "key-service"}, headers=headers).status_code
        == 201
    )


def test_401_response_does_not_echo_key(client: TestClient, monkeypatch):
    monkeypatch.setenv("AUTH_API_KEY", "super-secret-key-value")
    wrong = client.get("/services", headers={"X-API-Key": "wrong"})
    assert wrong.status_code == 401
    assert "super-secret-key-value" not in wrong.text
    # 正确钥匙能通过，且 401 错误信息里从头到尾没出现过钥匙
    assert (
        client.get(
            "/services", headers={"X-API-Key": "super-secret-key-value"}
        ).status_code
        == 200
    )


def test_features_reports_lock_and_limits_without_leaking_key(
    client: TestClient, monkeypatch
):
    monkeypatch.setenv("AUTH_API_KEY", "feature-key-999")
    monkeypatch.setenv("MAX_REQUEST_BODY_BYTES", "12345")
    monkeypatch.setenv("WRITE_RATE_LIMIT_PER_MINUTE", "42")
    response = client.get("/features", headers={"X-API-Key": "feature-key-999"})
    features = response.json()
    assert features["auth_enabled"] is True
    assert features["request_size_limit_bytes"] == 12345
    assert features["write_rate_limit_per_minute"] == 42
    assert "feature-key-999" not in response.text  # 面板不输出钥匙本身

    monkeypatch.delenv("AUTH_API_KEY")
    assert client.get("/features").json()["auth_enabled"] is False


# ── 请求大小上限 ─────────────────────────────────────────────────────────────


def test_oversized_body_rejected_with_413(protected_client: TestClient, monkeypatch):
    monkeypatch.setenv("MAX_REQUEST_BODY_BYTES", "200")
    service = protected_client.post("/services", json={"name": "size-service"}).json()
    small = protected_client.post(
        "/logs",
        json={"service_id": service["id"], "level": "INFO", "message": "short"},
    )
    assert small.status_code == 201
    big = protected_client.post(
        "/logs",
        json={"service_id": service["id"], "level": "INFO", "message": "x" * 400},
    )
    assert big.status_code == 413
    assert "too large" in big.text.lower()


# ── 写入频率限流 ─────────────────────────────────────────────────────────────


def test_excess_writes_return_429_with_retry_after(
    protected_client: TestClient, monkeypatch
):
    monkeypatch.setenv("WRITE_RATE_LIMIT_PER_MINUTE", "2")
    assert protected_client.post("/services", json={"name": "rate-service"}).status_code == 201
    service = protected_client.get("/services").json()[0]
    assert (
        protected_client.post(
            "/logs",
            json={"service_id": service["id"], "level": "INFO", "message": "one"},
        ).status_code
        == 201
    )
    # 第 3 次写入超限：429 + Retry-After
    blocked = protected_client.post(
        "/logs",
        json={"service_id": service["id"], "level": "INFO", "message": "two"},
    )
    assert blocked.status_code == 429
    assert "retry-after" in blocked.headers
    # 读取不计数，仍可用
    assert protected_client.get("/services").status_code == 200
    assert protected_client.get(f"/logs?service_id={service['id']}").status_code == 200


def test_reads_do_not_consume_write_quota(protected_client: TestClient, monkeypatch):
    monkeypatch.setenv("WRITE_RATE_LIMIT_PER_MINUTE", "1")
    service = protected_client.post("/services", json={"name": "quota-service"}).json()
    for _ in range(3):
        assert protected_client.get(f"/logs?service_id={service['id']}").status_code == 200
    # 读取没占额度，但唯一的写入额度已被上面的建服务用掉 → 写入被限
    blocked = protected_client.post(
        "/logs",
        json={"service_id": service["id"], "level": "INFO", "message": "write"},
    )
    assert blocked.status_code == 429


def test_zero_limit_disables_rate_limiting(protected_client: TestClient, monkeypatch):
    monkeypatch.setenv("WRITE_RATE_LIMIT_PER_MINUTE", "0")
    service = protected_client.post("/services", json={"name": "nolimit-service"}).json()
    for index in range(3):
        assert (
            protected_client.post(
                "/logs",
                json={
                    "service_id": service["id"],
                    "level": "INFO",
                    "message": f"msg {index}",
                },
            ).status_code
            == 201
        )


def test_429_does_not_echo_key(protected_client: TestClient, monkeypatch):
    monkeypatch.setenv("AUTH_API_KEY", "rate-key-secret")
    monkeypatch.setenv("WRITE_RATE_LIMIT_PER_MINUTE", "1")
    headers = {"X-API-Key": "rate-key-secret"}
    protected_client.post("/services", json={"name": "rate-auth-service"}, headers=headers)
    blocked = protected_client.post("/services", json={"name": "another"}, headers=headers)
    assert blocked.status_code == 429
    assert "rate-key-secret" not in blocked.text
