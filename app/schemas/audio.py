"""Request and response schemas for audio file endpoints."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import AudioFileStatus


class PresignedUploadRequest(BaseModel):
    file_name: str = Field(min_length=1, max_length=255)
    content_type: str = Field(min_length=1, max_length=100)
    session_id: uuid.UUID
    file_size: int | None = Field(default=None, ge=0)


class PresignedUploadResponse(BaseModel):
    audio_file_id: uuid.UUID
    upload_url: str
    object_key: str
    expires_in: int


class AudioFileCompleteRequest(BaseModel):
    session_id: uuid.UUID
    object_key: str = Field(min_length=1)
    actual_size_bytes: int | None = Field(default=None, ge=0)


class AudioFileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    created_by_slp_id: uuid.UUID
    object_key: str
    original_filename: str
    content_type: str | None
    actual_size_bytes: int | None
    presigned_expires_at: datetime | None
    uploaded_at: datetime | None
    status: AudioFileStatus
    created_at: datetime
