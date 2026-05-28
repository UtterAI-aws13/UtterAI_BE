"""Request and response schemas for analysis job APIs."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import AnalysisJobStatus


class AnalysisJobCreateRequest(BaseModel):
    """Payload for creating a new AI analysis request."""

    session_id: uuid.UUID
    audio_file_id: uuid.UUID
    analysis_template: str | None = Field(default=None, max_length=255)


class AnalysisJobRead(BaseModel):
    """Public analysis job representation returned to clients."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    audio_id: uuid.UUID
    external_ai_job_id: str | None
    status: AnalysisJobStatus
    progress: int
    current_stage: str | None
    error_code: str | None
    error_message: str | None
    requested_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AnalysisJobProgressCallbackRequest(BaseModel):
    """Payload used by the AI service to report progress updates."""

    status: AnalysisJobStatus
    progress: int = Field(ge=0, le=100)
    current_stage: str | None = Field(default=None, max_length=255)


class AnalysisJobCancelResponse(BaseModel):
    """Simple response returned when a job is cancelled."""

    job: AnalysisJobRead
    message: str
