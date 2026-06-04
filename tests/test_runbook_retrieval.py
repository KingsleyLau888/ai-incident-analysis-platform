from fastapi.testclient import TestClient

from app.services import embedding_service
from app.services.embedding_service import get_embedder
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


def test_default_embedding_backend_uses_tfidf(monkeypatch):
    monkeypatch.delenv("RUNBOOK_EMBEDDING_BACKEND", raising=False)

    embedder = get_embedder()

    assert embedder.name == "tfidf"


def test_sentence_transformers_backend_falls_back_when_unavailable(monkeypatch):
    class BrokenSentenceTransformerEmbedder:
        def __init__(self) -> None:
            raise RuntimeError("model unavailable")

    monkeypatch.setenv("RUNBOOK_EMBEDDING_BACKEND", "sentence-transformers")
    monkeypatch.setattr(embedding_service, "SentenceTransformerEmbedder", BrokenSentenceTransformerEmbedder)

    embedder = get_embedder()

    assert embedder.name == "tfidf"


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


def test_unknown_issue_analyze_returns_no_runbook_chunks(client: TestClient):
    incident = _create_incident_with_logs(
        client,
        service_name="profile-service",
        messages=["INFO profile request completed slower than usual"],
    )

    response = client.post(f"/incidents/{incident['id']}/analyze")

    assert response.status_code == 201
    analysis = response.json()
    assert analysis["issue_type"] == "unknown"
    assert analysis["retrieved_runbook_chunks"] == []
    assert "retrieve_runbooks" not in analysis["analysis_plan"]["tool_steps"]
    assert "retrieve_similar_incidents" not in analysis["analysis_plan"]["tool_steps"]


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
    retrieval_step = next(step for step in trace if step["step_name"] == "vector_runbook_retrieval")
    assert "backend=" in retrieval_step["detail"]
    assert any(
        backend in retrieval_step["detail"]
        for backend in ["backend=tfidf", "backend=sentence-transformers"]
    )


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
