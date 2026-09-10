from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.log_entry import LogEntry
from app.schemas.log_entry import LogEntryCreate


def create_log_entry(db: Session, log_in: LogEntryCreate) -> LogEntry:
    data = log_in.model_dump()
    # 入账统一 UTC（F04）：带时区输入换算到 UTC；无时区输入按 UTC 理解（写入约定）。
    # SQLite 按存储文本比较时间，混合偏移量会导致同一时刻排序错乱，故必须归一。
    if data["timestamp"] is None:
        data.pop("timestamp")
    else:
        data["timestamp"] = _normalize_to_utc(data["timestamp"])
    # 送达时间（F04）：服务器接收时刻，客户端不可伪造，与事件时间分开记录
    data["received_at"] = datetime.now(UTC)
    log_entry = LogEntry(**data)
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    return log_entry


def _normalize_to_utc(value: datetime) -> datetime:
    """带时区 → astimezone(UTC)；无时区 → 视为 UTC（写入约定，见 F04）。"""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


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
