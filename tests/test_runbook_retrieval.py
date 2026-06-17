from fastapi.testclient import TestClient

from app.services import embedding_service
from app.services.embedding_service import get_embedder
from app.services.runbook_chunker import load_runbook_chunks
from app.services.runbook_retriever import RunbookRetriever


class _Log:
    def __init__(self, message: str) -> None:
        self.message = message


class _FakeDenseEmbedder:
    name = "sentence-transformers"

    def rank(self, query: str, documents: list[str], top_k: int) -> list[tuple[int, float]]:
        scored = list(enumerate(reversed([float(index) for index in range(len(documents))])))
        return sorted(scored, key=lambda item: item[1], reverse=True)[:top_k]


class _FakeRunbookVectorStore:
    def __init__(self, chunk_id: str) -> None:
        self.chunk_id = chunk_id
        self.queries: list[str] = []
        self.wheres: list[dict | None] = []

    def query_runbooks(self, query: str, top_k: int, where: dict | None = None) -> list[dict]:
        self.queries.append(query)
        self.wheres.append(where)
        return [{"chunk_id": self.chunk_id, "score": 0.99}]


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


def test_hybrid_retrieval_mode_returns_runbook_results(monkeypatch):
    monkeypatch.setenv("RETRIEVAL_MODE", "hybrid")
    retriever = RunbookRetriever(dense_embedder=_FakeDenseEmbedder())

    chunks = retriever.retrieve(
        incident_title="Payment failures",
        service_name="payment-service",
        evidence_logs=[_Log("ERROR DBConnectionTimeout when connecting to mysql-primary")],
        issue_type="database_issue",
        top_k=3,
    )

    assert chunks
    assert retriever.effective_retrieval_mode == "hybrid"
    assert all(hasattr(chunk, "score") for chunk in chunks)


def test_hybrid_falls_back_to_tfidf_when_sentence_transformers_unavailable(monkeypatch):
    class BrokenSentenceTransformerEmbedder:
        def __init__(self) -> None:
            raise RuntimeError("model unavailable")

    monkeypatch.setenv("RETRIEVAL_MODE", "hybrid")
    monkeypatch.setattr(embedding_service, "SentenceTransformerEmbedder", BrokenSentenceTransformerEmbedder)

    retriever = RunbookRetriever()
    chunks = retriever.retrieve(
        incident_title="Payment failures",
        service_name="payment-service",
        evidence_logs=[_Log("ERROR DBConnectionTimeout when connecting to mysql-primary")],
        issue_type="database_issue",
        top_k=3,
    )

    assert chunks
    assert retriever.effective_retrieval_mode == "tfidf"
    assert "components=[tfidf]" in retriever.retrieval_detail
    assert "fusion=none" in retriever.retrieval_detail
    assert "fallback_reason=sentence-transformers unavailable" in retriever.retrieval_detail


def test_chromadb_rank_uses_vector_store_results():
    chunks = load_runbook_chunks()
    target_chunk = chunks[-1]
    vector_store = _FakeRunbookVectorStore(target_chunk.chunk_id)
    retriever = RunbookRetriever(chunks=chunks, retrieval_mode="tfidf")
    retriever._vector_store = vector_store

    ranked = retriever._rank("database connection timeout", [], top_k=3)

    assert vector_store.queries == ["database connection timeout"]
    assert ranked == [(len(chunks) - 1, 0.99)]


def test_chromadb_rank_can_use_issue_type_metadata_filter(monkeypatch):
    monkeypatch.setenv("RUNBOOK_METADATA_FILTER", "1")
    chunks = load_runbook_chunks()
    target_chunk = chunks[-1]
    vector_store = _FakeRunbookVectorStore(target_chunk.chunk_id)
    retriever = RunbookRetriever(chunks=chunks, retrieval_mode="tfidf")
    retriever._vector_store = vector_store

    retriever._rank("database connection timeout", [], top_k=3, issue_type="database_issue")

    assert vector_store.wheres == [{"issue_type": "database_issue"}]


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
    assert "retrieval_mode=" in retrieval_step["detail"]
    assert "effective_retrieval_mode=" in retrieval_step["detail"]


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
