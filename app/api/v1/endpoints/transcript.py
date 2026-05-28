"""Transcript and analysis result callback endpoints."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, verify_internal_token
from app.core.db import get_db_session
from app.schemas.auth import UserRead
from app.schemas.transcript import (
    AnalysisResultCallbackRequest,
    TranscriptBulkUpdateRequest,
    TranscriptConfirmResponse,
    TranscriptRead,
    TranscriptSegmentRead,
    TranscriptSegmentUpdateRequest,
)
from app.services.transcript import TranscriptService

router = APIRouter()
internal_result_router = APIRouter()


@router.get("/{result_id}", response_model=TranscriptRead)
def get_transcript_by_result(
    result_id: uuid.UUID,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> TranscriptRead:
    """Return transcript data using the analysis result identifier."""

    service = TranscriptService(db)
    return service.get_transcript_by_result(result_id, current_user)


@router.patch("/{result_id}/segments/{segment_id}", response_model=TranscriptSegmentRead)
def update_transcript_segment(
    result_id: uuid.UUID,
    segment_id: uuid.UUID,
    request: TranscriptSegmentUpdateRequest,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> TranscriptSegmentRead:
    """Update one transcript segment and preserve edit history."""

    service = TranscriptService(db)
    return service.update_segment(segment_id, request, current_user)


@router.patch("/{result_id}/segments", response_model=TranscriptRead)
def bulk_update_transcript_segments(
    result_id: uuid.UUID,
    request: TranscriptBulkUpdateRequest,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> TranscriptRead:
    """Update multiple transcript segments in one request."""

    service = TranscriptService(db)
    return service.bulk_update_segments(request, current_user)


@router.patch("/{result_id}/confirm", response_model=TranscriptConfirmResponse)
def confirm_transcript(
    result_id: uuid.UUID,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> TranscriptConfirmResponse:
    """Mark transcript segments as confirmed for downstream note generation."""

    service = TranscriptService(db)
    return service.confirm_transcript(result_id, current_user)


@internal_result_router.post("/callback", response_model=TranscriptRead)
def handle_analysis_result_callback(
    request: AnalysisResultCallbackRequest,
    _: str = Depends(verify_internal_token),
    db: Session = Depends(get_db_session),
) -> TranscriptRead:
    """Persist transcript/result data delivered by the AI service."""

    service = TranscriptService(db)
    return service.handle_result_callback(request)
