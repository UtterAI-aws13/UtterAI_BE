"""Service-layer logic for analysis result callbacks and transcript editing."""

from __future__ import annotations

from datetime import UTC, datetime
import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session as DbSession

from app.core.enums import AnalysisJobStatus, SessionStatus, SpeakerRole, UserRole
from app.models.entities import AnalysisJob, AnalysisResult, Speaker, Utterance, UtteranceEditHistory
from app.repositories.analysis_job import AnalysisJobRepository
from app.repositories.analysis_result import AnalysisResultRepository
from app.repositories.session import SessionRepository
from app.schemas.auth import UserRead
from app.schemas.transcript import (
    AnalysisResultCallbackRequest,
    TranscriptBulkUpdateRequest,
    TranscriptConfirmResponse,
    TranscriptRead,
    TranscriptSegmentRead,
    TranscriptSegmentUpdateRequest,
)


class TranscriptService:
    """Store AI transcript results and support therapist review/edit workflow."""

    def __init__(self, db: DbSession) -> None:
        self.analysis_job_repository = AnalysisJobRepository(db)
        self.analysis_result_repository = AnalysisResultRepository(db)
        self.session_repository = SessionRepository(db)

    def handle_result_callback(self, request: AnalysisResultCallbackRequest) -> TranscriptRead:
        """Persist completed analysis results and transcript rows from AI callback.

        The callback is treated as the first source of transcript truth. It
        stores summary/metrics plus speaker and utterance rows so later therapist
        review can happen entirely through backend-managed data.
        """

        job = self.analysis_job_repository.get_by_id(request.job_id)
        if job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis job not found.",
            )
        if request.status != AnalysisJobStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only completed analysis callbacks are supported in this flow.",
            )

        result = AnalysisResult(
            job_id=job.id,
            session_id=job.session_id,
            summary_json=request.summary,
            metrics_json=request.metrics,
            interpretation_text=request.interpretation_text,
            transcript_s3_key=request.transcript_s3_key,
            metrics_s3_key=request.metrics_s3_key,
            raw_result_s3_key=request.raw_result_s3_key,
            report_s3_key=request.report_s3_key,
        )
        stored_result = self.analysis_result_repository.create_result(result)

        speakers = [
            Speaker(
                session_id=job.session_id,
                speaker_label=item.label,
                speaker_role=item.role,
            )
            for item in request.speakers
        ]
        utterances = [
            Utterance(
                session_id=job.session_id,
                speaker_label=item.speaker_label,
                # speaker_id is linked after speaker rows are flushed in the repository.
                speaker_id=None,
                start_time=item.start_time,
                end_time=item.end_time,
                original_text=item.text,
                edited_text=None,
                confidence=item.confidence,
                is_confirmed=False,
            )
            for item in request.utterances
        ]

        # Speaker primary keys are assigned after flush during repository replace.
        self.analysis_result_repository.replace_speakers_and_utterances(
            session_id=job.session_id,
            speakers=speakers,
            utterances=utterances,
        )

        job.status = AnalysisJobStatus.COMPLETED
        job.progress = 100
        job.current_stage = "Analysis completed"
        if job.started_at is None:
            job.started_at = datetime.now(UTC)
        job.completed_at = datetime.now(UTC)
        self.analysis_job_repository.update(job)

        session = self.session_repository.get_by_id(job.session_id)
        if session is not None:
            session.status = SessionStatus.ANALYSIS_COMPLETED
            self.session_repository.update(session)

        return self.get_transcript_by_session(job.session_id, current_user=None, allow_internal=True)

    def get_transcript_by_session(
        self,
        session_id: uuid.UUID,
        current_user: UserRead | None,
        allow_internal: bool = False,
    ) -> TranscriptRead:
        """Return transcript segments for one session."""

        session = self._get_accessible_session(session_id, current_user, allow_internal)
        result = self.analysis_result_repository.get_result_by_session_id(session.id)
        utterances = self.analysis_result_repository.list_utterances_by_session(session.id)
        return TranscriptRead(
            session_id=session.id,
            result_id=result.id if result is not None else None,
            segments=[self._build_segment_read(item) for item in utterances],
        )

    def get_transcript_by_result(
        self,
        result_id: uuid.UUID,
        current_user: UserRead,
    ) -> TranscriptRead:
        """Return transcript segments using the analysis result identifier."""

        result = self.analysis_result_repository.get_result_by_id(result_id)
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis result not found.",
            )
        return self.get_transcript_by_session(result.session_id, current_user)

    def update_segment(
        self,
        segment_id: uuid.UUID,
        request: TranscriptSegmentUpdateRequest,
        current_user: UserRead,
    ) -> TranscriptSegmentRead:
        """Update one transcript segment and append edit history."""

        utterance = self._get_accessible_utterance(segment_id, current_user)
        previous_text = utterance.edited_text or utterance.original_text
        previous_role = None
        speaker = None
        if utterance.speaker_id is not None:
            speaker = self.analysis_result_repository.get_speaker_by_id(utterance.speaker_id)
            previous_role = speaker.speaker_role.value if speaker is not None else None

        if request.text is not None:
            utterance.edited_text = request.text
        updated_utterance = self.analysis_result_repository.update_utterance(utterance)

        new_role = previous_role
        if request.speaker_role is not None and speaker is not None:
            speaker.speaker_role = request.speaker_role
            speaker = self.analysis_result_repository.update_speaker(speaker)
            new_role = speaker.speaker_role.value

        history = UtteranceEditHistory(
            utterance_id=updated_utterance.id,
            session_id=updated_utterance.session_id,
            edited_by=current_user.id,
            previous_text=previous_text,
            new_text=updated_utterance.edited_text or updated_utterance.original_text,
            previous_speaker_role=previous_role,
            new_speaker_role=new_role,
            edit_reason=request.edit_reason,
            created_at=datetime.now(UTC),
        )
        self.analysis_result_repository.create_edit_history(history)
        return self._build_segment_read(updated_utterance)

    def bulk_update_segments(
        self,
        request: TranscriptBulkUpdateRequest,
        current_user: UserRead,
    ) -> TranscriptRead:
        """Apply repeated single-segment update logic to multiple segments."""

        session_id: uuid.UUID | None = None
        for item in request.segments:
            updated = self.update_segment(
                item.segment_id,
                TranscriptSegmentUpdateRequest(
                    text=item.text,
                    speaker_role=item.speaker_role,
                    edit_reason=item.edit_reason,
                ),
                current_user,
            )
            session_id = updated.session_id

        if session_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No transcript segments were provided for bulk update.",
            )
        return self.get_transcript_by_session(session_id, current_user)

    def confirm_transcript(
        self,
        result_id: uuid.UUID,
        current_user: UserRead,
    ) -> TranscriptConfirmResponse:
        """Mark every segment in the transcript as confirmed for later note generation."""

        result = self.analysis_result_repository.get_result_by_id(result_id)
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis result not found.",
            )
        transcript = self.get_transcript_by_session(result.session_id, current_user)
        confirmed_count = 0
        for segment in transcript.segments:
            utterance = self.analysis_result_repository.get_utterance_by_id(segment.id)
            if utterance is None:
                continue
            utterance.is_confirmed = True
            self.analysis_result_repository.update_utterance(utterance)
            confirmed_count += 1

        return TranscriptConfirmResponse(
            session_id=result.session_id,
            confirmed_segments=confirmed_count,
            message="Transcript confirmed successfully.",
        )

    def _get_accessible_session(
        self,
        session_id: uuid.UUID,
        current_user: UserRead | None,
        allow_internal: bool = False,
    ):
        """Load a session and enforce therapist ownership unless internal."""

        session = self.session_repository.get_by_id(session_id)
        if session is None or session.status == SessionStatus.DELETED:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found.",
            )
        if allow_internal:
            return session
        if current_user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required.",
            )
        if current_user.role == UserRole.ADMIN:
            return session
        if current_user.role == UserRole.THERAPIST and session.therapist_id == current_user.id:
            return session
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this transcript.",
        )

    def _get_accessible_utterance(self, utterance_id: uuid.UUID, current_user: UserRead) -> Utterance:
        """Load one utterance and enforce access through its parent session."""

        utterance = self.analysis_result_repository.get_utterance_by_id(utterance_id)
        if utterance is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transcript segment not found.",
            )
        self._get_accessible_session(utterance.session_id, current_user)
        return utterance

    def _build_segment_read(self, utterance: Utterance) -> TranscriptSegmentRead:
        """Build transcript segment response data including final text and role."""

        speaker_role = None
        if utterance.speaker_id is not None:
            speaker = self.analysis_result_repository.get_speaker_by_id(utterance.speaker_id)
            speaker_role = speaker.speaker_role if speaker is not None else None

        final_text = utterance.edited_text or utterance.original_text
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
            final_text=final_text,
            confidence=utterance.confidence,
            is_confirmed=utterance.is_confirmed,
            created_at=utterance.created_at,
            updated_at=utterance.updated_at,
        )
