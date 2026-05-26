from fastapi.testclient import TestClient


def test_create_list_and_get_incident(client: TestClient):
    service = client.post("/services", json={"name": "order-api"}).json()

    payload = {
        "service_id": service["id"],
        "title": "Checkout failures",
        "description": "Users cannot complete checkout",
    }
    create_response = client.post("/incidents", json=payload)

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["service_id"] == service["id"]
    assert created["status"] == "open"

    list_response = client.get(f"/incidents?service_id={service['id']}")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    get_response = client.get(f"/incidents/{created['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["title"] == payload["title"]


def test_create_incident_for_missing_service_returns_404(client: TestClient):
    response = client.post(
        "/incidents",
        json={"service_id": 999, "title": "Missing service incident"},
    )

    assert response.status_code == 404
