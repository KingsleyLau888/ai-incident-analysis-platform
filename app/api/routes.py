"""API routes — REST endpoints, SSE streaming, and dashboard."""

import json
import time
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.analysis import AnalysisRunRead, AnalysisTraceRead
from app.schemas.feedback import FeedbackCreate, FeedbackRead
from app.schemas.incident import IncidentCreate, IncidentRead
from app.schemas.log_entry import LogEntryCreate, LogEntryRead
from app.schemas.service import ServiceCreate, ServiceRead
from app.services import analysis_service, feedback_service, incident_service, log_service, service_service

router = APIRouter()

# Dashboard templates
templates = Jinja2Templates(directory="templates")


# ═══════════════════════════════════════════════════════════════════════════════
# Health
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# ═══════════════════════════════════════════════════════════════════════════════
# Feature status — tells the dashboard what's active
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/features")
def get_features():
    """Return which advanced features are currently active."""
    return analysis_service.detect_features()


# ═══════════════════════════════════════════════════════════════════════════════
# Dashboard (HTML pages)
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    """Main dashboard page — create services, logs, incidents, and analyze."""
    services = service_service.list_services(db)
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "services": services},
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Services
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/services", response_model=ServiceRead, status_code=status.HTTP_201_CREATED)
def create_service(service_in: ServiceCreate, db: Session = Depends(get_db)):
    return service_service.create_service(db, service_in)


@router.get("/services", response_model=list[ServiceRead])
def list_services(db: Session = Depends(get_db)):
    return service_service.list_services(db)


@router.get("/services/{service_id}", response_model=ServiceRead)
def get_service(service_id: int, db: Session = Depends(get_db)):
    service = service_service.get_service(db, service_id)
    if service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    return service


# ═══════════════════════════════════════════════════════════════════════════════
# Logs
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/logs", response_model=LogEntryRead, status_code=status.HTTP_201_CREATED)
def create_log_entry(log_in: LogEntryCreate, db: Session = Depends(get_db)):
    if service_service.get_service(db, log_in.service_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    return log_service.create_log_entry(db, log_in)


@router.get("/logs", response_model=list[LogEntryRead])
def list_log_entries(
    service_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return log_service.list_log_entries(db, service_id=service_id)


# ═══════════════════════════════════════════════════════════════════════════════
# Incidents
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/incidents", response_model=IncidentRead, status_code=status.HTTP_201_CREATED)
def create_incident(incident_in: IncidentCreate, db: Session = Depends(get_db)):
    if service_service.get_service(db, incident_in.service_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    return incident_service.create_incident(db, incident_in)


@router.get("/incidents", response_model=list[IncidentRead])
def list_incidents(
    service_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return incident_service.list_incidents(db, service_id=service_id)


@router.get("/incidents/{incident_id}", response_model=IncidentRead)
def get_incident(incident_id: int, db: Session = Depends(get_db)):
    incident = incident_service.get_incident(db, incident_id)
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    return incident


# ═══════════════════════════════════════════════════════════════════════════════
# Analysis (standard + SSE streaming)
# ═══════════════════════════════════════════════════════════════════════════════


@router.post(
    "/incidents/{incident_id}/analyze",
    response_model=AnalysisRunRead,
    status_code=status.HTTP_201_CREATED,
)
def analyze_incident(incident_id: int, db: Session = Depends(get_db)):
    incident = incident_service.get_incident(db, incident_id)
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    return analysis_service.analyze_incident(db, incident)


@router.post("/incidents/{incident_id}/analyze/stream")
async def analyze_incident_stream(incident_id: int, db: Session = Depends(get_db)):
    """Stream the analysis process as Server-Sent Events.

    Each step of the pipeline is emitted as a separate event so the
    frontend can show real-time progress.
    """
    incident = incident_service.get_incident(db, incident_id)
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")

    # Run analysis synchronously while the DB session is still alive,
    # then stream the already-collected results.
    analysis = analysis_service.analyze_incident(db, incident)
    traces = sorted(analysis.traces, key=lambda t: t.step_order)

    async def event_stream() -> AsyncGenerator[str, None]:
        # 1. Loading incident
        yield _sse_event("progress", {"step": "loading", "message": "Loading incident..."})
        await _sleep(0.1)

        # 2. Collecting logs
        yield _sse_event("progress", {"step": "logs", "message": "Collecting service logs..."})
        await _sleep(0.15)

        # 3. Rule detection
        yield _sse_event("progress", {"step": "rules", "message": "Running rule-based signal detection..."})
        await _sleep(0.15)

        # 4. Retrieval
        yield _sse_event("progress", {"step": "retrieval", "message": "Retrieving runbooks and similar incidents..."})
        await _sleep(0.15)

        # 5. Stream diagnosis chunks
        yield _sse_event("progress", {"step": "diagnosis", "message": "Generating structured diagnosis..."})

        # Stream the diagnosis summary word-by-word (simulated streaming)
        summary = analysis.diagnosis_summary
        words = summary.split()
        for i, word in enumerate(words):
            chunk = word + (" " if i < len(words) - 1 else "")
            yield _sse_event("diagnosis_chunk", {"field": "summary", "text": chunk})
            await _sleep(0.03)

        # Stream root cause hypotheses
        for i, hypothesis in enumerate(analysis.root_cause_hypotheses):
            yield _sse_event("hypothesis", {
                "index": i,
                "cause": hypothesis.get("cause", ""),
                "confidence": hypothesis.get("confidence", 0),
            })
            await _sleep(0.05)

        # Stream suggested actions
        actions = analysis.structured_suggested_actions or [analysis.suggested_actions]
        for action in actions:
            yield _sse_event("action", {"text": action})
            await _sleep(0.05)

        # 6. Evidence
        evidence_count = len(analysis.evidence_logs)
        yield _sse_event("progress", {
            "step": "evidence",
            "message": f"Selected {evidence_count} evidence log(s).",
        })
        await _sleep(0.1)

        # 7. Trace
        for trace in traces:
            yield _sse_event("trace", {
                "step_name": trace.step_name,
                "step_order": trace.step_order,
                "detail": trace.detail,
            })
            await _sleep(0.05)

        # 8. Complete
        yield _sse_event("complete", {
            "analysis_id": analysis.id,
            "issue_type": analysis.issue_type,
            "severity": analysis.severity,
            "impact_scope": analysis.impact_scope,
            "runbook_count": len(analysis.retrieved_runbook_chunks),
            "similar_incident_count": len(analysis.similar_incidents),
        })

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/incidents/{incident_id}/analysis", response_model=AnalysisRunRead)
def get_incident_analysis(incident_id: int, db: Session = Depends(get_db)):
    if incident_service.get_incident(db, incident_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    analysis = analysis_service.get_latest_analysis_for_incident(db, incident_id)
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    return analysis


@router.get("/incidents/{incident_id}/trace", response_model=list[AnalysisTraceRead])
def get_incident_trace(incident_id: int, db: Session = Depends(get_db)):
    if incident_service.get_incident(db, incident_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    analysis = analysis_service.get_latest_analysis_for_incident(db, incident_id)
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    return sorted(analysis.traces, key=lambda trace: trace.step_order)


# ═══════════════════════════════════════════════════════════════════════════════
# Feedback
# ═══════════════════════════════════════════════════════════════════════════════


@router.post(
    "/analysis/{analysis_run_id}/feedback",
    response_model=FeedbackRead,
    status_code=status.HTTP_201_CREATED,
)
def create_feedback(analysis_run_id: int, feedback_in: FeedbackCreate, db: Session = Depends(get_db)):
    return feedback_service.upsert_feedback(db, analysis_run_id, feedback_in)


@router.get("/analysis/{analysis_run_id}/feedback", response_model=FeedbackRead)
def get_feedback(analysis_run_id: int, db: Session = Depends(get_db)):
    feedback = feedback_service.get_feedback(db, analysis_run_id)
    if feedback is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feedback not found")
    return feedback


@router.get("/feedback", response_model=list[FeedbackRead])
def list_positive_feedback(min_rating: int = 4, db: Session = Depends(get_db)):
    return feedback_service.list_positive_feedback(db, min_rating=min_rating)


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════


def _sse_event(event: str, data: dict) -> str:
    """Format a dict as a Server-Sent Event."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _sleep(seconds: float) -> None:
    """Async sleep for simulating streaming delay."""
    import asyncio
    await asyncio.sleep(seconds)
