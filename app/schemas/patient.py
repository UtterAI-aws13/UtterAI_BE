"""Request and response schemas for patient endpoints."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import PatientStatus


class PatientCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    birth_date: date | None = None
    gender: str | None = Field(default=None, pattern=r'^[MFU]$')
    memo: str | None = None
    slp_id: uuid.UUID | None = None


class PatientUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    birth_date: date | None = None
    gender: str | None = Field(default=None, pattern=r'^[MFU]$')
    memo: str | None = None


class PatientRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    birth_date: date | None
    gender: str | None
    memo: str | None
    created_by_slp_id: uuid.UUID
    current_slp_id: uuid.UUID
    status: PatientStatus
    created_at: datetime
