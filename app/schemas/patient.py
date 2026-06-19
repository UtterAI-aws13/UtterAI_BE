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
    slp_id: uuid.UUID | None = None  # ADMIN only: assign to specific SLP


class PatientUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    birth_date: date | None = None
    gender: str | None = Field(default=None, pattern=r'^[MFU]$')
    memo: str | None = None


class PatientRead(BaseModel):
    model_config = ConfigDict(from_attributes=False)

    id: uuid.UUID
    patient_ref_id: uuid.UUID
    name: str
    birth_date: date | None
    gender: str | None
    memo: str | None
    status: PatientStatus
    created_by_slp_id: uuid.UUID
    current_slp_id: uuid.UUID
    created_at: datetime
