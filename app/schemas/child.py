"""Request and response schemas for child-profile endpoints."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import ChildStatus


class ChildCreateRequest(BaseModel):
    """Payload for creating a new child profile."""

    name: str = Field(min_length=1, max_length=100)
    birth_date: date | None = None
    gender: str | None = Field(default=None, max_length=20)
    memo: str | None = None
    therapist_id: uuid.UUID | None = None


class ChildUpdateRequest(BaseModel):
    """Payload for updating editable child-profile fields."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    birth_date: date | None = None
    gender: str | None = Field(default=None, max_length=20)
    memo: str | None = None


class ChildRead(BaseModel):
    """Public child-profile shape returned to clients."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    therapist_id: uuid.UUID
    name: str
    birth_date: date | None
    gender: str | None
    memo: str | None
    status: ChildStatus
    created_at: datetime
    updated_at: datetime
