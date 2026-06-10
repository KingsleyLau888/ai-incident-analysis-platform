"""Feedback model — human evaluation of diagnosis quality.

Stores engineer ratings and correctness flags for analysis runs.
High-rated diagnoses are used as positive references in similar incident retrieval.
"""

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DiagnosisFeedback(Base):
    __tablename__ = "diagnosis_feedback"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    analysis_run_id: Mapped[int] = mapped_column(
        ForeignKey("analysis_runs.id"), index=True, unique=True
    )
    rating: Mapped[int] = mapped_column(Integer)  # 1-5
    is_diagnosis_correct: Mapped[bool] = mapped_column(Boolean, default=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    analysis_run: Mapped["AnalysisRun"] = relationship()
