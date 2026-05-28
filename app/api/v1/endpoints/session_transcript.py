"""Session-centric transcript lookup endpoints."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.db import get_db_session
from app.schemas.auth import UserRead
from app.schemas.transcript import TranscriptRead
from app.services.transcript import TranscriptService

router = APIRouter()


@router.get("/{session_id}/transcript", response_model=TranscriptRead)
def get_session_transcript(
    session_id: uuid.UUID,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> TranscriptRead:
    """Return transcript data grouped by session id."""

    service = TranscriptService(db)
    return service.get_transcript_by_session(session_id, current_user)
