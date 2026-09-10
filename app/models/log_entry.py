from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class LogEntry(Base):
    __tablename__ = "log_entries"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"), index=True)
    level: Mapped[str] = mapped_column(String(30), default="INFO")
    message: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True)
    # 送达时间（F04）：服务器收到日志的时刻，与事件发生时间 timestamp 区分；
    # 老数据由迁移用 timestamp 近似回填，故允许 NULL。
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=True)

    service: Mapped["Service"] = relationship(back_populates="logs")
