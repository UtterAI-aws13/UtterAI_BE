"""Database access helpers for audio file metadata."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import AudioFileStatus
from app.models.entities import AudioFile


class AudioFileRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, audio_file: AudioFile) -> AudioFile:
        self.db.add(audio_file)
        self.db.commit()
        self.db.refresh(audio_file)
        return audio_file

    def get_by_id(self, audio_file_id: uuid.UUID) -> AudioFile | None:
        statement = select(AudioFile).where(AudioFile.id == audio_file_id)
        return self.db.execute(statement).scalar_one_or_none()

    def get_by_object_key(self, object_key: str) -> AudioFile | None:
        statement = select(AudioFile).where(AudioFile.object_key == object_key)
        return self.db.execute(statement).scalar_one_or_none()

    def update(self, audio_file: AudioFile) -> AudioFile:
        self.db.add(audio_file)
        self.db.commit()
        self.db.refresh(audio_file)
        return audio_file

    def list_active_for_session(self, session_id: uuid.UUID) -> list[AudioFile]:
        statement = (
            select(AudioFile)
            .where(
                AudioFile.session_id == session_id,
                AudioFile.status != AudioFileStatus.DELETED,
            )
            .order_by(AudioFile.created_at.desc())
        )
        return list(self.db.execute(statement).scalars().all())
