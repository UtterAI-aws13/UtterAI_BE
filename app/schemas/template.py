"""Request and response schemas for analysis template endpoints."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import TemplateCategory, TemplateStatus


class TemplateCreateRequest(BaseModel):
    """Payload for creating a text-content template."""

    name: str = Field(min_length=1, max_length=255)
    category: TemplateCategory
    content: str = Field(min_length=1)


class TemplateUpdateRequest(BaseModel):
    """Payload for editing an existing template."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    category: TemplateCategory | None = None
    content: str | None = Field(default=None, min_length=1)


class TemplateRead(BaseModel):
    """Public template representation returned to clients."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    therapist_id: uuid.UUID | None
    name: str
    category: TemplateCategory
    content: str | None
    file_original_name: str | None
    is_system: bool
    use_count: int
    status: TemplateStatus
    created_at: datetime
    updated_at: datetime


class TemplateFileUrlResponse(BaseModel):
    """Presigned URL for downloading a template file."""

    url: str
