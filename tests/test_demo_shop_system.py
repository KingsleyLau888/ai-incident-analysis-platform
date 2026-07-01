import importlib

from fastapi.testclient import TestClient


def _shop_app(monkeypatch, tmp_path):
    monkeypatch.setenv("SHOP_LOG_FORWARDING_ENABLED", "0")
    module = importlib.import_module("demo_shop_system.app")
    module.DATABASE_PATH = tmp_path / "shop.db"
    module.fault_mode = "none"
    module.init_database()
    return module.app


def test_demo_shop_checkout_success(monkeypatch, tmp_path):
    client = TestClient(_shop_app(monkeypatch, tmp_path))

    response = client.post("/api/checkout", json={"sku": "keyboard-pro", "quantity": 1})

    assert response.status_code == 200
    assert response.json()["status"] == "paid"


def test_demo_shop_simple_database_fault_returns_500(monkeypatch, tmp_path):
    client = TestClient(_shop_app(monkeypatch, tmp_path))

    client.post("/api/faults/simple_database")
    response = client.post("/api/checkout", json={"sku": "keyboard-pro", "quantity": 1})

    assert response.status_code == 500
    assert response.json()["detail"] == "database unavailable"


def test_demo_shop_complex_database_fault_returns_500(monkeypatch, tmp_path):
    client = TestClient(_shop_app(monkeypatch, tmp_path))

    client.post("/api/faults/complex_database")
    response = client.post("/api/checkout", json={"sku": "keyboard-pro", "quantity": 1})

    assert response.status_code == 500
    assert response.json()["detail"] == "database unavailable"


def test_demo_shop_complex_mixed_fault_returns_500(monkeypatch, tmp_path):
    client = TestClient(_shop_app(monkeypatch, tmp_path))

    client.post("/api/faults/complex_mixed")
    response = client.post("/api/checkout", json={"sku": "keyboard-pro", "quantity": 1})

    assert response.status_code == 500
    assert response.json()["detail"] == "mixed checkout failure"


def test_demo_shop_fault_endpoint_returns_operator_label(monkeypatch, tmp_path):
    client = TestClient(_shop_app(monkeypatch, tmp_path))

    response = client.post("/api/faults/simple_database")

    assert response.status_code == 200
    assert response.json()["fault_mode"] == "simple_database"
    assert response.json()["fault_label"] == "数据库降级"


def test_demo_shop_frontend_loads_realistic_roles(monkeypatch, tmp_path):
    client = TestClient(_shop_app(monkeypatch, tmp_path))

    response = client.get("/")

    assert response.status_code == 200
    assert "Demo Shop" in response.text
    assert "Checkout" in response.text
    assert "用户视角" in response.text
    assert "运行状态控制台" in response.text
    assert "普通用户不会看到这里" in response.text
