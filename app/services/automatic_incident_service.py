"""Create and analyze incidents automatically after log ingestion."""

from __future__ import annotations

import threading
from contextlib import contextmanager

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.models.analysis_job import AnalysisJob
from app.models.incident import Incident
from app.models.log_entry import LogEntry
from app.schemas.incident import IncidentCreate
from app.services import analysis_job_service
from app.services.incident_detector import (
    automatic_incidents_enabled,
    evaluate_error_burst,
    find_recent_open_incident,
    infer_issue_type_for_burst,
)

# 按服务串行化"看+建"，防止并发日志为同一爆发建多个事故（F03）。
# 仅覆盖单进程部署；多进程需数据库级方案（随部署需求再定，见基线 F03）。
_service_creation_locks: dict[int, threading.Lock] = {}
_locks_guard = threading.Lock()


@contextmanager
def _service_creation_lock(service_id: int):
    with _locks_guard:
        lock = _service_creation_locks.setdefault(service_id, threading.Lock())
    with lock:
        yield


def process_log_entry(db: Session, log_entry: LogEntry) -> tuple[Incident | None, int | None]:
    """Create one incident per error burst and report whether analysis is needed."""
    if not automatic_incidents_enabled():
        return None, None

    with _service_creation_lock(log_entry.service_id):
        latest_open = find_recent_open_incident(db, log_entry.service_id)
        burst_start = latest_open.created_at if latest_open is not None else None
        decision = evaluate_error_burst(db, log_entry, since=burst_start)
        if not decision.should_create:
            return None, None

        issue_type = infer_issue_type_for_burst(db, log_entry, since=burst_start)
        existing = find_recent_open_incident(db, log_entry.service_id, issue_type=issue_type)
        if existing is not None:
            return existing, None

        service_name = log_entry.service.name if log_entry.service else f"service-{log_entry.service_id}"
        incident, job = create_incident_with_job(
            db,
            IncidentCreate(
                service_id=log_entry.service_id,
                title=f"Automatic alert for {service_name}",
                description=f"{decision.reason} Inferred issue_type={issue_type}.",
                status="open",
                inferred_issue_type=issue_type,
            ),
            trigger="automatic",
        )
        return incident, job.id


def create_incident_with_job(
    db: Session, incident_in: IncidentCreate, trigger: str = "automatic"
) -> tuple[Incident, AnalysisJob]:
    """事故与任务一次提交（F03）：中途失败两者都不落库，不留孤儿事故。"""
    incident = Incident(**incident_in.model_dump())
    db.add(incident)
    db.flush()
    job = AnalysisJob(incident_id=incident.id, trigger=trigger)
    db.add(job)
    db.commit()
    db.refresh(incident)
    db.refresh(job)
    return incident, job


def analyze_incident_in_background(bind: Engine, job_id: int) -> None:
    analysis_job_service.run_job(bind, job_id)
