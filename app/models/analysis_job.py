from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"
    # 每事故最多一个未完成任务：关闭并发先查后建的竞态窗口（F03）
    __table_args__ = (
        Index(
            "uq_active_job_per_incident",
            "incident_id",
            unique=True,
            sqlite_where=text("status IN ('pending','running')"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id"), index=True)
    analysis_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("analysis_runs.id"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    trigger: Mapped[str] = mapped_column(String(30), default="manual")
    current_step: Mapped[str] = mapped_column(String(80), default="queued")
    detail: Mapped[str] = mapped_column(Text, default="Waiting for a worker.")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    incident: Mapped["Incident"] = relationship()
    analysis_run: Mapped["AnalysisRun | None"] = relationship()
