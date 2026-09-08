"""Create and analyze incidents automatically after log ingestion."""

from __future__ import annotations

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.models.incident import Incident
from app.models.log_entry import LogEntry
from app.schemas.incident import IncidentCreate
from app.services import analysis_job_service, incident_service
from app.services.incident_detector import (
    automatic_incidents_enabled,
    evaluate_error_burst,
    find_recent_open_incident,
    infer_issue_type_for_burst,
)


def process_log_entry(db: Session, log_entry: LogEntry) -> tuple[Incident | None, int | None]:
    """Create one incident per error burst and report whether analysis is needed."""
    if not automatic_incidents_enabled():
        return None, None

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
    incident = incident_service.create_incident(
        db,
        IncidentCreate(
            service_id=log_entry.service_id,
            title=f"Automatic alert for {service_name}",
            description=f"{decision.reason} Inferred issue_type={issue_type}.",
            status="open",
        ),
    )
    job = analysis_job_service.create_job(db, incident.id, trigger="automatic")
    return incident, job.id


def analyze_incident_in_background(bind: Engine, job_id: int) -> None:
    analysis_job_service.run_job(bind, job_id)
