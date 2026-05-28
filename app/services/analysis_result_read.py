"""Read-only service logic for analysis result APIs."""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status

from app.core.enums import SessionStatus, UserRole
from app.repositories.analysis_result import AnalysisResultRepository
from app.repositories.session import SessionRepository
from app.schemas.analysis_result import (
    AnalysisMetricsRead,
    AnalysisResultRead,
    AnalysisResultSpeakerListRead,
    AnalysisResultSpeakerRead,
    AnalysisResultTranscriptRead,
)
from app.schemas.auth import UserRead
from app.schemas.transcript import TranscriptSegmentRead


class AnalysisResultReadService:
    """Provide access-controlled read APIs for stored analysis results."""

    def __init__(self, db) -> None:
        self.analysis_result_repository = AnalysisResultRepository(db)
        self.session_repository = SessionRepository(db)

    def get_result(self, result_id: uuid.UUID, current_user: UserRead) -> AnalysisResultRead:
        """Return one analysis result after session-level access checks."""

        result = self.analysis_result_repository.get_result_by_id(result_id)
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis result not found.",
            )
        self._get_accessible_session(result.session_id, current_user)
        return AnalysisResultRead.model_validate(result)

    def get_result_by_session(
        self,
        session_id: uuid.UUID,
        current_user: UserRead,
    ) -> AnalysisResultRead:
        """Return the latest analysis result for a session."""

        self._get_accessible_session(session_id, current_user)
        result = self.analysis_result_repository.get_result_by_session_id(session_id)
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis result not found for this session.",
            )
        return AnalysisResultRead.model_validate(result)

    def get_metrics(self, result_id: uuid.UUID, current_user: UserRead) -> AnalysisMetricsRead:
        """Return only the metrics payload for one analysis result."""

        result = self.analysis_result_repository.get_result_by_id(result_id)
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis result not found.",
            )
        self._get_accessible_session(result.session_id, current_user)
        return AnalysisMetricsRead(
            result_id=result.id,
            session_id=result.session_id,
            metrics=result.metrics_json,
        )

    def get_transcript(
        self,
        result_id: uuid.UUID,
        current_user: UserRead,
    ) -> AnalysisResultTranscriptRead:
        """Return transcript segments under the analysis-results namespace."""

        result = self.analysis_result_repository.get_result_by_id(result_id)
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis result not found.",
            )
        self._get_accessible_session(result.session_id, current_user)
        utterances = self.analysis_result_repository.list_utterances_by_session(result.session_id)
        return AnalysisResultTranscriptRead(
            result_id=result.id,
            session_id=result.session_id,
            segments=[self._build_segment_read(item) for item in utterances],
        )

    def get_speakers(
        self,
        result_id: uuid.UUID,
        current_user: UserRead,
    ) -> AnalysisResultSpeakerListRead:
        """Return speaker-role mappings and simple counts for one result."""

        result = self.analysis_result_repository.get_result_by_id(result_id)
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis result not found.",
            )
        self._get_accessible_session(result.session_id, current_user)
        speakers = self.analysis_result_repository.list_speakers_by_session(result.session_id)
        utterances = self.analysis_result_repository.list_utterances_by_session(result.session_id)

        utterance_counts: dict[uuid.UUID, int] = {}
        for utterance in utterances:
            if utterance.speaker_id is None:
                continue
            utterance_counts[utterance.speaker_id] = utterance_counts.get(utterance.speaker_id, 0) + 1

        return AnalysisResultSpeakerListRead(
            result_id=result.id,
            session_id=result.session_id,
            speakers=[
                AnalysisResultSpeakerRead(
                    speaker_id=speaker.id,
                    session_id=speaker.session_id,
                    speaker_label=speaker.speaker_label,
                    speaker_role=speaker.speaker_role,
                    utterance_count=utterance_counts.get(speaker.id, 0),
                )
                for speaker in speakers
            ],
        )

    def _get_accessible_session(self, session_id: uuid.UUID, current_user: UserRead):
        """Load a session and enforce therapist ownership or admin override."""

        session = self.session_repository.get_by_id(session_id)
        if session is None or session.status == SessionStatus.DELETED:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found.",
            )
        if current_user.role == UserRole.ADMIN:
            return session
        if current_user.role == UserRole.THERAPIST and session.therapist_id == current_user.id:
            return session
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this analysis result.",
        )

    def _build_segment_read(self, utterance) -> TranscriptSegmentRead:
        """Build transcript segment output with final text and speaker role."""

        speaker_role = None
        if utterance.speaker_id is not None:
            speaker = self.analysis_result_repository.get_speaker_by_id(utterance.speaker_id)
            speaker_role = speaker.speaker_role if speaker is not None else None

        return TranscriptSegmentRead(
            id=utterance.id,
            session_id=utterance.session_id,
            speaker_id=utterance.speaker_id,
            speaker_label=utterance.speaker_label,
            speaker_role=speaker_role,
            start_time=utterance.start_time,
            end_time=utterance.end_time,
            original_text=utterance.original_text,
            edited_text=utterance.edited_text,
            final_text=utterance.edited_text or utterance.original_text,
            confidence=utterance.confidence,
            is_confirmed=utterance.is_confirmed,
            created_at=utterance.created_at,
            updated_at=utterance.updated_at,
        )
