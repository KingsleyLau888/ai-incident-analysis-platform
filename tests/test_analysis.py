from fastapi.testclient import TestClient


def test_analyze_database_issue(client: TestClient):
    incident = _create_incident_with_logs(
        client,
        service_name="payment-service",
        messages=[
            "INFO request started",
            "ERROR DBConnection failed while connecting to postgres",
            "ERROR request timed out after retry",
        ],
    )

    response = client.post(f"/incidents/{incident['id']}/analyze")

    assert response.status_code == 201
    analysis = response.json()
    assert analysis["incident_id"] == incident["id"]
    assert analysis["issue_type"] == "database_issue"
    assert analysis["severity"] == "high"
    assert analysis["summary"] == "Detected database_issue in payment-service based on related error logs."
    assert analysis["suggested_actions"] == "Check database availability, connection pool, and credentials."
    assert len(analysis["evidence_logs"]) == 1
    assert "DBConnection" in analysis["evidence_logs"][0]["log_entry"]["message"]
    assert "payment-service is showing signs of database issue" in analysis["diagnosis_summary"]
    assert analysis["root_cause_hypotheses"]
    assert analysis["impact_scope"] == "Likely impact is scoped to payment-service and its directly related dependencies."
    assert analysis["structured_suggested_actions"]


def test_analyze_timeout_issue(client: TestClient):
    incident = _create_incident_with_logs(
        client,
        service_name="checkout-service",
        messages=[
            "INFO request started",
            "ERROR upstream request timed out after 30s",
        ],
    )

    response = client.post(f"/incidents/{incident['id']}/analyze")

    assert response.status_code == 201
    analysis = response.json()
    assert analysis["issue_type"] == "timeout_issue"
    assert analysis["severity"] == "medium"
    assert analysis["suggested_actions"] == "Check upstream latency and timeout settings."
    assert len(analysis["evidence_logs"]) == 1


def test_get_analysis(client: TestClient):
    incident = _create_incident_with_logs(
        client,
        service_name="order-service",
        messages=["ERROR mysql connection failed"],
    )
    analyze_response = client.post(f"/incidents/{incident['id']}/analyze")
    assert analyze_response.status_code == 201

    response = client.get(f"/incidents/{incident['id']}/analysis")

    assert response.status_code == 200
    analysis = response.json()
    assert analysis["issue_type"] == "database_issue"
    assert analysis["severity"] == "high"


def test_get_trace(client: TestClient):
    incident = _create_incident_with_logs(
        client,
        service_name="auth-service",
        messages=["ERROR Unauthorized token rejected"],
    )
    analyze_response = client.post(f"/incidents/{incident['id']}/analyze")
    assert analyze_response.status_code == 201

    response = client.get(f"/incidents/{incident['id']}/trace")

    assert response.status_code == 200
    trace = response.json()
    assert [step["step_name"] for step in trace] == [
        "log_filtering",
        "rule_detection",
        "evidence_selection",
        "vector_runbook_retrieval",
        "summary_generation",
    ]
    assert [step["step_order"] for step in trace] == [1, 2, 3, 4, 5]
    summary_step = next(step for step in trace if step["step_name"] == "summary_generation")
    assert "mock LLM structured diagnosis" in summary_step["detail"]


def _create_incident_with_logs(
    client: TestClient,
    service_name: str,
    messages: list[str],
) -> dict:
    service = client.post("/services", json={"name": service_name}).json()
    for message in messages:
        client.post(
            "/logs",
            json={
                "service_id": service["id"],
                "level": "ERROR",
                "message": message,
            },
        )
    return client.post(
        "/incidents",
        json={
            "service_id": service["id"],
            "title": f"{service_name} incident",
        },
    ).json()
