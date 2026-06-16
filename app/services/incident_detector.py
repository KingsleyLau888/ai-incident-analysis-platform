"""Detect incident-worthy bursts from newly ingested logs."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.incident import Incident
from app.models.log_entry import LogEntry


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
) -> DetectionDecision:
    threshold = threshold or int(os.getenv("AUTO_INCIDENT_ERROR_THRESHOLD", "3"))
    window_seconds = window_seconds or int(os.getenv("AUTO_INCIDENT_WINDOW_SECONDS", "60"))

    if log_entry.level.upper() not in {"ERROR", "CRITICAL"}:
        return DetectionDecision(False, 0, window_seconds, "Log level does not trigger detection.")

    timestamp = _as_utc(log_entry.timestamp)
    window_start = timestamp - timedelta(seconds=window_seconds)
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


def find_recent_open_incident(db: Session, service_id: int) -> Incident | None:
    dedupe_minutes = int(os.getenv("AUTO_INCIDENT_DEDUPE_MINUTES", "10"))
    cutoff = datetime.now(UTC) - timedelta(minutes=dedupe_minutes)
    return db.scalars(
        select(Incident)
        .where(
            Incident.service_id == service_id,
            Incident.status == "open",
            Incident.created_at >= cutoff,
        )
        .order_by(Incident.id.desc())
    ).first()


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)

