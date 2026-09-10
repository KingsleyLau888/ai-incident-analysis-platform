from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="open", index=True)
    # 初步类型（创建时推断）：自动去重不依赖尚未生成的分析结果（F03）
    inferred_issue_type: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    # 出身（F04）：automatic=自动爆发检测创建，manual=人工创建；
    # 分析窗口语义看出身，不再看标题前缀。老数据由迁移按标题回填。
    source: Mapped[str] = mapped_column(String(20), default="manual", nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    service: Mapped["Service"] = relationship(back_populates="incidents")
    analysis_runs: Mapped[list["AnalysisRun"]] = relationship(back_populates="incident")
