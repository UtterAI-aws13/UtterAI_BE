"""Audio file upload lifecycle endpoints."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.db import get_db_session
from app.schemas.audio import (
    AudioFileCompleteRequest,
    AudioFileRead,
    PresignedUploadRequest,
    PresignedUploadResponse,
)
from app.schemas.auth import UserRead
from app.services.audio import AudioService

router = APIRouter()


@router.post("/presigned-url", response_model=PresignedUploadResponse, status_code=201)
def create_presigned_upload(
    request: PresignedUploadRequest,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> PresignedUploadResponse:
    """Create a pending audio row and return a presigned S3 upload URL."""

    service = AudioService(db)
    return service.create_presigned_upload(request, current_user)


@router.post("/", response_model=AudioFileRead)
def complete_upload(
    request: AudioFileCompleteRequest,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> AudioFileRead:
    """Mark an uploaded S3 object as completed and usable by the backend."""

    service = AudioService(db)
    return service.complete_upload(request, current_user)


@router.get("/{audio_file_id}", response_model=AudioFileRead)
def get_audio_file(
    audio_file_id: uuid.UUID,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> AudioFileRead:
    """Return audio metadata after ownership checks."""

    service = AudioService(db)
    return service.get_audio_file(audio_file_id, current_user)


@router.delete("/{audio_file_id}", response_model=AudioFileRead)
def delete_audio_file(
    audio_file_id: uuid.UUID,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> AudioFileRead:
    """Soft-delete audio metadata for an accessible session."""

    service = AudioService(db)
    return service.delete_audio_file(audio_file_id, current_user)
