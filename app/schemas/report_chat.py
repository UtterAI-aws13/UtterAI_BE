"""Schemas for report chat thread, messages, and patch proposals."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.core.enums import ReportPatchStatus


class ChatMessageRequest(BaseModel):
    message: str


class PatchProposalRead(BaseModel):
    patch_id: uuid.UUID
    target_section: str
    original_text: str
    proposed_text: str
    rationale: str | None
    evidence_refs: list
    base_report_version: int
    status: ReportPatchStatus

    model_config = {"from_attributes": True}


class ChatMessageResponse(BaseModel):
    thread_id: uuid.UUID
    assistant_message: str
    intent: dict | None
    patch_proposal: PatchProposalRead | None


class PatchApplyRequest(BaseModel):
    confirm: bool


class PatchApplyResponse(BaseModel):
    report_id: uuid.UUID
    version: int
    updated_sections: list[str]


class EvidenceItem(BaseModel):
    title: str | None
    section: str | None
    summary: str
    source_id: str | None
    page: int | None


class PatientEvidenceItem(BaseModel):
    type: str
    summary: str


class EvidenceResponse(BaseModel):
    literature_evidence: list[EvidenceItem]
    patient_evidence: list[PatientEvidenceItem]