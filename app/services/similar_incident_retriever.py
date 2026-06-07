import json
from dataclasses import asdict, dataclass
from pathlib import Path

from app.models.log_entry import LogEntry
from app.services.embedding_service import (
    TextEmbedder,
    TfidfEmbedder,
    get_embedder,
    get_retrieval_mode,
    get_sentence_transformer_embedder,
)
from app.services.rrf import reciprocal_rank_fusion


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
        if self.retrieval_mode != "hybrid" or self.dense_embedder is None:
            return self.embedder.rank(query, documents, top_k=top_k)

        sparse_ranked = self.sparse_embedder.rank(query, documents, top_k=top_k)
        dense_ranked = self.dense_embedder.rank(query, documents, top_k=top_k)
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
