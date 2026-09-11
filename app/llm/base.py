from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel, Field

from app.models.log_entry import LogEntry
from app.services.runbook_retriever import RetrievedRunbookChunk
from app.services.similar_incident_retriever import SimilarIncident


class RootCauseHypothesis(BaseModel):
    cause: str
    confidence: float = Field(ge=0.0, le=1.0)
    supporting_evidence: list[str]


class StructuredDiagnosis(BaseModel):
    diagnosis_summary: str
    root_cause_hypotheses: list[RootCauseHypothesis]
    impact_scope: str
    structured_suggested_actions: list[str]
    # F10：区分事实/假设/缺失信息——无法从证据确定的点必须单列，不混进结论
    missing_information: list[str] = Field(default_factory=list)


@dataclass(frozen=True)
class DiagnosisResult:
    diagnosis: StructuredDiagnosis
    provider: str
    # F09：结构化执行元数据——降级时对照请求与生效后端、原因、耗时、用量
    requested_provider: str | None = None
    model: str | None = None
    fallback_reason: str | None = None
    duration_ms: int | None = None
    token_usage: dict | None = None
    # F10：引用校验结果——伪造/不可核实引用被降级时逐条记录，Trace 可见
    citation_warnings: list[str] | None = None


class LLMClient(Protocol):
    def diagnose(
        self,
        incident_title: str,
        service_name: str,
        issue_type: str,
        severity: str,
        evidence_logs: list[LogEntry],
        retrieved_runbook_chunks: list[RetrievedRunbookChunk],
        similar_incidents: list[SimilarIncident],
        investigation_notes: list[str] | None = None,
    ) -> DiagnosisResult:
        ...
