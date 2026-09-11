import json
from dataclasses import asdict, dataclass
from pathlib import Path

from app.models.log_entry import LogEntry
from app.services.embedding_service import (
    TextEmbedder,
    TfidfEmbedder,
    get_cross_encoder,
    get_embedder,
    get_retrieval_mode,
    get_sentence_transformer_embedder,
    two_stage_retrieve,
)
from app.services.rrf import reciprocal_rank_fusion
from app.services.vector_store import VectorStore


HISTORICAL_INCIDENTS_PATH = Path(__file__).resolve().parents[2] / "data" / "historical_incidents.json"


@dataclass(frozen=True)
class HistoricalIncident:
    historical_id: str
    title: str
    service_name: str
    issue_type: str
    symptoms: list[str]
    root_cause: str
    resolution: str
    tags: list[str]


@dataclass(frozen=True)
class SimilarIncident:
    historical_id: str
    title: str
    issue_type: str
    similarity_score: float
    root_cause: str
    resolution: str


class SimilarIncidentRetriever:
    def __init__(
        self,
        incidents: list[HistoricalIncident] | None = None,
        embedder: TextEmbedder | None = None,
        dense_embedder: TextEmbedder | None = None,
        retrieval_mode: str | None = None,
    ) -> None:
        self.incidents = incidents if incidents is not None else load_historical_incidents()
        self.retrieval_mode = retrieval_mode or get_retrieval_mode()
        self.sparse_embedder = TfidfEmbedder()
        self.dense_embedder = dense_embedder
        self.fallback_reason: str | None = None
        # F09：实例级检索计时——一次分析一个检索器实例，计时不串分析
        self._last_timing: dict = {}

        # ChromaDB path
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
            self.embedder = self.sparse_embedder
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
        # F09：优先报告本次检索实际计时；无计时记录（chromadb 路径）退回配置标注
        if self._last_timing:
            rerank_note = self._timing_note()
        else:
            cross_encoder = get_cross_encoder()
            rerank_note = f" rerank={cross_encoder.name}" if cross_encoder else ""

        if self.retrieval_mode == "chromadb":
            if self._vector_store is not None:
                return f"retrieval_mode=chromadb; store=persistent; count={self._vector_store.incident_count()}{rerank_note}"
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

    def _timing_note(self) -> str:
        """F09：本次检索的实际计时摘要（coarse/rerank/候选数）。"""
        note = f" coarse={self._last_timing.get('coarse_ms', 0):.0f}ms"
        note += f"; candidates={self._last_timing.get('coarse_candidates', 0)}"
        reranker = self._last_timing.get("reranker")
        if reranker not in (None, "none"):
            note += f"; rerank={reranker}({self._last_timing.get('rerank_ms', 0):.0f}ms)"
        return note

    def retrieve(
        self,
        incident_title: str,
        service_name: str,
        issue_type: str,
        evidence_logs: list[LogEntry],
        top_k: int = 3,
    ) -> list[SimilarIncident]:
        if issue_type == "unknown":
            return []

        query = build_similar_incident_query(
            incident_title=incident_title,
            service_name=service_name,
            issue_type=issue_type,
            evidence_logs=evidence_logs,
        )
        documents = [_incident_document(incident) for incident in self.incidents]

        # ChromaDB path
        if self._vector_store is not None:
            results = self._vector_store.query_incidents(query, top_k=top_k)
            return [
                SimilarIncident(
                    historical_id=result.get("historical_id", ""),
                    title=result.get("title", ""),
                    issue_type=result.get("issue_type", ""),
                    similarity_score=result["score"],
                    root_cause=result.get("root_cause", ""),
                    resolution=result.get("resolution", ""),
                )
                for result in results
            ]

        ranked = self._rank(query, documents, top_k)

        return [
            SimilarIncident(
                historical_id=self.incidents[index].historical_id,
                title=self.incidents[index].title,
                issue_type=self.incidents[index].issue_type,
                similarity_score=round(score, 6),
                root_cause=self.incidents[index].root_cause,
                resolution=self.incidents[index].resolution,
            )
            for index, score in ranked
        ]

    def retrieve_with_query(
        self,
        query: str,
        top_k: int = 3,
        issue_type: str | None = None,
    ) -> list[SimilarIncident]:
        """按调用方给定的查询文本检索（F06）：Agent 的调查查询真正进入检索输入。"""
        documents = [_incident_document(incident) for incident in self.incidents]
        ranked = self._rank(query, documents, top_k)
        return [
            SimilarIncident(
                historical_id=self.incidents[index].historical_id,
                title=self.incidents[index].title,
                issue_type=self.incidents[index].issue_type,
                similarity_score=round(score, 6),
                root_cause=self.incidents[index].root_cause,
                resolution=self.incidents[index].resolution,
            )
            for index, score in ranked
        ]

    def _rank(self, query: str, documents: list[str], top_k: int) -> list[tuple[int, float]]:
        # F09：每次检索入口重置计时（chromadb 路径无计时，同样不残留旧值）
        self._last_timing = {}
        if self._vector_store is not None:
            incident_index = {
                incident.historical_id: index
                for index, incident in enumerate(self.incidents)
            }
            ranked = []
            for result in self._vector_store.query_incidents(query, top_k=top_k):
                historical_id = result.get("historical_id")
                if historical_id in incident_index:
                    ranked.append((incident_index[historical_id], result["score"]))
            return ranked

        return two_stage_retrieve(
            query=query,
            documents=documents,
            coarse_top_k=10,
            fine_top_k=top_k,
            coarse_ranker=self._coarse_ranker(),
            timing=self._last_timing,
        )

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


def load_historical_incidents(
    path: Path = HISTORICAL_INCIDENTS_PATH,
) -> list[HistoricalIncident]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return [HistoricalIncident(**item) for item in data]


def build_similar_incident_query(
    incident_title: str,
    service_name: str,
    issue_type: str,
    evidence_logs: list[LogEntry],
) -> str:
    evidence_text = " ".join(log.message for log in evidence_logs)
    return " ".join(
        part
        for part in [incident_title, service_name, issue_type, evidence_text]
        if part
    )


def serialize_similar_incidents(incidents: list[SimilarIncident]) -> list[dict]:
    return [asdict(incident) for incident in incidents]


def _incident_document(incident: HistoricalIncident) -> str:
    return "\n".join(
        [
            incident.historical_id,
            incident.title,
            incident.service_name,
            incident.issue_type,
            " ".join(incident.symptoms),
            incident.root_cause,
            incident.resolution,
            " ".join(incident.tags),
        ]
    )
