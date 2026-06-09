"""Database access helpers for transcript and transcript segment persistence."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Transcript, TranscriptSegment


class TranscriptRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, transcript: Transcript) -> Transcript:
        self.db.add(transcript)
        self.db.commit()
        self.db.refresh(transcript)
        return transcript

    def get_by_id(self, transcript_id: uuid.UUID) -> Transcript | None:
        statement = select(Transcript).where(Transcript.id == transcript_id)
        return self.db.execute(statement).scalar_one_or_none()

    def get_by_session_id(self, session_id: uuid.UUID) -> Transcript | None:
        statement = (
            select(Transcript)
            .where(Transcript.session_id == session_id)
            .order_by(Transcript.created_at.desc())
        )
        return self.db.execute(statement).scalar_one_or_none()

    def update(self, transcript: Transcript) -> Transcript:
        self.db.add(transcript)
        self.db.commit()
        self.db.refresh(transcript)
        return transcript

    def list_segments(self, transcript_id: uuid.UUID) -> list[TranscriptSegment]:
        statement = (
            select(TranscriptSegment)
            .where(TranscriptSegment.transcript_id == transcript_id)
            .order_by(TranscriptSegment.segment_index)
        )
        return list(self.db.execute(statement).scalars().all())

    def get_segment_by_id(self, segment_id: uuid.UUID) -> TranscriptSegment | None:
        statement = select(TranscriptSegment).where(TranscriptSegment.id == segment_id)
        return self.db.execute(statement).scalar_one_or_none()

    def create_segment(self, segment: TranscriptSegment) -> TranscriptSegment:
        self.db.add(segment)
        self.db.commit()
        self.db.refresh(segment)
        return segment

    def update_segment(self, segment: TranscriptSegment) -> TranscriptSegment:
        self.db.add(segment)
        self.db.commit()
        self.db.refresh(segment)
        return segment

    def bulk_create_segments(self, segments: list[TranscriptSegment]) -> list[TranscriptSegment]:
        for seg in segments:
            self.db.add(seg)
        self.db.commit()
        for seg in segments:
            self.db.refresh(seg)
        return segments
