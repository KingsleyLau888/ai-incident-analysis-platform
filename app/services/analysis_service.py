from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.analysis import AnalysisRun, AnalysisTrace, IncidentEvidence
from app.models.incident import Incident
from app.models.log_entry import LogEntry
from app.rule_engine.detector import detect_issue, suggested_actions_for

TRACE_STEPS = (
    "log_filtering",
    "rule_detection",
    "evidence_selection",
    "summary_generation",
)


def analyze_incident(db: Session, incident: Incident) -> AnalysisRun:
    logs = list(
        db.scalars(
            select(LogEntry)
            .where(LogEntry.service_id == incident.service_id)
            .order_by(LogEntry.timestamp, LogEntry.id)
        ).all()
    )
    detection = detect_issue(logs)
    service_name = incident.service.name if incident.service else f"service-{incident.service_id}"
    summary = f"Detected {detection.issue_type} in {service_name} based on related error logs."

    analysis_run = AnalysisRun(
        incident_id=incident.id,
        issue_type=detection.issue_type,
        severity=detection.severity,
        root_cause_summary=summary,
        suggested_actions=suggested_actions_for(detection.issue_type),
    )
    db.add(analysis_run)
    db.flush()

    for log in detection.evidence_logs:
        db.add(
            IncidentEvidence(
                analysis_run_id=analysis_run.id,
                log_entry_id=log.id,
                reason=f"Matched {detection.issue_type} rule.",
            )
        )

    trace_details = {
        "log_filtering": f"Selected {len(logs)} logs for service_id={incident.service_id}.",
        "rule_detection": f"Detected issue_type={detection.issue_type}; matched={detection.matched_issues or ['unknown']}.",
        "evidence_selection": f"Selected {len(detection.evidence_logs)} evidence logs.",
        "summary_generation": "Generated deterministic template summary and rule-based suggested actions.",
    }
    for index, step_name in enumerate(TRACE_STEPS, start=1):
        db.add(
            AnalysisTrace(
                analysis_run_id=analysis_run.id,
                step_name=step_name,
                step_order=index,
                detail=trace_details[step_name],
            )
        )

    db.commit()
    return get_analysis_run(db, analysis_run.id)


def get_latest_analysis_for_incident(db: Session, incident_id: int) -> AnalysisRun | None:
    return db.scalars(
        select(AnalysisRun)
        .where(AnalysisRun.incident_id == incident_id)
        .options(
            selectinload(AnalysisRun.evidence_logs).selectinload(IncidentEvidence.log_entry),
            selectinload(AnalysisRun.traces),
        )
        .order_by(AnalysisRun.id.desc())
    ).first()


def get_analysis_run(db: Session, analysis_run_id: int) -> AnalysisRun | None:
    return db.scalars(
        select(AnalysisRun)
        .where(AnalysisRun.id == analysis_run_id)
        .options(
            selectinload(AnalysisRun.evidence_logs).selectinload(IncidentEvidence.log_entry),
            selectinload(AnalysisRun.traces),
        )
    ).first()
