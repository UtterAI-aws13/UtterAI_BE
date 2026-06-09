"""Service-layer logic for audio upload lifecycle management."""

from __future__ import annotations

import os
import uuid

from fastapi import HTTPException, status
from opentelemetry import trace
from sqlalchemy.orm import Session as DbSession

from app.core.config import get_settings
from app.core.enums import AudioFileStatus, SessionStatus, UserRole
from app.infrastructure.s3.client import S3Client
from app.models.entities import AudioFile, Child, Session
from app.repositories.audio import AudioFileRepository
from app.repositories.child import ChildRepository
from app.repositories.session import SessionRepository
from app.observability.metrics import record_audio_upload_completed
from app.schemas.audio import (
    AudioFileCompleteRequest,
    AudioFileRead,
    PresignedUploadRequest,
    PresignedUploadResponse,
)
from app.schemas.auth import UserRead

settings = get_settings()


class AudioService:
    """Coordinate S3 upload preparation and audio metadata lifecycle changes."""

    def __init__(self, db: DbSession) -> None:
        self.audio_repository = AudioFileRepository(db)
        self.child_repository = ChildRepository(db)
        self.session_repository = SessionRepository(db)
        self.s3_client = S3Client()

    def create_presigned_upload(
        self,
        request: PresignedUploadRequest,
        current_user: UserRead,
    ) -> PresignedUploadResponse:
        """Create a pending audio row and return a presigned upload URL.

        The metadata row is inserted before the client uploads so the backend
        has a durable record of the intended object key and can complete the
        lifecycle idempotently after S3 upload finishes.
        """

        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("audio_upload.create_presigned") as span:
            session = self._get_accessible_session(request.session_id, current_user)
            object_key = self._build_audio_object_key(
                therapist_id=session.therapist_id,
                child_id=session.child_id,
                session_id=session.id,
                file_name=request.file_name,
            )
            span.set_attribute("session.id", str(session.id))
            span.set_attribute("audio.object_key", object_key)

            audio_file = AudioFile(
                session_id=session.id,
                original_file_name=request.file_name,
                content_type=request.content_type,
                file_size=request.file_size,
                s3_bucket=settings.raw_audio_bucket,
                s3_key=object_key,
                status=AudioFileStatus.PENDING,
            )
            created_audio = self.audio_repository.create(audio_file)

            if session.status == SessionStatus.CREATED:
                session.status = SessionStatus.AUDIO_UPLOADING
                self.session_repository.update(session)

            upload_url = self.s3_client.generate_upload_url(
                bucket=created_audio.s3_bucket,
                key=created_audio.s3_key,
                content_type=request.content_type,
            )
            return PresignedUploadResponse(
                audio_file_id=created_audio.id,
                upload_url=upload_url,
                s3_bucket=created_audio.s3_bucket,
                s3_key=created_audio.s3_key,
                expires_in=settings.presigned_url_expire_seconds,
            )

    def complete_upload(
        self,
        request: AudioFileCompleteRequest,
        current_user: UserRead,
    ) -> AudioFileRead:
        """Mark an uploaded object as complete after verifying it exists in S3.

        This endpoint is designed to be idempotent around the same `s3_key`.
        Repeated completion calls for an already uploaded object return the same
        final metadata instead of creating duplicate rows or invalid transitions.
        """

        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("audio_upload.complete") as span:
            session = self._get_accessible_session(request.session_id, current_user)
            audio_file = self.audio_repository.get_by_s3_key(request.s3_key)
            if audio_file is None or audio_file.session_id != session.id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Pending audio file not found for this session.",
                )

            if audio_file.status == AudioFileStatus.DELETED:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Deleted audio files cannot be completed.",
                )

            if not self.s3_client.object_exists(audio_file.s3_bucket, audio_file.s3_key):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Uploaded object not found in S3.",
                )

            audio_file.duration_seconds = request.duration_seconds
            audio_file.status = AudioFileStatus.UPLOADED
            updated_audio = self.audio_repository.update(audio_file)

            session.status = SessionStatus.AUDIO_UPLOADED
            self.session_repository.update(session)
            record_audio_upload_completed()

            span.set_attribute("audio.file.id", str(updated_audio.id))
            span.set_attribute("audio.duration_seconds", request.duration_seconds)

            return AudioFileRead.model_validate(updated_audio)

    def get_audio_file(self, audio_file_id: uuid.UUID, current_user: UserRead) -> AudioFileRead:
        """Return one accessible audio metadata row."""

        audio_file = self._get_accessible_audio_file(audio_file_id, current_user)
        return AudioFileRead.model_validate(audio_file)

    def delete_audio_file(self, audio_file_id: uuid.UUID, current_user: UserRead) -> AudioFileRead:
        """Soft-delete audio metadata and move session state back if needed."""

        audio_file = self._get_accessible_audio_file(audio_file_id, current_user)
        audio_file.status = AudioFileStatus.DELETED
        updated_audio = self.audio_repository.update(audio_file)

        remaining_audio = self.audio_repository.list_active_for_session(audio_file.session_id)
        session = self.session_repository.get_by_id(audio_file.session_id)
        if session is not None and not remaining_audio:
            session.status = SessionStatus.CREATED
            self.session_repository.update(session)

        return AudioFileRead.model_validate(updated_audio)

    def _get_accessible_audio_file(self, audio_file_id: uuid.UUID, current_user: UserRead) -> AudioFile:
        """Load audio metadata and enforce session ownership/admin override."""

        audio_file = self.audio_repository.get_by_id(audio_file_id)
        if audio_file is None or audio_file.status == AudioFileStatus.DELETED:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Audio file not found.",
            )

        self._get_accessible_session(audio_file.session_id, current_user)
        return audio_file

    def _get_accessible_session(self, session_id: uuid.UUID, current_user: UserRead) -> Session:
        """Load a session and verify the user can operate on its audio."""

        session = self.session_repository.get_by_id(session_id)
        if session is None or session.status == SessionStatus.DELETED:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found.",
            )

        child = self.child_repository.get_by_id(session.child_id)
        if child is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Child profile not found for this session.",
            )

        if current_user.role == UserRole.ADMIN:
            return session

        if current_user.role == UserRole.THERAPIST and session.therapist_id == current_user.id:
            return session

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this session.",
        )

    def _build_audio_object_key(
        self,
        therapist_id: uuid.UUID,
        child_id: uuid.UUID,
        session_id: uuid.UUID,
        file_name: str,
    ) -> str:
        """Generate a controlled S3 object key instead of trusting raw filenames.

        The original client filename is reduced to a sanitized basename and
        random suffix so uploads land in a predictable hierarchy without key
        collisions or direct path injection from user input.
        """

        base_name = os.path.basename(file_name).replace(" ", "_")
        random_suffix = uuid.uuid4().hex[:12]
        return (
            f"raw-audio/{therapist_id}/{child_id}/{session_id}/"
            f"{random_suffix}_{base_name}"
        )
