"""Request and response schemas for analysis job APIs."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import AnalysisJobStatus


class AnalysisJobCreateRequest(BaseModel):
    session_id: uuid.UUID
    audio_file_id: uuid.UUID
    template_id: uuid.UUID | None = None


class AnalysisJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    audio_file_id: uuid.UUID
    status: AnalysisJobStatus
    pipeline_stage: str | None
    error_code: str | None
    error_message: str | None
    retry_count: int
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class AnalysisJobProgressCallbackRequest(BaseModel):
    status: AnalysisJobStatus
    pipeline_stage: str | None = Field(default=None, max_length=255)
    error_code: str | None = Field(default=None, max_length=100)
    error_message: str | None = None


class AnalysisJobCancelResponse(BaseModel):
    job: AnalysisJobRead
    message: str
