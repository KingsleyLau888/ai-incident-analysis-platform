from fastapi.testclient import TestClient

from app.services.similar_incident_retriever import SimilarIncidentRetriever


class _Log:
    def __init__(self, message: str) -> None:
        self.message = message


class _FakeDenseEmbedder:
    name = "sentence-transformers"

    def rank(self, query: str, documents: list[str], top_k: int) -> list[tuple[int, float]]:
        return [(index, float(len(documents) - index)) for index in range(min(top_k, len(documents)))]


class _FakeIncidentVectorStore:
    def __init__(self, historical_id: str) -> None:
        self.historical_id = historical_id
        self.queries: list[str] = []

    def query_incidents(self, query: str, top_k: int) -> list[dict]:
        self.queries.append(query)
        return [{"historical_id": self.historical_id, "score": 0.88}]


def test_database_payment_case_retrieves_database_history():
    retriever = SimilarIncidentRetriever()

    incidents = retriever.retrieve(
        incident_title="Payment API returns 500 errors",
        service_name="payment-service",
        issue_type="database_issue",
        evidence_logs=[_Log("ERROR DBConnectionTimeout while connecting to mysql-primary")],
    )

    assert incidents
    assert any(incident.issue_type == "database_issue" for incident in incidents)
    assert any(
        "connection" in incident.root_cause.lower() or "mysql-primary" in incident.root_cause.lower()
        for incident in incidents
    )


def test_hybrid_retrieval_mode_returns_similar_incidents(monkeypatch):
    monkeypatch.setenv("RETRIEVAL_MODE", "hybrid")
    retriever = SimilarIncidentRetriever(dense_embedder=_FakeDenseEmbedder())

    incidents = retriever.retrieve(
        incident_title="Payment API returns 500 errors",
        service_name="payment-service",
        issue_type="database_issue",
        evidence_logs=[_Log("ERROR DBConnectionTimeout while connecting to mysql-primary")],
    )

    assert incidents
    assert retriever.effective_retrieval_mode == "hybrid"


def test_chromadb_rank_uses_vector_store_results():
    retriever = SimilarIncidentRetriever(retrieval_mode="tfidf")
    target_incident = retriever.incidents[-1]
    vector_store = _FakeIncidentVectorStore(target_incident.historical_id)
    retriever._vector_store = vector_store

    ranked = retriever._rank("database connection timeout", [], top_k=3)

    assert vector_store.queries == ["database connection timeout"]
    assert ranked == [(len(retriever.incidents) - 1, 0.88)]


def test_analyze_returns_similar_incidents_and_trace(client: TestClient):
    service = client.post("/services", json={"name": "payment-service"}).json()
    client.post(
        "/logs",
        json={
            "service_id": service["id"],
            "level": "ERROR",
            "message": "ERROR DBConnectionTimeout while connecting to mysql-primary",
        },
    )
    incident = client.post(
        "/incidents",
        json={
            "service_id": service["id"],
            "title": "Payment API returns 500 errors",
        },
    ).json()

    analysis_response = client.post(f"/incidents/{incident['id']}/analyze")
    trace_response = client.get(f"/incidents/{incident['id']}/trace")

    assert analysis_response.status_code == 201
    assert analysis_response.json()["similar_incidents"]
    assert "similar_incident_retrieval" in [
        step["step_name"] for step in trace_response.json()
    ]
    retrieval_step = next(
        step for step in trace_response.json() if step["step_name"] == "similar_incident_retrieval"
    )
    assert "retrieval_mode=" in retrieval_step["detail"]
