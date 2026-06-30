"""Report chat and patch-apply endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.db import get_db_session
from app.schemas.auth import UserRead
from app.schemas.report_chat import (
    ChatMessageRequest,
    ChatMessageResponse,
    EvidenceResponse,
    PatchApplyResponse,
)
from app.services.report_chat import ReportChatService

router = APIRouter()


@router.post("/{report_id}/chat/messages", response_model=ChatMessageResponse)
def send_chat_message(
    report_id: uuid.UUID,
    request: ChatMessageRequest,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> ChatMessageResponse:
    service = ReportChatService(db)
    return service.send_message(report_id, request, current_user)


@router.post("/patch-proposals/{patch_id}/apply", response_model=PatchApplyResponse)
def apply_patch_proposal(
    patch_id: uuid.UUID,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> PatchApplyResponse:
    service = ReportChatService(db)
    return service.apply_patch(patch_id, current_user)


@router.get("/{report_id}/chat/evidence", response_model=EvidenceResponse)
def get_evidence(
    report_id: uuid.UUID,
    metric: str | None = Query(default=None),
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> EvidenceResponse:
    service = ReportChatService(db)
    return service.get_evidence(report_id, metric, current_user)