"""Detect incident-worthy bursts from newly ingested logs."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.analysis import AnalysisRun
from app.models.incident import Incident
from app.models.log_entry import LogEntry
from app.rule_engine.detector import detect_issue


@dataclass(frozen=True)
class DetectionDecision:
    should_create: bool
    error_count: int
    window_seconds: int
    reason: str


def automatic_incidents_enabled() -> bool:
    return os.getenv("AUTO_INCIDENT_ENABLED", "1").strip().lower() in {
        "1",
        "true",
        "yes",
    }


def evaluate_error_burst(
    db: Session,
    log_entry: LogEntry,
    *,
    threshold: int | None = None,
    window_seconds: int | None = None,
    since: datetime | None = None,
) -> DetectionDecision:
    threshold = threshold or int(os.getenv("AUTO_INCIDENT_ERROR_THRESHOLD", "3"))
    window_seconds = window_seconds or int(os.getenv("AUTO_INCIDENT_WINDOW_SECONDS", "60"))

    if log_entry.level.upper() not in {"ERROR", "CRITICAL"}:
        return DetectionDecision(False, 0, window_seconds, "Log level does not trigger detection.")

    timestamp = _as_utc(log_entry.timestamp)
    window_start = timestamp - timedelta(seconds=window_seconds)
    if since is not None:
        window_start = max(window_start, _as_utc(since))
    error_count = db.scalar(
        select(func.count(LogEntry.id)).where(
            LogEntry.service_id == log_entry.service_id,
            LogEntry.timestamp >= window_start,
            func.upper(LogEntry.level).in_(["ERROR", "CRITICAL"]),
        )
    ) or 0

    return DetectionDecision(
        should_create=error_count >= threshold,
        error_count=error_count,
        window_seconds=window_seconds,
        reason=f"Detected {error_count} ERROR/CRITICAL logs in {window_seconds} seconds.",
    )


def find_recent_open_incident(
    db: Session,
    service_id: int,
    *,
    issue_type: str | None = None,
) -> Incident | None:
    dedupe_minutes = int(os.getenv("AUTO_INCIDENT_DEDUPE_MINUTES", "10"))
    cutoff = datetime.now(UTC) - timedelta(minutes=dedupe_minutes)
    incidents = db.scalars(
        select(Incident)
        .where(
            Incident.service_id == service_id,
            Incident.status == "open",
            Incident.created_at >= cutoff,
        )
        .order_by(Incident.id.desc())
    ).all()
    if issue_type is None:
        return incidents[0] if incidents else None

    for incident in incidents:
        latest_analysis = db.scalars(
            select(AnalysisRun)
            .where(AnalysisRun.incident_id == incident.id)
            .order_by(AnalysisRun.id.desc())
        ).first()
        if latest_analysis is not None and latest_analysis.issue_type == issue_type:
            return incident
    return None


def infer_issue_type_for_burst(
    db: Session,
    log_entry: LogEntry,
    *,
    since: datetime | None = None,
    window_seconds: int | None = None,
) -> str:
    window_seconds = window_seconds or int(os.getenv("AUTO_INCIDENT_WINDOW_SECONDS", "60"))
    timestamp = _as_utc(log_entry.timestamp)
    window_start = timestamp - timedelta(seconds=window_seconds)
    if since is not None:
        window_start = max(window_start, _as_utc(since))
    logs = list(
        db.scalars(
            select(LogEntry)
            .where(
                LogEntry.service_id == log_entry.service_id,
                LogEntry.timestamp >= window_start,
                LogEntry.timestamp <= log_entry.timestamp,
            )
            .order_by(LogEntry.id)
        ).all()
    )
    return detect_issue(logs).issue_type


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
