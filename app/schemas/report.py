"""Schemas for report, report segment, and approval APIs."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.core.enums import ApprovalAction, ReportSegmentType, ReportStatus


class ReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    job_id: uuid.UUID
    template_id: uuid.UUID | None
    status: ReportStatus
    model_used: str | None
    clinical_flags: list[Any] | None
    evidence_chunk_ids: list[Any] | None
    requires_human_review: bool
    s3_key: str | None
    generated_at: datetime | None
    updated_at: datetime


class ReportSegmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    report_id: uuid.UUID
    segment_type: ReportSegmentType
    segment_index: int
    title: str | None
    ai_content: str | None
    content: str | None
    is_edited: bool
    edited_by: uuid.UUID | None
    edited_at: datetime | None
    created_at: datetime


class ReportSegmentUpdateRequest(BaseModel):
    content: str | None = None
    title: str | None = None


class ReportStatusUpdateRequest(BaseModel):
    status: ReportStatus


class ApprovalHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    report_id: uuid.UUID
    approved_by: uuid.UUID
    action: ApprovalAction
    comment: str | None
    created_at: datetime


class ApprovalCreateRequest(BaseModel):
    action: ApprovalAction
    comment: str | None = None
