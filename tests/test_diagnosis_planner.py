from fastapi.testclient import TestClient


def test_database_issue_plan_includes_retrieval_tools(client: TestClient):
    incident = _create_incident(
        client,
        service_name="payment-service",
        log_message="ERROR DBConnectionTimeout while connecting to mysql-primary",
    )

    response = client.post(f"/incidents/{incident['id']}/analyze")

    assert response.status_code == 201
    tool_steps = response.json()["analysis_plan"]["tool_steps"]
    assert "retrieve_runbooks" in tool_steps
    assert "retrieve_similar_incidents" in tool_steps


def test_trace_contains_planner_decision(client: TestClient):
    incident = _create_incident(
        client,
        service_name="payment-service",
        log_message="ERROR DBConnectionTimeout while connecting to mysql-primary",
    )
    client.post(f"/incidents/{incident['id']}/analyze")

    trace = client.get(f"/incidents/{incident['id']}/trace").json()

    planner_step = next(step for step in trace if step["step_name"] == "planner_decision")
    assert "retrieve_runbooks" in planner_step["detail"]
    assert "retrieve_similar_incidents" in planner_step["detail"]


def _create_incident(client: TestClient, service_name: str, log_message: str) -> dict:
    service = client.post("/services", json={"name": service_name}).json()
    client.post(
        "/logs",
        json={
            "service_id": service["id"],
            "level": "ERROR",
            "message": log_message,
        },
    )
    return client.post(
        "/incidents",
        json={
            "service_id": service["id"],
            "title": f"{service_name} incident",
        },
    ).json()
