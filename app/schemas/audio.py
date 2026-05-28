"""Request and response schemas for audio file endpoints."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import AudioFileStatus


class PresignedUploadRequest(BaseModel):
    """Payload for requesting an upload URL before the client sends audio."""

    file_name: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=100)
    session_id: uuid.UUID
    file_size: int | None = Field(default=None, ge=0)


class PresignedUploadResponse(BaseModel):
    """Upload URL response including the created pending audio metadata row."""

    audio_file_id: uuid.UUID
    upload_url: str
    s3_bucket: str
    s3_key: str
    expires_in: int


class AudioFileCompleteRequest(BaseModel):
    """Payload sent after the client finishes uploading to S3."""

    session_id: uuid.UUID
    s3_key: str = Field(min_length=1)
    duration_seconds: float | None = Field(default=None, ge=0)


class AudioFileRead(BaseModel):
    """Public audio metadata returned to clients."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    original_file_name: str
    content_type: str | None
    file_size: int | None
    s3_bucket: str
    s3_key: str
    duration_seconds: float | None
    status: AudioFileStatus
    created_at: datetime
    updated_at: datetime
