"""Schemas for SOAP note generation and reads."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import SoapNoteStatus


class SoapNoteGenerateRequest(BaseModel):
    """Payload for generating a SOAP draft from session artifacts."""

    session_id: uuid.UUID = Field(alias="sessionId")
    transcript_id: uuid.UUID = Field(alias="transcriptId")
    clinical_analysis_job_id: uuid.UUID | None = Field(default=None, alias="clinicalAnalysisJobId")


class SoapNoteRead(BaseModel):
    """Public SOAP note representation."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    result_id: uuid.UUID | None
    job_id: uuid.UUID | None
    generated_by: uuid.UUID
    subjective: str | None
    objective: str | None
    assessment: str | None
    plan: str | None
    status: SoapNoteStatus
    created_at: datetime
    updated_at: datetime
