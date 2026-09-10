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

    def retrieve_with_query(
        self,
        query: str,
        top_k: int = 3,
        issue_type: str | None = None,
    ) -> list[RetrievedRunbookChunk]:
        """按调用方给定的查询文本检索（F06）：Agent 的调查查询真正进入检索输入。

        与 retrieve() 的区别：不再由证据日志拼查询；issue_type 仅用于
        类型过滤（None = 不过滤，调查阶段允许跨类型召回）。
        """
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

        filter_mode = _runbook_filter_mode()
        if filter_mode == "soft":
            return self._rank_soft(query, documents, top_k, issue_type)

        candidate_indices = _candidate_indices_for_issue_type(self.chunks, issue_type)
        if candidate_indices:
            candidate_documents = [documents[index] for index in candidate_indices]
            ranked = two_stage_retrieve(
                query=query,
                documents=candidate_documents,
                coarse_top_k=10,
                fine_top_k=top_k,
                coarse_ranker=self._coarse_ranker(),
            )
            return [(candidate_indices[index], score) for index, score in ranked]

        # Two-stage retrieval (coarse 鈫?CrossEncoder fine)
        return two_stage_retrieve(
            query=query,
            documents=documents,
            coarse_top_k=10,
            fine_top_k=top_k,
            coarse_ranker=self._coarse_ranker(),
        )

    def _rank_soft(
        self,
        query: str,
        documents: list[str],
        top_k: int,
        issue_type: str | None = None,
    ) -> list[tuple[int, float]]:
        """soft 过滤模式：全量粗排后对类型不匹配 chunk 降权，再精排取 top_k。

        粗排候选数放大，保证跨类型文档有机会进入降权前的候选集；
        降权后按分数重排，CrossEncoder 精排沿用 two_stage 语义。
        """
        penalty = _runbook_filter_soft_penalty()
        coarse_top_k = max(10, top_k * 5)
        coarse = self._coarse_ranker().rank(query, documents, top_k=coarse_top_k)
        penalized = [
            (
                index,
                score * penalty if self.chunks[index].issue_type != issue_type else score,
            )
            for index, score in coarse
        ]
        penalized.sort(key=lambda pair: pair[1], reverse=True)

        reranker = get_cross_encoder()
        if reranker is None or len(penalized) <= top_k:
            return penalized[:top_k]
        candidate_documents = [documents[index] for index, _ in penalized]
        fine = reranker.rerank(query, candidate_documents, top_k=top_k)
        return [(penalized[candidate_index][0], score) for candidate_index, score in fine]

    def _rank_with_vector_store(
        self,
        query: str,
        top_k: int,
        issue_type: str | None = None,
    ) -> list[tuple[int, float]]:
        if self._vector_store is None:
            return []

        filter_mode = _runbook_filter_mode()
        candidate_k = max(top_k, int(os.getenv("VECTOR_RETRIEVAL_CANDIDATES", "10")))
        if filter_mode == "soft":
            candidate_k = max(candidate_k, top_k * 5)
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

        if filter_mode == "soft":
            penalty = _runbook_filter_soft_penalty()
            ranked = [
                (
                    index,
                    score * penalty if self.chunks[index].issue_type != issue_type else score,
                )
                for index, score in ranked
            ]
            ranked.sort(key=lambda pair: pair[1], reverse=True)

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
    # 去重：错误风暴会产生同文案日志，重复消息会虚增查询词权重
    evidence_text = " ".join(dict.fromkeys(log.message for log in evidence_logs))
    max_chars = int(os.getenv("RUNBOOK_QUERY_EVIDENCE_MAX_CHARS", "500"))
    if len(evidence_text) > max_chars:
        evidence_text = evidence_text[:max_chars]
    # 人类可读类型词：database_issue → database issue，与语料中的 "database" 能对上
    issue_label = issue_type.replace("_", " ")
    return " ".join(
        part
        for part in [
            incident_title,
            service_name,
            issue_label,
            evidence_text,
        ]
        if part
    )


def _runbook_metadata_filter(issue_type: str | None) -> dict | None:
    if _runbook_filter_mode() != "hard" or not issue_type or issue_type == "unknown":
        return None
    return {"issue_type": issue_type}


def _runbook_metadata_filter_enabled() -> bool:
    return os.getenv("RUNBOOK_METADATA_FILTER", "1").strip().lower() in {"1", "true", "yes"}


def _runbook_filter_mode() -> str:
    """过滤模式：hard（默认，现状）| soft（降权不排除）| off（不过滤）。

    RUNBOOK_METADATA_FILTER=0 时强制 off；RUNBOOK_FILTER_MODE 非法取值回退 hard。
    """
    if not _runbook_metadata_filter_enabled():
        return "off"
    mode = os.getenv("RUNBOOK_FILTER_MODE", "hard").strip().lower()
    return mode if mode in {"hard", "soft", "off"} else "hard"


def _runbook_filter_soft_penalty() -> float:
    """soft 模式下类型不匹配 chunk 的打分降权系数。"""
    try:
        penalty = float(os.getenv("RUNBOOK_FILTER_SOFT_PENALTY", "0.5"))
    except ValueError:
        return 0.5
    return penalty if 0.0 <= penalty <= 1.0 else 0.5


def _candidate_indices_for_issue_type(
    chunks: list[RunbookChunk],
    issue_type: str | None,
) -> list[int]:
    if _runbook_filter_mode() != "hard" or not issue_type or issue_type == "unknown":
        return []
    return [
        index for index, chunk in enumerate(chunks)
        if chunk.issue_type == issue_type
    ]


def serialize_retrieved_chunks(chunks: list[RetrievedRunbookChunk]) -> list[dict]:
    return [asdict(chunk) for chunk in chunks]
