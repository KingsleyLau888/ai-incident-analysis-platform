"""Feedback service — CRUD for human evaluations of diagnosis quality."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.feedback import DiagnosisFeedback
from app.schemas.feedback import FeedbackCreate


def upsert_feedback(db: Session, analysis_run_id: int, feedback_in: FeedbackCreate) -> DiagnosisFeedback:
    """Create or replace feedback for an analysis run."""
    existing = db.scalars(
        select(DiagnosisFeedback).where(DiagnosisFeedback.analysis_run_id == analysis_run_id)
    ).first()

    if existing:
        existing.rating = feedback_in.rating
        existing.is_diagnosis_correct = feedback_in.is_diagnosis_correct
        existing.comment = feedback_in.comment
        db.commit()
        db.refresh(existing)
        return existing

    feedback = DiagnosisFeedback(
        analysis_run_id=analysis_run_id,
        rating=feedback_in.rating,
        is_diagnosis_correct=feedback_in.is_diagnosis_correct,
        comment=feedback_in.comment,
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback


def get_feedback(db: Session, analysis_run_id: int) -> DiagnosisFeedback | None:
    return db.scalars(
        select(DiagnosisFeedback).where(DiagnosisFeedback.analysis_run_id == analysis_run_id)
    ).first()


def list_positive_feedback(db: Session, min_rating: int = 4) -> list[DiagnosisFeedback]:
    return list(
        db.scalars(
            select(DiagnosisFeedback)
            .where(DiagnosisFeedback.rating >= min_rating)
            .order_by(DiagnosisFeedback.rating.desc())
        ).all()
    )
