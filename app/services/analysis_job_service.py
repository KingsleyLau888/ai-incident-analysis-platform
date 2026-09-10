from __future__ import annotations

import threading
from datetime import UTC, datetime

from sqlalchemy import Engine, select, update
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


def find_active_job(db: Session, incident_id: int) -> AnalysisJob | None:
    """该事故最新的未完成任务（pending/running）——防连点去重用（F02）。

    已完成的任务不拦：再次触发视为有意重分析，允许新建任务。
    """
    return db.scalars(
        select(AnalysisJob)
        .where(
            AnalysisJob.incident_id == incident_id,
            AnalysisJob.status.in_(["pending", "running"]),
        )
        .order_by(AnalysisJob.id.desc())
    ).first()


def _try_claim(db: Session, job_id: int) -> AnalysisJob | None:
    """原子领取任务：仅 pending 可领取（数据库条件更新），并发执行者只有一个能成功（F02）。"""
    result = db.execute(
        update(AnalysisJob)
        .where(AnalysisJob.id == job_id, AnalysisJob.status == "pending")
        .values(status="running", started_at=datetime.now(UTC))
    )
    db.commit()
    if result.rowcount != 1:
        return None
    return get_job(db, job_id)


def run_job(bind: Engine, job_id: int) -> None:
    with Session(bind=bind) as db:
        job = _try_claim(db, job_id)
        if job is None:
            # 没领到：任务不存在 / 正被别的执行者处理 / 已完成。
            # 成功任务重入不重跑，已有结果保持不变（幂等，F02）。
            return

        incident = incident_service.get_incident(db, job.incident_id)
        if incident is None:
            _fail(db, job, "Incident not found.")
            return

        try:
            # 初始进度也在保护伞内：提交失败会记 failed，而不是永远卡 running（F02）
            _set_progress(db, job, "loading_incident", "Loading incident context.")
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


def recover_interrupted_jobs(bind: Engine) -> dict[str, int]:
    """开机清场（F02）：进程中断遗留的任务恢复或明确失败。

    - running → failed：进程内 BackgroundTasks 无跨进程续跑能力，重启后
      遗留的 running 一定是中断的，标失败并写明原因。
    - pending → 重新执行：补发时领取是原子条件更新，重复触发不会产生重复结果。
    仅适用单进程部署；多 worker 时 running 可能属于其他进程（已知限制，F02）。
    """
    with Session(bind=bind) as db:
        pending_ids = [
            job.id
            for job in db.scalars(select(AnalysisJob).where(AnalysisJob.status == "pending")).all()
        ]
        stale_running = db.execute(
            update(AnalysisJob)
            .where(AnalysisJob.status == "running")
            .values(
                status="failed",
                current_step="failed",
                detail="Analysis failed.",
                error="Interrupted by process shutdown; recovered at startup.",
                completed_at=datetime.now(UTC),
            )
        )
        db.commit()
        failed_count = stale_running.rowcount or 0

    for job_id in pending_ids:
        threading.Thread(target=run_job, args=(bind, job_id), daemon=True).start()
    return {"failed": failed_count, "requeued": len(pending_ids)}
