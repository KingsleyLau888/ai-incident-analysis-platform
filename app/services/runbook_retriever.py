import os
from dataclasses import asdict, dataclass

from app.models.log_entry import LogEntry
from app.services.embedding_service import (
    ChromaDBRetriever,
    TextEmbedder,
    TfidfEmbedder,
    get_cross_encoder,
    get_embedder,
    get_last_retrieval_timing,
    get_retrieval_mode,
    get_sentence_transformer_embedder,
    two_stage_retrieve,
)
from app.services.rrf import reciprocal_rank_fusion
from app.services.runbook_chunker import RunbookChunk, load_runbook_chunks
from app.services.vector_store import VectorStore


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

        self._vector_store: VectorStore | None = None
        if self.retrieval_mode == "chromadb":
            dense = get_sentence_transformer_embedder()
            if dense is not None:
                try:
                    self._vector_store = VectorStore(embed_fn=dense.encode)
                    self._vector_store.ensure_initialized()
                except Exception as exc:
                    self._vector_store = None
                    self.fallback_reason = f"chromadb unavailable: {exc}"
            else:
                self.fallback_reason = "sentence-transformers unavailable for chromadb"
            self.embedder = self.sparse_embedder  # fallback ranker
        elif self.retrieval_mode == "hybrid":
            if self.dense_embedder is None:
                self.dense_embedder = get_sentence_transformer_embedder()
            if self.dense_embedder is None:
                self.fallback_reason = "sentence-transformers unavailable"
            self.embedder = self.sparse_embedder
        else:
            self.embedder = embedder if embedder is not None else get_embedder(self.retrieval_mode)

    @property
    def backend_name(self) -> str:
        if self.retrieval_mode == "chromadb" and self._vector_store is not None:
            return "chromadb"
        return self.embedder.name

    @property
    def effective_retrieval_mode(self) -> str:
        if self.retrieval_mode == "chromadb" and self._vector_store is not None:
            return "chromadb"
        if self.retrieval_mode == "hybrid" and self.dense_embedder is not None:
            return "hybrid"
        return self.embedder.name

    @property
    def retrieval_detail(self) -> str:
        cross_encoder = get_cross_encoder()
        rerank_note = f" rerank={cross_encoder.name}" if cross_encoder else ""

        if self.retrieval_mode == "chromadb":
            if self._vector_store is not None:
                return (
                    f"retrieval_mode=chromadb; store=persistent; "
                    f"count={self._vector_store.runbook_count()}; "
                    f"metadata_filter={_runbook_metadata_filter_enabled()}{rerank_note}"
                )
            return f"retrieval_mode=chromadb; status=degraded; fallback_reason={self.fallback_reason}"

        if self.retrieval_mode == "hybrid" and self.effective_retrieval_mode == "hybrid":
            return (
                "retrieval_mode=hybrid; components=[tfidf,sentence-transformers]; "
                f"fusion=rrf; effective_retrieval_mode=hybrid{rerank_note}"
            )
        if self.retrieval_mode == "hybrid":
            return (
                "retrieval_mode=hybrid; components=[tfidf]; fusion=none; "
                f"effective_retrieval_mode={self.effective_retrieval_mode}; "
                f"fallback_reason={self.fallback_reason}{rerank_note}"
            )
        return (
            f"retrieval_mode={self.retrieval_mode}; "
            f"effective_retrieval_mode={self.effective_retrieval_mode}{rerank_note}"
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

        ranked = self._rank(query, documents, top_k, issue_type=issue_type)

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

    def _rank(
        self,
        query: str,
        documents: list[str],
        top_k: int,
        issue_type: str | None = None,
    ) -> list[tuple[int, float]]:
        if self._vector_store is not None:
            return self._rank_with_vector_store(query, top_k, issue_type)

        # Two-stage retrieval (coarse 鈫?CrossEncoder fine)
        return two_stage_retrieve(
            query=query,
            documents=documents,
            coarse_top_k=10,
            fine_top_k=top_k,
            coarse_ranker=self._coarse_ranker(),
        )

    def _rank_with_vector_store(
        self,
        query: str,
        top_k: int,
        issue_type: str | None = None,
    ) -> list[tuple[int, float]]:
        if self._vector_store is None:
            return []

        candidate_k = max(top_k, int(os.getenv("VECTOR_RETRIEVAL_CANDIDATES", "10")))
        where = _runbook_metadata_filter(issue_type)
        results = self._vector_store.query_runbooks(query, top_k=candidate_k, where=where)
        if not results and where is not None:
            results = self._vector_store.query_runbooks(query, top_k=candidate_k)

        chunk_index = {
            chunk.chunk_id: index
            for index, chunk in enumerate(self.chunks)
        }
        ranked = [
            (chunk_index[result["chunk_id"]], result["score"])
            for result in results
            if result.get("chunk_id") in chunk_index
        ]

        reranker = get_cross_encoder()
        if reranker is None or len(ranked) <= top_k:
            return ranked[:top_k]

        candidate_documents = [
            f"{self.chunks[index].source}\n{self.chunks[index].title}\n{self.chunks[index].content}"
            for index, _ in ranked
        ]
        reranked = reranker.rerank(query, candidate_documents, top_k=top_k)
        return [(ranked[candidate_index][0], score) for candidate_index, score in reranked]

    def _coarse_ranker(self) -> TextEmbedder:
        if self.retrieval_mode != "hybrid" or self.dense_embedder is None:
            return self.embedder

        # For hybrid mode, create a composite ranker that fuses sparse + dense
        return _HybridRanker(self.sparse_embedder, self.dense_embedder)


class _HybridRanker:
    """Composite ranker fusing sparse and dense scores with RRF."""

    name = "hybrid"

    def __init__(self, sparse: TextEmbedder, dense: TextEmbedder):
        self._sparse = sparse
        self._dense = dense

    def encode(self, texts: list[str]) -> list[list[float]]:
        return []

    def rank(self, query: str, documents: list[str], top_k: int) -> list[tuple[int, float]]:
        sparse_ranked = self._sparse.rank(query, documents, top_k=top_k)
        dense_ranked = self._dense.rank(query, documents, top_k=top_k)
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


def _runbook_metadata_filter(issue_type: str | None) -> dict | None:
    if not _runbook_metadata_filter_enabled() or not issue_type or issue_type == "unknown":
        return None
    return {"issue_type": issue_type}


def _runbook_metadata_filter_enabled() -> bool:
    return os.getenv("RUNBOOK_METADATA_FILTER", "1").strip().lower() in {"1", "true", "yes"}


def serialize_retrieved_chunks(chunks: list[RetrievedRunbookChunk]) -> list[dict]:
    return [asdict(chunk) for chunk in chunks]
