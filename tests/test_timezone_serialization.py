from fastapi.testclient import TestClient


def test_log_timestamp_is_serialized_as_beijing_time(client: TestClient):
    service = client.post("/services", json={"name": "timezone-service"}).json()

    response = client.post(
        "/logs",
        json={
            "service_id": service["id"],
            "level": "INFO",
            "message": "timezone probe",
            "timestamp": "2026-07-02T08:00:00+00:00",
        },
    )

    assert response.status_code == 201
    timestamp = response.json()["timestamp"]
    assert timestamp.startswith("2026-07-02T16:00:00")
    assert timestamp.endswith("+08:00")


def test_created_at_is_serialized_with_beijing_offset(client: TestClient):
    response = client.post("/services", json={"name": "timezone-created-at-service"})

    assert response.status_code == 201
    assert response.json()["created_at"].endswith("+08:00")
