from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AnalysisJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    incident_id: int
    analysis_run_id: int | None
    status: str
    trigger: str
    current_step: str
    detail: str
    error: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
