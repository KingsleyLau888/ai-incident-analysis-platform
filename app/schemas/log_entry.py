from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LogEntryBase(BaseModel):
    service_id: int
    level: str = Field(default="INFO", max_length=30)
    message: str = Field(..., min_length=1)
    timestamp: datetime | None = None


class LogEntryCreate(LogEntryBase):
    pass


class ExternalLogCreate(BaseModel):
    service_name: str = Field(..., min_length=1, max_length=120)
    level: str = Field(default="INFO", max_length=30)
    message: str = Field(..., min_length=1)
    timestamp: datetime | None = None


class LogEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    service_id: int
    level: str
    message: str
    timestamp: datetime
