from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AnalysisRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    incident_id: int
    issue_type: str
    severity: str
    root_cause_summary: str
    suggested_actions: str
    created_at: datetime
