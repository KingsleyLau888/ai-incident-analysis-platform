from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    incident: Mapped["Incident"] = relationship(back_populates="analysis_runs")
    evidence_logs: Mapped[list["IncidentEvidence"]] = relationship(back_populates="analysis_run")
    traces: Mapped[list["AnalysisTrace"]] = relationship(back_populates="analysis_run")

    @property
    def retrieved_runbook_chunks(self) -> list[dict]:
        return getattr(self, "_retrieved_runbook_chunks", [])

    def set_retrieved_runbook_chunks(self, chunks: list[dict]) -> None:
        self._retrieved_runbook_chunks = chunks


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
