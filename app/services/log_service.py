from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.log_entry import LogEntry
from app.schemas.log_entry import LogEntryCreate


def create_log_entry(db: Session, log_in: LogEntryCreate) -> LogEntry:
    data = log_in.model_dump()
    if data["timestamp"] is None:
        data.pop("timestamp")
    log_entry = LogEntry(**data)
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    return log_entry


def list_log_entries(
    db: Session, service_id: int | None = None, limit: int | None = None
) -> list[LogEntry]:
    statement = select(LogEntry)
    if service_id is not None:
        statement = statement.where(LogEntry.service_id == service_id)
    if limit is not None:
        # 只取最新 limit 条：按 id 倒序取前 limit 再翻回升序，与旧版 [-limit:] 同序（F14）
        return list(
            reversed(db.scalars(statement.order_by(LogEntry.id.desc()).limit(limit)).all())
        )
    return list(db.scalars(statement.order_by(LogEntry.id)).all())


def get_log_entry(db: Session, log_entry_id: int) -> LogEntry | None:
    return db.get(LogEntry, log_entry_id)
