from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.incident import Incident
from app.schemas.incident import IncidentCreate


def create_incident(db: Session, incident_in: IncidentCreate) -> Incident:
    # 出身字段（F04）：人工接口创建的一律 manual，客户端不可伪造出身
    data = incident_in.model_dump()
    data["source"] = "manual"
    incident = Incident(**data)
    db.add(incident)
    db.commit()
    db.refresh(incident)
    return incident


def list_incidents(
    db: Session, service_id: int | None = None, limit: int | None = None
) -> list[Incident]:
    statement = select(Incident)
    if service_id is not None:
        statement = statement.where(Incident.service_id == service_id)
    if limit is not None:
        # 只取最新 limit 条：按 id 倒序取前 limit 再翻回升序，与旧版 [-limit:] 同序（F14）
        return list(
            reversed(db.scalars(statement.order_by(Incident.id.desc()).limit(limit)).all())
        )
    return list(db.scalars(statement.order_by(Incident.id)).all())


def get_incident(db: Session, incident_id: int) -> Incident | None:
    return db.get(Incident, incident_id)
