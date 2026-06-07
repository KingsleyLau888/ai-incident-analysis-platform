from dataclasses import asdict, dataclass

from app.models.log_entry import LogEntry
from app.services.embedding_service import (
    TextEmbedder,
    TfidfEmbedder,
    get_embedder,
    get_retrieval_mode,
    get_sentence_transformer_embedder,
)
from app.services.rrf import reciprocal_rank_fusion
from app.services.runbook_chunker import RunbookChunk, load_runbook_chunks


@dataclass(frozen=True)
class RetrievedRunbookChunk:
    chunk_id: str
    source: str
    title: str
    content: str
    score: float


class RunbookRetriever:
    def __init__(
        self,
        chunks: list[RunbookChunk] | None = None,
        embedder: TextEmbedder | None = None,
        dense_embedder: TextEmbedder | None = None,
        retrieval_mode: str | None = None,
    ) -> None:
        self.chunks = chunks if chunks is not None else load_runbook_chunks()
        self.retrieval_mode = retrieval_mode or get_retrieval_mode()
        self.sparse_embedder = TfidfEmbedder()
        self.dense_embedder = dense_embedder
        self.fallback_reason: str | None = None

        if self.retrieval_mode == "hybrid":
            if self.dense_embedder is None:
                self.dense_embedder = get_sentence_transformer_embedder()
            if self.dense_embedder is None:
                self.fallback_reason = "sentence-transformers unavailable"
            self.embedder = self.sparse_embedder
        else:
            self.embedder = embedder if embedder is not None else get_embedder(self.retrieval_mode)

    @property
    def backend_name(self) -> str:
        return self.embedder.name

    @property
    def effective_retrieval_mode(self) -> str:
        if self.retrieval_mode == "hybrid" and self.dense_embedder is not None:
            return "hybrid"
        return self.embedder.name

    @property
    def retrieval_detail(self) -> str:
        if self.retrieval_mode == "hybrid" and self.effective_retrieval_mode == "hybrid":
            return (
                "retrieval_mode=hybrid; components=[tfidf,sentence-transformers]; "
                "fusion=rrf; effective_retrieval_mode=hybrid"
            )
        if self.retrieval_mode == "hybrid":
            return (
                "retrieval_mode=hybrid; components=[tfidf]; fusion=none; "
                f"effective_retrieval_mode={self.effective_retrieval_mode}; "
                f"fallback_reason={self.fallback_reason}"
            )
        return (
            f"retrieval_mode={self.retrieval_mode}; "
            f"effective_retrieval_mode={self.effective_retrieval_mode}"
        )

    def retrieve(
        self,
        incident_title: str,
        service_name: str,
        evidence_logs: list[LogEntry],
        issue_type: str,
        top_k: int = 3,
    ) -> list[RetrievedRunbookChunk]:
        if issue_type == "unknown":
            return []

        query = build_runbook_query(
            incident_title=incident_title,
            service_name=service_name,
            evidence_logs=evidence_logs,
            issue_type=issue_type,
        )
        documents = [f"{chunk.source}\n{chunk.title}\n{chunk.content}" for chunk in self.chunks]
        ranked = self._rank(query, documents, top_k)

        return [
            RetrievedRunbookChunk(
                chunk_id=self.chunks[index].chunk_id,
                source=self.chunks[index].source,
                title=self.chunks[index].title,
                content=self.chunks[index].content,
                score=round(score, 6),
            )
            for index, score in ranked
        ]

    def _rank(self, query: str, documents: list[str], top_k: int) -> list[tuple[int, float]]:
        if self.retrieval_mode != "hybrid" or self.dense_embedder is None:
            return self.embedder.rank(query, documents, top_k=top_k)

        sparse_ranked = self.sparse_embedder.rank(query, documents, top_k=top_k)
        dense_ranked = self.dense_embedder.rank(query, documents, top_k=top_k)
        fused = reciprocal_rank_fusion(
            [sparse_ranked, dense_ranked],
            key=lambda ranked_item: ranked_item[0],
        )
        return [(result.item[0], result.score) for result in fused[:top_k]]


def build_runbook_query(
    incident_title: str,
    service_name: str,
    evidence_logs: list[LogEntry],
    issue_type: str,
) -> str:
    evidence_text = " ".join(log.message for log in evidence_logs)
    return " ".join(
        part
        for part in [
            incident_title,
            service_name,
            issue_type,
            evidence_text,
        ]
        if part
    )


def serialize_retrieved_chunks(chunks: list[RetrievedRunbookChunk]) -> list[dict]:
    return [asdict(chunk) for chunk in chunks]
