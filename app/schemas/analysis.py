from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.log_entry import LogEntryRead


class EvidenceLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    log_entry_id: int
    reason: str | None
    log_entry: LogEntryRead


class AnalysisTraceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    analysis_run_id: int
    step_name: str
    step_order: int
    detail: str
    created_at: datetime


class RetrievedRunbookChunkRead(BaseModel):
    chunk_id: str
    source: str
    title: str
    content: str
    score: float


class SimilarIncidentRead(BaseModel):
    historical_id: str
    title: str
    issue_type: str
    similarity_score: float
    root_cause: str
    resolution: str


class AnalysisRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    incident_id: int
    issue_type: str
    severity: str
    summary: str = Field(validation_alias="root_cause_summary")
    suggested_actions: str
    created_at: datetime
    evidence_logs: list[EvidenceLogRead] = []
    retrieved_runbook_chunks: list[RetrievedRunbookChunkRead] = []
    similar_incidents: list[SimilarIncidentRead] = []
    diagnosis_summary: str = ""
    root_cause_hypotheses: list[str] = []
    impact_scope: str = ""
    structured_suggested_actions: list[str] = []
