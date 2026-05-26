from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.incident import Incident
from app.schemas.incident import IncidentCreate


def create_incident(db: Session, incident_in: IncidentCreate) -> Incident:
    incident = Incident(**incident_in.model_dump())
    db.add(incident)
    db.commit()
    db.refresh(incident)
    return incident


def list_incidents(db: Session, service_id: int | None = None) -> list[Incident]:
    statement = select(Incident)
    if service_id is not None:
        statement = statement.where(Incident.service_id == service_id)
    return list(db.scalars(statement.order_by(Incident.id)).all())


def get_incident(db: Session, incident_id: int) -> Incident | None:
    return db.get(Incident, incident_id)
