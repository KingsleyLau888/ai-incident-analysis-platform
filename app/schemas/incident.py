from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.timezone import BeijingTimeMixin


class IncidentBase(BaseModel):
    service_id: int
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    status: str = Field(default="open", max_length=30)
    inferred_issue_type: str | None = Field(default=None, max_length=80)


class IncidentCreate(IncidentBase):
    pass


class IncidentRead(BeijingTimeMixin, BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    service_id: int
    title: str
    description: str | None
    status: str
    inferred_issue_type: str | None
    created_at: datetime
