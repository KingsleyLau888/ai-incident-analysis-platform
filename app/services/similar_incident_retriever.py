import json
from dataclasses import asdict, dataclass
from pathlib import Path

from app.models.log_entry import LogEntry
from app.services.embedding_service import TextEmbedder, get_embedder


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
    ) -> None:
        self.incidents = incidents if incidents is not None else load_historical_incidents()
        self.embedder = embedder if embedder is not None else get_embedder()

    @property
    def backend_name(self) -> str:
        return self.embedder.name

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
        ranked = self.embedder.rank(query, documents, top_k=top_k)

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
