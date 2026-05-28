"""Schemas for transcript views, edits, and AI result callbacks."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import AnalysisJobStatus, SpeakerRole


class CallbackSpeaker(BaseModel):
    """Speaker row delivered by the AI result callback."""

    label: str = Field(min_length=1, max_length=50)
    role: SpeakerRole = SpeakerRole.UNKNOWN


class CallbackUtterance(BaseModel):
    """Utterance row delivered by the AI result callback."""

    speaker_label: str | None = Field(default=None, max_length=50)
    start_time: float | None = Field(default=None, ge=0)
    end_time: float | None = Field(default=None, ge=0)
    text: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)


class AnalysisResultCallbackRequest(BaseModel):
    """Internal callback payload from the AI service after completion."""

    job_id: uuid.UUID = Field(alias="jobId")
    status: AnalysisJobStatus
    summary: dict[str, Any] | None = None
    metrics: dict[str, Any] | None = None
    interpretation_text: str | None = Field(default=None, alias="interpretationText")
    transcript_s3_key: str | None = Field(default=None, alias="transcriptS3Key")
    metrics_s3_key: str | None = Field(default=None, alias="metricsS3Key")
    raw_result_s3_key: str | None = Field(default=None, alias="rawResultS3Key")
    report_s3_key: str | None = Field(default=None, alias="reportS3Key")
    speakers: list[CallbackSpeaker] = Field(default_factory=list)
    utterances: list[CallbackUtterance] = Field(default_factory=list)


class TranscriptSegmentRead(BaseModel):
    """Segment representation returned to transcript screens."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    speaker_id: uuid.UUID | None
    speaker_label: str | None
    speaker_role: SpeakerRole | None = None
    start_time: float | None
    end_time: float | None
    original_text: str | None
    edited_text: str | None
    final_text: str | None
    confidence: float | None
    is_confirmed: bool
    created_at: datetime
    updated_at: datetime


class TranscriptRead(BaseModel):
    """Transcript view grouped at the session level."""

    session_id: uuid.UUID
    result_id: uuid.UUID | None
    segments: list[TranscriptSegmentRead]


class TranscriptSegmentUpdateRequest(BaseModel):
    """Payload for editing one utterance segment."""

    text: str | None = None
    speaker_role: SpeakerRole | None = None
    edit_reason: str | None = None


class TranscriptBulkUpdateItem(BaseModel):
    """Single item inside a bulk transcript edit payload."""

    segment_id: uuid.UUID
    text: str | None = None
    speaker_role: SpeakerRole | None = None
    edit_reason: str | None = None


class TranscriptBulkUpdateRequest(BaseModel):
    """Payload for editing multiple transcript segments at once."""

    segments: list[TranscriptBulkUpdateItem]


class TranscriptSegmentCreateRequest(BaseModel):
    """Payload for manually adding a missing transcript segment."""

    speaker_label: str | None = Field(default=None, max_length=50)
    speaker_role: SpeakerRole | None = None
    start_time: float | None = Field(default=None, ge=0)
    end_time: float | None = Field(default=None, ge=0)
    text: str | None = None
    edit_reason: str | None = None


class TranscriptConfirmResponse(BaseModel):
    """Response returned after transcript confirmation."""

    session_id: uuid.UUID
    confirmed_segments: int
    message: str
