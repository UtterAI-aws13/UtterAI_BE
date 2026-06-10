"""Request and response schemas for template endpoints."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import TemplateStatus, TemplateType


class TemplateCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    template_type: TemplateType = TemplateType.SOAP_NOTE
    description: str | None = None
    sections_json: dict[str, Any] | None = None


class TemplateUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    sections_json: dict[str, Any] | None = None


class TemplateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_id: uuid.UUID | None
    name: str
    description: str | None
    template_type: TemplateType
    sections_json: dict[str, Any] | None
    file_s3_key: str | None
    file_original_name: str | None
    is_system: bool
    use_count: int
    status: TemplateStatus
    created_at: datetime
    updated_at: datetime


class TemplateFileUrlResponse(BaseModel):
    url: str
