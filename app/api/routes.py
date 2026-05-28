from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.analysis import AnalysisRunRead, AnalysisTraceRead
from app.schemas.incident import IncidentCreate, IncidentRead
from app.schemas.log_entry import LogEntryCreate, LogEntryRead
from app.schemas.service import ServiceCreate, ServiceRead
from app.services import analysis_service, incident_service, log_service, service_service

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


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


@router.post("/incidents/{incident_id}/analyze", response_model=AnalysisRunRead, status_code=status.HTTP_201_CREATED)
def analyze_incident(incident_id: int, db: Session = Depends(get_db)):
    incident = incident_service.get_incident(db, incident_id)
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    return analysis_service.analyze_incident(db, incident)


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
