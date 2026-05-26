from fastapi.testclient import TestClient


def test_create_and_list_logs(client: TestClient):
    service = client.post("/services", json={"name": "payment-api"}).json()

    payload = {
        "service_id": service["id"],
        "level": "ERROR",
        "message": "request timed out while calling database",
    }
    create_response = client.post("/logs", json=payload)

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["service_id"] == service["id"]
    assert created["message"] == payload["message"]

    list_response = client.get(f"/logs?service_id={service['id']}")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1


def test_create_log_for_missing_service_returns_404(client: TestClient):
    response = client.post(
        "/logs",
        json={"service_id": 999, "level": "ERROR", "message": "boom"},
    )

    assert response.status_code == 404
