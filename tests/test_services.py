from fastapi.testclient import TestClient


def test_create_list_and_get_service(client: TestClient):
    payload = {
        "name": "checkout-api",
        "description": "Handles checkout requests",
        "owner": "platform-team",
    }

    create_response = client.post("/services", json=payload)
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["id"] == 1
    assert created["name"] == payload["name"]

    list_response = client.get("/services")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    get_response = client.get("/services/1")
    assert get_response.status_code == 200
    assert get_response.json()["owner"] == "platform-team"


def test_get_missing_service_returns_404(client: TestClient):
    response = client.get("/services/404")

    assert response.status_code == 404
