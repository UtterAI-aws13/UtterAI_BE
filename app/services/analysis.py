"""Service-layer logic for requesting and tracking analysis jobs."""

from __future__ import annotations

from datetime import UTC, datetime
import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session as DbSession

from app.core.config import get_settings
from app.core.enums import AnalysisJobStatus, AudioFileStatus, SessionStatus, UserRole
from app.infrastructure.ai_client.client import AIClient
from app.models.entities import AnalysisJob
from app.repositories.analysis_job import AnalysisJobRepository
from app.repositories.audio import AudioFileRepository
from app.repositories.session import SessionRepository
from app.schemas.analysis import (
    AnalysisJobCancelResponse,
    AnalysisJobCreateRequest,
    AnalysisJobProgressCallbackRequest,
    AnalysisJobRead,
)
from app.schemas.auth import UserRead

settings = get_settings()


class AnalysisJobService:
    """Coordinate job creation, visibility, cancellation, and progress updates."""

    def __init__(self, db: DbSession) -> None:
        self.analysis_repository = AnalysisJobRepository(db)
        self.audio_repository = AudioFileRepository(db)
        self.session_repository = SessionRepository(db)
        self.ai_client = AIClient()

    def create(self, request: AnalysisJobCreateRequest, current_user: UserRead) -> AnalysisJobRead:
        """Create a new analysis job for an uploaded audio file.

        Only uploaded audio can be analyzed. The service also enforces that one
        session cannot have multiple active analysis jobs at the same time.
        """

        session = self._get_accessible_session(request.session_id, current_user)
        audio_file = self.audio_repository.get_by_id(request.audio_file_id)
        if audio_file is None or audio_file.session_id != session.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Audio file not found for this session.",
            )
        if audio_file.status != AudioFileStatus.UPLOADED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only uploaded audio files can be analyzed.",
            )

        active_job = self.analysis_repository.find_active_for_session(session.id)
        if active_job is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An active analysis job already exists for this session.",
            )

        now = datetime.now(UTC)
        job = AnalysisJob(
            session_id=session.id,
            audio_id=audio_file.id,
            status=AnalysisJobStatus.REQUESTED,
            progress=0,
            current_stage="Analysis requested",
            requested_at=now,
        )
        created_job = self.analysis_repository.create(job)

        session.status = SessionStatus.ANALYSIS_REQUESTED
        self.session_repository.update(session)

        dispatch_payload = {
            "jobId": str(created_job.id),
            "sessionId": str(created_job.session_id),
            "audioId": str(created_job.audio_id),
            "audioS3Bucket": audio_file.s3_bucket,
            "audioS3Key": audio_file.s3_key,
            "callbackUrl": (
                f"{settings.public_api_base_url.rstrip('/')}"
                "/api/v1/internal/analysis-results/callback"
            ),
            "progressCallbackUrl": (
                f"{settings.public_api_base_url.rstrip('/')}"
                f"/api/v1/internal/analysis-jobs/{created_job.id}/progress"
            ),
            "analysisTemplate": request.analysis_template,
        }
        dispatch_result = self.ai_client.dispatch_analysis_job(dispatch_payload)
        if dispatch_result is not None:
            created_job.external_ai_job_id = dispatch_result.get("externalAiJobId")
            created_job.status = AnalysisJobStatus.QUEUED
            created_job.current_stage = dispatch_result.get(
                "currentStage",
                "Queued in AI service",
            )
            created_job.progress = int(dispatch_result.get("progress", 0))
            created_job = self.analysis_repository.update(created_job)
            session.status = SessionStatus.ANALYSIS_PROCESSING
            self.session_repository.update(session)

        return AnalysisJobRead.model_validate(created_job)

    def list(
        self,
        current_user: UserRead,
        session_id: uuid.UUID | None = None,
        status_filter: AnalysisJobStatus | None = None,
    ) -> list[AnalysisJobRead]:
        """List analysis jobs visible to the current user."""

        if session_id is not None:
            self._get_accessible_session(session_id, current_user)

        jobs = self.analysis_repository.list_visible(current_user, session_id, status_filter)
        return [AnalysisJobRead.model_validate(job) for job in jobs]

    def get(self, job_id: uuid.UUID, current_user: UserRead) -> AnalysisJobRead:
        """Return one accessible analysis job."""

        job = self._get_accessible_job(job_id, current_user)
        return AnalysisJobRead.model_validate(job)

    def cancel(self, job_id: uuid.UUID, current_user: UserRead) -> AnalysisJobCancelResponse:
        """Cancel an active analysis job if it is still cancellable."""

        job = self._get_accessible_job(job_id, current_user)
        cancellable = {
            AnalysisJobStatus.REQUESTED,
            AnalysisJobStatus.QUEUED,
            AnalysisJobStatus.PROCESSING,
        }
        if job.status not in cancellable:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This analysis job can no longer be cancelled.",
            )

        job.status = AnalysisJobStatus.CANCELLED
        job.current_stage = "Cancelled by user"
        job.completed_at = datetime.now(UTC)
        updated_job = self.analysis_repository.update(job)

        session = self.session_repository.get_by_id(job.session_id)
        if session is not None:
            session.status = SessionStatus.AUDIO_UPLOADED
            self.session_repository.update(session)

        return AnalysisJobCancelResponse(
            job=AnalysisJobRead.model_validate(updated_job),
            message="Analysis job cancelled successfully.",
        )

    def update_progress(
        self,
        job_id: uuid.UUID,
        request: AnalysisJobProgressCallbackRequest,
    ) -> AnalysisJobRead:
        """Apply progress updates from the AI service.

        Progress callbacks must not resurrect terminal jobs. If a job is already
        cancelled or completed, later progress updates are rejected to protect
        state machine consistency.
        """

        job = self.analysis_repository.get_by_id(job_id)
        if job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis job not found.",
            )
        if job.status in {
            AnalysisJobStatus.CANCELLED,
            AnalysisJobStatus.COMPLETED,
            AnalysisJobStatus.FAILED,
            AnalysisJobStatus.EXPIRED,
        }:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Terminal jobs cannot accept progress updates.",
            )

        if request.status in {
            AnalysisJobStatus.COMPLETED,
            AnalysisJobStatus.CANCELLED,
            AnalysisJobStatus.EXPIRED,
        }:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Use domain-specific completion or cancellation flows for terminal updates.",
            )

        job.status = request.status
        job.progress = request.progress
        job.current_stage = request.current_stage
        if request.status == AnalysisJobStatus.PROCESSING and job.started_at is None:
            job.started_at = datetime.now(UTC)
        updated_job = self.analysis_repository.update(job)

        session = self.session_repository.get_by_id(job.session_id)
        if session is not None and request.status in {
            AnalysisJobStatus.QUEUED,
            AnalysisJobStatus.PROCESSING,
        }:
            session.status = SessionStatus.ANALYSIS_PROCESSING
            self.session_repository.update(session)

        return AnalysisJobRead.model_validate(updated_job)

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
            detail="You do not have access to this session.",
        )

    def _get_accessible_job(self, job_id: uuid.UUID, current_user: UserRead) -> AnalysisJob:
        """Load a job and enforce visibility through the owning session."""

        job = self.analysis_repository.get_by_id(job_id)
        if job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis job not found.",
            )
        self._get_accessible_session(job.session_id, current_user)
        return job
