from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class IncidentBase(BaseModel):
    service_id: int
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    status: str = Field(default="open", max_length=30)


class IncidentCreate(IncidentBase):
    pass


class IncidentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    service_id: int
    title: str
    description: str | None
    status: str
    created_at: datetime
