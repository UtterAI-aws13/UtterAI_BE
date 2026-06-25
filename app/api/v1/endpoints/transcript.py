"""Transcript read, segment edit, finalize, and internal callback endpoints."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, verify_internal_token
from app.core.db import get_db_session
from app.schemas.auth import UserRead
from app.schemas.transcript import (
    InternalTranscriptCallbackRequest,
    TranscriptBulkUpdateRequest,
    TranscriptFinalizeRequest,
    TranscriptFinalizeResponse,
    TranscriptRead,
    TranscriptSegmentRead,
    TranscriptSegmentUpdateRequest,
)
from app.services.transcript import TranscriptService

router = APIRouter()
internal_result_router = APIRouter()


@router.get("/{transcript_id}", response_model=TranscriptRead)
def get_transcript(
    transcript_id: uuid.UUID,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> TranscriptRead:
    service = TranscriptService(db)
    return service.get_by_id(transcript_id, current_user)


@router.get("/{transcript_id}/segments", response_model=list[TranscriptSegmentRead])
def list_transcript_segments(
    transcript_id: uuid.UUID,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> list[TranscriptSegmentRead]:
    service = TranscriptService(db)
    return service.list_segments(transcript_id, current_user)


@router.patch("/{transcript_id}/segments/{segment_id}", response_model=TranscriptSegmentRead)
def update_transcript_segment(
    transcript_id: uuid.UUID,
    segment_id: uuid.UUID,
    request: TranscriptSegmentUpdateRequest,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> TranscriptSegmentRead:
    service = TranscriptService(db)
    return service.update_segment(transcript_id, segment_id, request, current_user)


@router.delete("/{transcript_id}/segments/{segment_id}", status_code=204)
def delete_transcript_segment(
    transcript_id: uuid.UUID,
    segment_id: uuid.UUID,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> None:
    service = TranscriptService(db)
    service.delete_segment(transcript_id, segment_id, current_user)


@router.patch("/{transcript_id}/segments", response_model=list[TranscriptSegmentRead])
def bulk_update_transcript_segments(
    transcript_id: uuid.UUID,
    request: TranscriptBulkUpdateRequest,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> list[TranscriptSegmentRead]:
    service = TranscriptService(db)
    return service.bulk_update_segments(transcript_id, request, current_user)


@router.post("/{transcript_id}/finalize", response_model=TranscriptFinalizeResponse)
def finalize_transcript(
    transcript_id: uuid.UUID,
    request: TranscriptFinalizeRequest = TranscriptFinalizeRequest(),
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> TranscriptFinalizeResponse:
    service = TranscriptService(db)
    return service.finalize(transcript_id, current_user, template_id=request.template_id)


@internal_result_router.post("/callback", response_model=TranscriptRead)
def handle_analysis_result_callback(
    request: InternalTranscriptCallbackRequest,
    _: str = Depends(verify_internal_token),
    db: Session = Depends(get_db_session),
) -> TranscriptRead:
    """Persist transcript data delivered by the AI worker (dev/test tooling)."""
    service = TranscriptService(db)
    return service.handle_internal_callback(request)
