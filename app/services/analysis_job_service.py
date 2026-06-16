from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.models.analysis_job import AnalysisJob
from app.services import analysis_service, incident_service


def create_job(db: Session, incident_id: int, trigger: str = "manual") -> AnalysisJob:
    job = AnalysisJob(incident_id=incident_id, trigger=trigger)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def get_job(db: Session, job_id: int) -> AnalysisJob | None:
    return db.get(AnalysisJob, job_id)


def list_jobs(db: Session, incident_id: int | None = None, limit: int = 50) -> list[AnalysisJob]:
    statement = select(AnalysisJob)
    if incident_id is not None:
        statement = statement.where(AnalysisJob.incident_id == incident_id)
    return list(db.scalars(statement.order_by(AnalysisJob.id.desc()).limit(limit)).all())


def run_job(bind: Engine, job_id: int) -> None:
    with Session(bind=bind) as db:
        job = get_job(db, job_id)
        if job is None:
            return
        job.status = "running"
        job.started_at = datetime.now(UTC)
        _set_progress(db, job, "loading_incident", "Loading incident context.")

        incident = incident_service.get_incident(db, job.incident_id)
        if incident is None:
            _fail(db, job, "Incident not found.")
            return

        try:
            analysis = analysis_service.analyze_incident(
                db,
                incident,
                progress_callback=lambda step, detail: _update_by_id(db, job.id, step, detail),
            )
            job = get_job(db, job.id)
            job.analysis_run_id = analysis.id
            job.status = "succeeded"
            job.current_step = "completed"
            job.detail = "Analysis completed and persisted."
            job.completed_at = datetime.now(UTC)
            db.commit()
        except Exception as exc:
            db.rollback()
            job = get_job(db, job_id)
            if job is not None:
                _fail(db, job, str(exc))


def _update_by_id(db: Session, job_id: int, step: str, detail: str) -> None:
    job = get_job(db, job_id)
    if job is not None:
        _set_progress(db, job, step, detail)


def _set_progress(db: Session, job: AnalysisJob, step: str, detail: str) -> None:
    job.current_step = step
    job.detail = detail
    db.commit()


def _fail(db: Session, job: AnalysisJob, error: str) -> None:
    job.status = "failed"
    job.current_step = "failed"
    job.detail = "Analysis failed."
    job.error = error[:2000]
    job.completed_at = datetime.now(UTC)
    db.commit()
