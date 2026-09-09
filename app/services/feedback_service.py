"""Feedback service — CRUD for human evaluations of diagnosis quality."""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.analysis import AnalysisRun
from app.models.feedback import DiagnosisFeedback
from app.schemas.feedback import FeedbackCreate


def upsert_feedback(db: Session, analysis_run_id: int, feedback_in: FeedbackCreate) -> DiagnosisFeedback:
    """Create or replace feedback for an analysis run.

    目标分析必须存在（F15：孤儿反馈不得入库）；并发重复提交撞唯一约束时
    转为更新已有行，不抛 500。
    """
    if db.get(AnalysisRun, analysis_run_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis run {analysis_run_id} not found.",
        )

    existing = db.scalars(
        select(DiagnosisFeedback).where(DiagnosisFeedback.analysis_run_id == analysis_run_id)
    ).first()

    if existing:
        return _update_feedback(db, existing, feedback_in)

    feedback = DiagnosisFeedback(
        analysis_run_id=analysis_run_id,
        rating=feedback_in.rating,
        is_diagnosis_correct=feedback_in.is_diagnosis_correct,
        comment=feedback_in.comment,
    )
    db.add(feedback)
    try:
        db.commit()
    except IntegrityError:
        # 并发重复提交：另一请求已先插入，转为更新（唯一约束兜底）
        db.rollback()
        existing = db.scalars(
            select(DiagnosisFeedback).where(DiagnosisFeedback.analysis_run_id == analysis_run_id)
        ).first()
        if existing is None:
            raise
        return _update_feedback(db, existing, feedback_in)
    db.refresh(feedback)
    return feedback


def _update_feedback(
    db: Session, feedback: DiagnosisFeedback, feedback_in: FeedbackCreate
) -> DiagnosisFeedback:
    feedback.rating = feedback_in.rating
    feedback.is_diagnosis_correct = feedback_in.is_diagnosis_correct
    feedback.comment = feedback_in.comment
    db.commit()
    db.refresh(feedback)
    return feedback


def get_feedback(db: Session, analysis_run_id: int) -> DiagnosisFeedback | None:
    return db.scalars(
        select(DiagnosisFeedback).where(DiagnosisFeedback.analysis_run_id == analysis_run_id)
    ).first()


def list_positive_feedback(db: Session, min_rating: int = 4) -> list[DiagnosisFeedback]:
    """正向反馈 = 高评分且工程师判定诊断正确（F15：只看星级会把错答案当范本）。"""
    return list(
        db.scalars(
            select(DiagnosisFeedback)
            .where(
                DiagnosisFeedback.rating >= min_rating,
                DiagnosisFeedback.is_diagnosis_correct.is_(True),
            )
            .order_by(DiagnosisFeedback.rating.desc())
        ).all()
    )
