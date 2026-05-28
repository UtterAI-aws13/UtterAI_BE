"""Request and response schemas for session endpoints."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import SessionStatus


class SessionCreateRequest(BaseModel):
    """Payload for creating a session tied to an existing child."""

    child_id: uuid.UUID
    session_date: date
    session_type: str | None = Field(default=None, max_length=100)
    memo: str | None = None


class SessionUpdateRequest(BaseModel):
    """Payload for updating editable session metadata."""

    session_date: date | None = None
    session_type: str | None = Field(default=None, max_length=100)
    memo: str | None = None
    status: SessionStatus | None = None


class SessionRead(BaseModel):
    """Public session shape returned to clients."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    child_id: uuid.UUID
    therapist_id: uuid.UUID
    session_date: date
    session_type: str | None
    memo: str | None
    status: SessionStatus
    created_at: datetime
    updated_at: datetime
