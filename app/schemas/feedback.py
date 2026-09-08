"""Pydantic schemas for diagnosis feedback."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.timezone import BeijingTimeMixin


class FeedbackCreate(BaseModel):
    rating: int = Field(ge=1, le=5, description="Rating from 1 (worst) to 5 (best)")
    is_diagnosis_correct: bool = Field(default=True)
    comment: str | None = Field(default=None)


class FeedbackRead(BeijingTimeMixin, BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    analysis_run_id: int
    rating: int
    is_diagnosis_correct: bool
    comment: str | None
    created_at: datetime
