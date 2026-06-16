from datetime import UTC, datetime

from fastapi.testclient import TestClient


def test_three_error_logs_create_and_analyze_incident(client: TestClient, monkeypatch):
    monkeypatch.setenv("AUTO_INCIDENT_ENABLED", "1")
    monkeypatch.setenv("AUTO_INCIDENT_ERROR_THRESHOLD", "3")
    service = client.post("/services", json={"name": "automatic-payment-service"}).json()

    for message in [
        "DBConnectionTimeout while connecting to mysql-primary",
        "Payment request failed after database retry",
        "Payment API returned 500 because database connection failed",
    ]:
        response = client.post(
            "/logs",
            json={
                "service_id": service["id"],
                "level": "ERROR",
                "message": message,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )
        assert response.status_code == 201

    incidents = client.get(f"/incidents?service_id={service['id']}").json()
    assert len(incidents) == 1
    assert incidents[0]["title"] == "Automatic alert for automatic-payment-service"

    analysis = client.get(f"/incidents/{incidents[0]['id']}/analysis")
    assert analysis.status_code == 200
    assert analysis.json()["issue_type"] == "database_issue"


def test_recent_open_incident_deduplicates_error_burst(client: TestClient, monkeypatch):
    monkeypatch.setenv("AUTO_INCIDENT_ENABLED", "1")
    monkeypatch.setenv("AUTO_INCIDENT_ERROR_THRESHOLD", "2")
    service = client.post("/services", json={"name": "dedupe-service"}).json()

    for index in range(4):
        response = client.post(
            "/logs",
            json={
                "service_id": service["id"],
                "level": "ERROR",
                "message": f"database connection failed attempt {index}",
            },
        )
        assert response.status_code == 201

    incidents = client.get(f"/incidents?service_id={service['id']}").json()
    assert len(incidents) == 1


def test_info_logs_do_not_create_incident(client: TestClient, monkeypatch):
    monkeypatch.setenv("AUTO_INCIDENT_ENABLED", "1")
    service = client.post("/services", json={"name": "healthy-service"}).json()

    for index in range(3):
        client.post(
            "/logs",
            json={
                "service_id": service["id"],
                "level": "INFO",
                "message": f"request completed {index}",
            },
        )

    incidents = client.get(f"/incidents?service_id={service['id']}").json()
    assert incidents == []
