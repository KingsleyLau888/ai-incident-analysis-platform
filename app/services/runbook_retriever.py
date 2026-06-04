from dataclasses import asdict, dataclass

from app.models.log_entry import LogEntry
from app.services.embedding_service import TextEmbedder, get_embedder
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
    ) -> None:
        self.chunks = chunks if chunks is not None else load_runbook_chunks()
        self.embedder = embedder if embedder is not None else get_embedder()

    @property
    def backend_name(self) -> str:
        return self.embedder.name

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
        ranked = self.embedder.rank(query, documents, top_k=top_k)

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
