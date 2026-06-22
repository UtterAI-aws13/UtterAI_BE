"""Service-layer logic for audio upload lifecycle management."""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from opentelemetry import trace
from sqlalchemy.orm import Session as DbSession

from app.core.config import get_settings
from app.core.enums import AudioFileStatus, SessionStatus, UserRole
from app.infrastructure.s3.client import S3Client
from app.models.entities import AudioFile
from app.observability.metrics import record_audio_upload_completed
from app.repositories.audio import AudioFileRepository
from app.repositories.session import SessionRepository
from app.schemas.audio import (
    AudioFileCompleteRequest,
    AudioFileRead,
    PresignedUploadRequest,
    PresignedUploadResponse,
)
from app.schemas.auth import UserRead

settings = get_settings()


class AudioService:
    def __init__(self, db: DbSession) -> None:
        self.audio_repository = AudioFileRepository(db)
        self.session_repository = SessionRepository(db)
        self.s3_client = S3Client()

    def create_presigned_upload(
        self,
        request: PresignedUploadRequest,
        current_user: UserRead,
    ) -> PresignedUploadResponse:
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("audio_upload.create_presigned") as span:
            session = self._get_accessible_session(request.session_id, current_user)
            object_key = self._build_audio_object_key(
                slp_id=session.slp_id,
                session_id=session.id,
                file_name=request.file_name,
            )
            span.set_attribute("session.id", str(session.id))
            span.set_attribute("audio.object_key", object_key)

            now = datetime.now(UTC)
            audio_file = AudioFile(
                session_id=session.id,
                created_by_slp_id=current_user.id,
                object_key=object_key,
                original_filename=request.file_name,
                content_type=request.content_type,
                status=AudioFileStatus.PENDING_UPLOAD,
                presigned_expires_at=datetime.fromtimestamp(
                    now.timestamp() + settings.presigned_url_expire_seconds, tz=UTC
                ),
                created_at=now,
            )
            created_audio = self.audio_repository.create(audio_file)

            if session.status == SessionStatus.CREATED:
                session.status = SessionStatus.AUDIO_UPLOADING
                self.session_repository.update(session)

            upload_url = self.s3_client.generate_upload_url(
                bucket=settings.s3_bucket_audio,
                key=created_audio.object_key,
                content_type=request.content_type,
            )
            span.set_attribute("audio.file.id", str(created_audio.id))
            return PresignedUploadResponse(
                audio_file_id=created_audio.id,
                upload_url=upload_url,
                object_key=created_audio.object_key,
                expires_in=settings.presigned_url_expire_seconds,
            )

    def complete_upload(
        self,
        request: AudioFileCompleteRequest,
        current_user: UserRead,
    ) -> AudioFileRead:
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("audio_upload.complete") as span:
            session = self._get_accessible_session(request.session_id, current_user)
            audio_file = self.audio_repository.get_by_object_key(request.object_key)
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

            if not self.s3_client.object_exists(settings.s3_bucket_audio, audio_file.object_key):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Uploaded object not found in S3.",
                )

            audio_file.actual_size_bytes = request.actual_size_bytes
            audio_file.status = AudioFileStatus.UPLOADED
            audio_file.uploaded_at = datetime.now(UTC)
            updated_audio = self.audio_repository.update(audio_file)

            session.status = SessionStatus.AUDIO_UPLOADED
            self.session_repository.update(session)
            record_audio_upload_completed()

            span.set_attribute("audio.file.id", str(updated_audio.id))
            if request.actual_size_bytes is not None:
                span.set_attribute("audio.actual_size_bytes", request.actual_size_bytes)

            return AudioFileRead.model_validate(updated_audio)

    def get_audio_file(self, audio_file_id: uuid.UUID, current_user: UserRead) -> AudioFileRead:
        audio_file = self._get_accessible_audio_file(audio_file_id, current_user)
        return AudioFileRead.model_validate(audio_file)

    def delete_audio_file(self, audio_file_id: uuid.UUID, current_user: UserRead) -> AudioFileRead:
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
        audio_file = self.audio_repository.get_by_id(audio_file_id)
        if audio_file is None or audio_file.status == AudioFileStatus.DELETED:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Audio file not found.",
            )
        self._get_accessible_session(audio_file.session_id, current_user)
        return audio_file

    def _get_accessible_session(self, session_id: uuid.UUID, current_user: UserRead):
        session = self.session_repository.get_by_id(session_id)
        if session is None or session.status == SessionStatus.DELETED:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found.",
            )
        if current_user.role == UserRole.ADMIN:
            return session
        if current_user.role == UserRole.SLP and session.slp_id == current_user.id:
            return session
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this session.",
        )

    @staticmethod
    def _build_audio_object_key(
        slp_id: uuid.UUID,
        session_id: uuid.UUID,
        file_name: str,
    ) -> str:
        base_name = os.path.basename(file_name).replace(" ", "_")
        random_suffix = uuid.uuid4().hex[:12]
        return f"raw-audio/{slp_id}/{session_id}/{random_suffix}_{base_name}"
