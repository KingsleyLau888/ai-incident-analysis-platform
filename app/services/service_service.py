from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.service import Service
from app.schemas.service import ServiceCreate


def create_service(db: Session, service_in: ServiceCreate) -> Service:
    service = Service(**service_in.model_dump())
    db.add(service)
    db.commit()
    db.refresh(service)
    return service


def list_services(db: Session) -> list[Service]:
    return list(db.scalars(select(Service).order_by(Service.id)).all())


def get_service(db: Session, service_id: int) -> Service | None:
    return db.get(Service, service_id)
