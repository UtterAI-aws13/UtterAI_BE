"""Database access helpers for audio file metadata."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import AudioFileStatus
from app.models.entities import AudioFile


class AudioFileRepository:
    """Encapsulate audio file persistence and lookup operations."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, audio_file: AudioFile) -> AudioFile:
        """Persist a new pending audio row and return the refreshed object."""

        self.db.add(audio_file)
        self.db.commit()
        self.db.refresh(audio_file)
        return audio_file

    def get_by_id(self, audio_file_id: uuid.UUID) -> AudioFile | None:
        """Return an audio row by primary key regardless of status."""

        statement = select(AudioFile).where(AudioFile.id == audio_file_id)
        return self.db.execute(statement).scalar_one_or_none()

    def get_by_s3_key(self, s3_key: str) -> AudioFile | None:
        """Find the pending or uploaded audio row associated with one S3 key."""

        statement = select(AudioFile).where(AudioFile.s3_key == s3_key)
        return self.db.execute(statement).scalar_one_or_none()

    def update(self, audio_file: AudioFile) -> AudioFile:
        """Commit an already-mutated audio row and refresh DB-managed fields."""

        self.db.add(audio_file)
        self.db.commit()
        self.db.refresh(audio_file)
        return audio_file

    def list_active_for_session(self, session_id: uuid.UUID) -> list[AudioFile]:
        """Return non-deleted audio files attached to one session."""

        statement = (
            select(AudioFile)
            .where(
                AudioFile.session_id == session_id,
                AudioFile.status != AudioFileStatus.DELETED,
            )
            .order_by(AudioFile.created_at.desc())
        )
        return list(self.db.execute(statement).scalars().all())
