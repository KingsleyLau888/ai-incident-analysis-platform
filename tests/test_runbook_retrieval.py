from fastapi.testclient import TestClient

from app.services.runbook_chunker import load_runbook_chunks
from app.services.runbook_retriever import RunbookRetriever


class _Log:
    def __init__(self, message: str) -> None:
        self.message = message


def test_runbooks_can_be_chunked():
    chunks = load_runbook_chunks()

    assert chunks
    assert {chunk.source for chunk in chunks} >= {
        "database_issue.md",
        "timeout_issue.md",
        "memory_issue.md",
        "auth_issue.md",
        "cache_issue.md",
        "server_error.md",
    }
    assert all(chunk.chunk_id for chunk in chunks)
    assert all(chunk.title for chunk in chunks)
    assert all(chunk.content for chunk in chunks)


def test_database_incident_query_retrieves_database_runbook_chunks():
    retriever = RunbookRetriever()

    chunks = retriever.retrieve(
        incident_title="Payment failures",
        service_name="payment-service",
        evidence_logs=[_Log("ERROR DBConnectionTimeout when connecting to mysql-primary")],
        issue_type="database_issue",
        top_k=3,
    )

    assert chunks
    assert any(chunk.source == "database_issue.md" for chunk in chunks)
    assert any("mysql-primary" in chunk.content or "connection" in chunk.content.lower() for chunk in chunks)


def test_analyze_returns_retrieved_runbook_chunks(client: TestClient):
    incident = _create_incident_with_logs(
        client,
        service_name="payment-service",
        messages=[
            "INFO payment request started",
            "ERROR DBConnectionTimeout when connecting to mysql-primary",
        ],
    )

    response = client.post(f"/incidents/{incident['id']}/analyze")

    assert response.status_code == 201
    analysis = response.json()
    assert "retrieved_runbook_chunks" in analysis
    assert analysis["retrieved_runbook_chunks"]
    assert any(chunk["source"] == "database_issue.md" for chunk in analysis["retrieved_runbook_chunks"])


def test_trace_contains_vector_runbook_retrieval(client: TestClient):
    incident = _create_incident_with_logs(
        client,
        service_name="payment-service",
        messages=["ERROR DBConnectionTimeout when connecting to mysql-primary"],
    )
    analyze_response = client.post(f"/incidents/{incident['id']}/analyze")
    assert analyze_response.status_code == 201

    response = client.get(f"/incidents/{incident['id']}/trace")

    assert response.status_code == 200
    trace = response.json()
    assert "vector_runbook_retrieval" in [step["step_name"] for step in trace]


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
