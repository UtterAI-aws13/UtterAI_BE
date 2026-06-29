"""Schemas for transcript views, edits, and internal AI worker callbacks."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import AnalysisJobStatus, SpeakerRole, TranscriptStatus


class TranscriptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    audio_file_id: uuid.UUID
    job_id: uuid.UUID
    status: TranscriptStatus
    raw_draft_s3_key: str | None
    final_s3_key: str | None
    finalized_by: uuid.UUID | None
    finalized_at: datetime | None
    created_at: datetime
    updated_at: datetime


class TranscriptSegmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    transcript_id: uuid.UUID
    session_id: uuid.UUID
    segment_index: int
    speaker_label: str | None
    speaker_role: SpeakerRole
    start_ms: int | None
    end_ms: int | None
    original_text: str | None
    text: str | None
    confidence: float | None
    is_edited: bool
    edited_by: uuid.UUID | None
    edited_at: datetime | None
    created_at: datetime


class TranscriptSegmentUpdateRequest(BaseModel):
    text: str | None = None
    speaker_role: SpeakerRole | None = None


class TranscriptBulkUpdateItem(BaseModel):
    segment_id: uuid.UUID
    text: str | None = None
    speaker_role: SpeakerRole | None = None


class TranscriptBulkUpdateRequest(BaseModel):
    segments: list[TranscriptBulkUpdateItem]


class TranscriptSegmentCreateRequest(BaseModel):
    after_segment_id: uuid.UUID
    text: str | None = None


class TranscriptFinalizeRequest(BaseModel):
    template_id: uuid.UUID | None = None


class TranscriptFinalizeResponse(BaseModel):
    transcript_id: uuid.UUID
    status: TranscriptStatus
    message: str


class InternalTranscriptSegmentItem(BaseModel):
    speaker_label: str | None = Field(default=None, max_length=50)
    speaker_role: SpeakerRole = SpeakerRole.UNKNOWN
    start_ms: int | None = None
    end_ms: int | None = None
    original_text: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)


class InternalTranscriptCallbackRequest(BaseModel):
    job_id: uuid.UUID
    status: AnalysisJobStatus
    segments: list[InternalTranscriptSegmentItem] = Field(default_factory=list)
    raw_draft_s3_key: str | None = None
