from fastapi.testclient import TestClient


def test_automatic_incident_creates_succeeded_analysis_job(client: TestClient, monkeypatch):
    monkeypatch.setenv("AUTO_INCIDENT_ERROR_THRESHOLD", "3")
    service = client.post("/services", json={"name": "job-payment-service"}).json()

    for message in [
        "DBConnectionTimeout while connecting to mysql-primary",
        "Payment request failed after database retry",
        "Payment API returned 500 because database connection failed",
    ]:
        response = client.post(
            "/logs",
            json={"service_id": service["id"], "level": "ERROR", "message": message},
        )
        assert response.status_code == 201

    incidents = client.get(f"/incidents?service_id={service['id']}").json()
    jobs = client.get(f"/analysis-jobs?incident_id={incidents[0]['id']}").json()

    assert len(jobs) == 1
    assert jobs[0]["status"] == "succeeded"
    assert jobs[0]["current_step"] == "completed"
    assert jobs[0]["analysis_run_id"] is not None


def test_automatic_incident_splits_when_issue_type_changes(client: TestClient, monkeypatch):
    monkeypatch.setenv("AUTO_INCIDENT_ERROR_THRESHOLD", "3")
    service = client.post("/services", json={"name": "split-checkout-service"}).json()

    for message in [
        "DBConnectionTimeout while connecting to shop-primary",
        "shop-primary database unavailable during checkout",
        "Checkout API returned 500 after database write failure",
    ]:
        response = client.post(
            "/logs",
            json={"service_id": service["id"], "level": "ERROR", "message": message},
        )
        assert response.status_code == 201

    for message in [
        "Unauthorized checkout token rejected by auth middleware",
        "Authentication failed while creating checkout session",
        "Checkout API returned 401 after invalid customer token",
    ]:
        response = client.post(
            "/logs",
            json={"service_id": service["id"], "level": "ERROR", "message": message},
        )
        assert response.status_code == 201

    incidents = client.get(f"/incidents?service_id={service['id']}").json()
    analyses = [
        client.get(f"/incidents/{incident['id']}/analysis").json()
        for incident in incidents
    ]

    assert len(incidents) == 2
    assert [analysis["issue_type"] for analysis in analyses] == [
        "database_issue",
        "auth_issue",
    ]


def test_external_ingest_registers_service_and_stores_log(client: TestClient):
    response = client.post(
        "/ingest/logs",
        json={
            "service_name": "external-order-service",
            "level": "INFO",
            "message": "Order request completed",
        },
    )

    assert response.status_code == 201
    services = client.get("/services").json()
    service = next(item for item in services if item["name"] == "external-order-service")
    logs = client.get(f"/logs?service_id={service['id']}").json()
    assert logs[0]["message"] == "Order request completed"
