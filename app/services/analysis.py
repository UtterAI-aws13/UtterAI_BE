"""Service-layer logic for requesting and tracking analysis jobs."""

from __future__ import annotations

from datetime import UTC, datetime
import uuid

from fastapi import HTTPException, status
from opentelemetry import trace
from sqlalchemy.orm import Session as DbSession

from app.core.config import get_settings
from app.core.enums import AnalysisJobStatus, AudioFileStatus, SessionStatus, UserRole
from app.infrastructure.ai_client.client import AIClient
from app.models.entities import AnalysisJob
from app.observability.metrics import (
    record_analysis_job_created,
    record_analysis_job_dispatch_failed,
    record_analysis_job_dispatched,
)
from app.repositories.analysis_job import AnalysisJobRepository
from app.repositories.audio import AudioFileRepository
from app.repositories.session import SessionRepository
from app.repositories.template import TemplateRepository
from app.schemas.analysis import (
    AnalysisJobCancelResponse,
    AnalysisJobCreateRequest,
    AnalysisJobProgressCallbackRequest,
    AnalysisJobRead,
)
from app.schemas.auth import UserRead

settings = get_settings()

_CANCELLABLE_STATUSES = {
    AnalysisJobStatus.PENDING,
    AnalysisJobStatus.DOWNLOADING,
    AnalysisJobStatus.RETRYING,
}

_TERMINAL_STATUSES = {
    AnalysisJobStatus.CANCELLED,
    AnalysisJobStatus.COMPLETED,
    AnalysisJobStatus.FAILED,
}


class AnalysisJobService:
    def __init__(self, db: DbSession) -> None:
        self.analysis_repository = AnalysisJobRepository(db)
        self.audio_repository = AudioFileRepository(db)
        self.session_repository = SessionRepository(db)
        self.template_repository = TemplateRepository(db)
        self.ai_client = AIClient()

    def create(self, request: AnalysisJobCreateRequest, current_user: UserRead) -> AnalysisJobRead:
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("analysis_job.create") as span:
            session = self._get_accessible_session(request.session_id, current_user)
            span.set_attribute("session.id", str(session.id))
            span.set_attribute("analysis.job.template_requested", request.template_id is not None)

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

            if request.template_id is not None:
                template = self.template_repository.get_by_id(request.template_id)
                if template is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Template not found.",
                    )
                is_accessible = (
                    template.is_system
                    or current_user.role == UserRole.ADMIN
                    or template.owner_id == current_user.id
                )
                if not is_accessible:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="You do not have access to this template.",
                    )
                self.template_repository.increment_use_count(template)

            now = datetime.now(UTC)
            job = AnalysisJob(
                session_id=session.id,
                audio_file_id=audio_file.id,
                status=AnalysisJobStatus.PENDING,
                created_at=now,
            )
            created_job = self.analysis_repository.create(job)
            record_analysis_job_created()

            session.status = SessionStatus.ANALYSIS_REQUESTED
            self.session_repository.update(session)

            dispatch_payload = {
                "jobId": str(created_job.id),
                "sessionId": str(created_job.session_id),
                "audioFileId": str(created_job.audio_file_id),
                "audioObjectKey": audio_file.object_key,
                "progressCallbackUrl": (
                    f"{settings.public_api_base_url.rstrip('/')}"
                    f"/api/v1/internal/analysis-jobs/{created_job.id}/progress"
                ),
            }
            if request.template_id is not None:
                dispatch_payload["templateId"] = str(request.template_id)

            try:
                dispatch_result = self.ai_client.dispatch_analysis_job(dispatch_payload)
            except Exception:
                record_analysis_job_dispatch_failed()
                raise

            if dispatch_result is not None:
                record_analysis_job_dispatched()
                created_job.status = AnalysisJobStatus.DOWNLOADING
                created_job = self.analysis_repository.update(created_job)
                session.status = SessionStatus.ANALYSIS_PROCESSING
                self.session_repository.update(session)
            else:
                span.set_attribute("analysis.job.dispatch.skipped", True)

            return AnalysisJobRead.model_validate(created_job)

    def list(
        self,
        current_user: UserRead,
        session_id: uuid.UUID | None = None,
        status_filter: AnalysisJobStatus | None = None,
    ) -> list[AnalysisJobRead]:
        if session_id is not None:
            self._get_accessible_session(session_id, current_user)
        jobs = self.analysis_repository.list_visible(current_user, session_id, status_filter)
        return [AnalysisJobRead.model_validate(job) for job in jobs]

    def get(self, job_id: uuid.UUID, current_user: UserRead) -> AnalysisJobRead:
        job = self._get_accessible_job(job_id, current_user)
        return AnalysisJobRead.model_validate(job)

    def cancel(self, job_id: uuid.UUID, current_user: UserRead) -> AnalysisJobCancelResponse:
        job = self._get_accessible_job(job_id, current_user)
        if job.status not in _CANCELLABLE_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This analysis job can no longer be cancelled.",
            )

        job.status = AnalysisJobStatus.CANCELLED
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
        job = self.analysis_repository.get_by_id(job_id)
        if job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis job not found.",
            )
        if job.status in _TERMINAL_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Terminal jobs cannot accept progress updates.",
            )
        if request.status in {AnalysisJobStatus.COMPLETED, AnalysisJobStatus.CANCELLED}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Use domain-specific completion or cancellation flows for terminal updates.",
            )

        job.status = request.status
        job.pipeline_stage = request.pipeline_stage
        if request.error_code is not None:
            job.error_code = request.error_code
        if request.error_message is not None:
            job.error_message = request.error_message
        if request.status == AnalysisJobStatus.DOWNLOADING and job.started_at is None:
            job.started_at = datetime.now(UTC)
        updated_job = self.analysis_repository.update(job)

        session = self.session_repository.get_by_id(job.session_id)
        if session is not None and request.status not in _TERMINAL_STATUSES:
            session.status = SessionStatus.ANALYSIS_PROCESSING
            self.session_repository.update(session)

        return AnalysisJobRead.model_validate(updated_job)

    def _get_accessible_session(self, session_id: uuid.UUID, current_user: UserRead):
        session = self.session_repository.get_by_id(session_id)
        if session is None or session.status == SessionStatus.DELETED:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found.",
            )
        if current_user.role == UserRole.ADMIN:
            return session
        if current_user.role == UserRole.THERAPIST and session.slp_id == current_user.id:
            return session
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this session.",
        )

    def _get_accessible_job(self, job_id: uuid.UUID, current_user: UserRead) -> AnalysisJob:
        job = self.analysis_repository.get_by_id(job_id)
        if job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis job not found.",
            )
        self._get_accessible_session(job.session_id, current_user)
        return job
