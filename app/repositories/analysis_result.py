"""Database access helpers for analysis results and transcript storage."""

from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.entities import AnalysisResult, Speaker, Utterance, UtteranceEditHistory


class AnalysisResultRepository:
    """Persist analysis result summaries and transcript-related rows."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create_result(self, result: AnalysisResult) -> AnalysisResult:
        """Persist an analysis result row and return the refreshed object."""

        self.db.add(result)
        self.db.commit()
        self.db.refresh(result)
        return result

    def get_result_by_id(self, result_id: uuid.UUID) -> AnalysisResult | None:
        """Return one analysis result by primary key."""

        statement = select(AnalysisResult).where(AnalysisResult.id == result_id)
        return self.db.execute(statement).scalar_one_or_none()

    def get_result_by_session_id(self, session_id: uuid.UUID) -> AnalysisResult | None:
        """Return the latest stored analysis result for a session."""

        statement = (
            select(AnalysisResult)
            .where(AnalysisResult.session_id == session_id)
            .order_by(AnalysisResult.created_at.desc())
        )
        return self.db.execute(statement).scalar_one_or_none()

    def list_speakers_by_session(self, session_id: uuid.UUID) -> list[Speaker]:
        """Return ordered speaker mappings for a session transcript."""

        statement = (
            select(Speaker)
            .where(Speaker.session_id == session_id)
            .order_by(Speaker.created_at.asc())
        )
        return list(self.db.execute(statement).scalars().all())

    def create_speaker(self, speaker: Speaker) -> Speaker:
        """Persist one speaker mapping row and refresh it."""

        self.db.add(speaker)
        self.db.commit()
        self.db.refresh(speaker)
        return speaker

    def replace_speakers_and_utterances(
        self,
        session_id: uuid.UUID,
        speakers: list[Speaker],
        utterances: list[Utterance],
    ) -> None:
        """Replace transcript speaker and utterance rows for one session.

        The result callback is treated as the source of truth for the initial
        transcript. Existing generated rows are removed before inserting the new
        ones so repeated callbacks remain idempotent at the session level.
        """

        self.db.execute(delete(Utterance).where(Utterance.session_id == session_id))
        self.db.execute(delete(Speaker).where(Speaker.session_id == session_id))
        for speaker in speakers:
            self.db.add(speaker)
        self.db.flush()
        speaker_map = {speaker.speaker_label: speaker for speaker in speakers}
        for utterance in utterances:
            if utterance.speaker_label is not None and utterance.speaker_label in speaker_map:
                utterance.speaker_id = speaker_map[utterance.speaker_label].id
            self.db.add(utterance)
        self.db.commit()

    def list_utterances_by_session(self, session_id: uuid.UUID) -> list[Utterance]:
        """Return ordered utterances for one session transcript view."""

        statement = (
            select(Utterance)
            .where(Utterance.session_id == session_id)
            .order_by(Utterance.start_time.asc(), Utterance.created_at.asc())
        )
        return list(self.db.execute(statement).scalars().all())

    def get_utterance_by_id(self, utterance_id: uuid.UUID) -> Utterance | None:
        """Return one utterance segment by primary key."""

        statement = select(Utterance).where(Utterance.id == utterance_id)
        return self.db.execute(statement).scalar_one_or_none()

    def get_speaker_by_id(self, speaker_id: uuid.UUID) -> Speaker | None:
        """Return one speaker row by primary key."""

        statement = select(Speaker).where(Speaker.id == speaker_id)
        return self.db.execute(statement).scalar_one_or_none()

    def update_utterance(self, utterance: Utterance) -> Utterance:
        """Commit a mutated utterance and refresh the row."""

        self.db.add(utterance)
        self.db.commit()
        self.db.refresh(utterance)
        return utterance

    def update_speaker(self, speaker: Speaker) -> Speaker:
        """Commit a mutated speaker role mapping and refresh it."""

        self.db.add(speaker)
        self.db.commit()
        self.db.refresh(speaker)
        return speaker

    def create_edit_history(self, history: UtteranceEditHistory) -> UtteranceEditHistory:
        """Persist one transcript edit history entry."""

        self.db.add(history)
        self.db.commit()
        self.db.refresh(history)
        return history

    def delete_utterance(self, utterance: Utterance) -> None:
        """Delete one utterance row and commit the change."""

        self.db.delete(utterance)
        self.db.commit()
