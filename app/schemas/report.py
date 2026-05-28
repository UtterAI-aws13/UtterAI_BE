"""Schemas for report generation, read, and download flows."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import ReportStatus


class ReportCreateRequest(BaseModel):
    """Payload required to generate a clinician-facing report."""

    session_id: uuid.UUID = Field(alias="sessionId")
    result_id: uuid.UUID = Field(alias="resultId")
    template_type: str = Field(alias="templateType", min_length=1, max_length=100)


class ReportRead(BaseModel):
    """Serialized report representation returned by report APIs."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    result_id: uuid.UUID | None
    soap_note_id: uuid.UUID | None
    generated_by: uuid.UUID
    title: str
    template_type: str
    content: str
    memo: str | None
    status: ReportStatus
    created_at: datetime
    updated_at: datetime
