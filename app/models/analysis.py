from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id"), index=True)
    issue_type: Mapped[str] = mapped_column(String(80))
    severity: Mapped[str] = mapped_column(String(30))
    root_cause_summary: Mapped[str] = mapped_column(Text)
    suggested_actions: Mapped[str] = mapped_column(Text)
    _retrieved_runbook_chunks: Mapped[list[dict]] = mapped_column(
        "retrieved_runbook_chunks", JSON, default=list
    )
    _similar_incidents: Mapped[list[dict]] = mapped_column(
        "similar_incidents", JSON, default=list
    )
    _analysis_plan: Mapped[dict] = mapped_column(
        "analysis_plan", JSON, default=lambda: {"analysis_plan": "", "tool_steps": []}
    )
    _diagnosis_summary: Mapped[str] = mapped_column(
        "diagnosis_summary", Text, default=""
    )
    _root_cause_hypotheses: Mapped[list[dict]] = mapped_column(
        "root_cause_hypotheses", JSON, default=list
    )
    _impact_scope: Mapped[str] = mapped_column("impact_scope", Text, default="")
    _structured_suggested_actions: Mapped[list[str]] = mapped_column(
        "structured_suggested_actions", JSON, default=list
    )
    # R03（2026-09-11 复核）：模型声明"还不确定/缺失的信息"必须随结果落库，
    # 不能让用户翻旧报告时只看到笃定的结论。
    _missing_information: Mapped[list[str]] = mapped_column(
        "missing_information", JSON, default=list
    )
    # 实际交给诊断模型的上下文快照：调查笔记（N# 编号按此顺序）与最终证据
    # 日志 ID 列表（E# 编号按此顺序），重载后仍可按编号还原所有材料。
    _investigation_notes: Mapped[list[str]] = mapped_column(
        "investigation_notes", JSON, default=list
    )
    _final_evidence_log_ids: Mapped[list[int]] = mapped_column(
        "final_evidence_log_ids", JSON, default=list
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    incident: Mapped["Incident"] = relationship(back_populates="analysis_runs")
    evidence_logs: Mapped[list["IncidentEvidence"]] = relationship(back_populates="analysis_run")
    traces: Mapped[list["AnalysisTrace"]] = relationship(back_populates="analysis_run")

    @property
    def retrieved_runbook_chunks(self) -> list[dict]:
        return self._retrieved_runbook_chunks or []

    def set_retrieved_runbook_chunks(self, chunks: list[dict]) -> None:
        self._retrieved_runbook_chunks = chunks

    @property
    def similar_incidents(self) -> list[dict]:
        return self._similar_incidents or []

    def set_similar_incidents(self, incidents: list[dict]) -> None:
        self._similar_incidents = incidents

    @property
    def analysis_plan(self) -> dict:
        return self._analysis_plan or {"analysis_plan": "", "tool_steps": []}

    def set_analysis_plan(self, analysis_plan: str, tool_steps: list[str]) -> None:
        self._analysis_plan = {
            "analysis_plan": analysis_plan,
            "tool_steps": tool_steps,
        }

    @property
    def diagnosis_summary(self) -> str:
        return self._diagnosis_summary or ""

    @property
    def root_cause_hypotheses(self) -> list[dict]:
        return self._root_cause_hypotheses or []

    @property
    def impact_scope(self) -> str:
        return self._impact_scope or ""

    @property
    def structured_suggested_actions(self) -> list[str]:
        return self._structured_suggested_actions or []

    @property
    def missing_information(self) -> list[str]:
        return self._missing_information or []

    @property
    def investigation_notes(self) -> list[str]:
        return self._investigation_notes or []

    @property
    def final_evidence_log_ids(self) -> list[int]:
        return self._final_evidence_log_ids or []

    def set_structured_diagnosis(
        self,
        diagnosis_summary: str,
        root_cause_hypotheses: list[dict],
        impact_scope: str,
        structured_suggested_actions: list[str],
        missing_information: list[str],
    ) -> None:
        self._diagnosis_summary = diagnosis_summary
        self._root_cause_hypotheses = root_cause_hypotheses
        self._impact_scope = impact_scope
        self._structured_suggested_actions = structured_suggested_actions
        self._missing_information = missing_information

    def set_investigation_context(
        self,
        investigation_notes: list[str],
        final_evidence_log_ids: list[int],
    ) -> None:
        """记录实际交给诊断模型的上下文快照（R03）：笔记与证据日志的最终
        顺序即 [N#]/[E#] 编号映射，重载后可按编号还原所有材料。"""
        self._investigation_notes = investigation_notes
        self._final_evidence_log_ids = final_evidence_log_ids


class IncidentEvidence(Base):
    __tablename__ = "incident_evidence"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    analysis_run_id: Mapped[int] = mapped_column(ForeignKey("analysis_runs.id"), index=True)
    log_entry_id: Mapped[int] = mapped_column(ForeignKey("log_entries.id"), index=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    analysis_run: Mapped[AnalysisRun] = relationship(back_populates="evidence_logs")
    log_entry: Mapped["LogEntry"] = relationship()


class AnalysisTrace(Base):
    __tablename__ = "analysis_traces"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    analysis_run_id: Mapped[int] = mapped_column(ForeignKey("analysis_runs.id"), index=True)
    step_name: Mapped[str] = mapped_column(String(80), index=True)
    step_order: Mapped[int] = mapped_column(Integer)
    detail: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    analysis_run: Mapped[AnalysisRun] = relationship(back_populates="traces")
