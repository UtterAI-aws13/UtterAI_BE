"""Request and response schemas for session endpoints."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import SessionStatus


class SessionCreateRequest(BaseModel):
    patient_ref_id: uuid.UUID
    session_date: date
    session_type: str | None = Field(default=None, max_length=100)
    session_goal: str | None = None
    memo: str | None = None


class SessionUpdateRequest(BaseModel):
    session_date: date | None = None
    session_type: str | None = Field(default=None, max_length=100)
    session_goal: str | None = None
    memo: str | None = None
    status: SessionStatus | None = None


class SessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    patient_ref_id: uuid.UUID
    slp_id: uuid.UUID
    session_date: date
    session_type: str | None
    session_goal: str | None
    memo: str | None
    status: SessionStatus
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
