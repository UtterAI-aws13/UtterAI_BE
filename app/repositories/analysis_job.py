"""Database access helpers for analysis job persistence and lookup."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import AnalysisJobStatus, UserRole
from app.models.entities import AnalysisJob, Session as SessionEntity
from app.schemas.auth import UserRead

_ACTIVE_STATUSES = (
    AnalysisJobStatus.PENDING,
    AnalysisJobStatus.DOWNLOADING,
    AnalysisJobStatus.PREPROCESSING,
    AnalysisJobStatus.RUNNING_VAD,
    AnalysisJobStatus.RUNNING_DIARIZATION,
    AnalysisJobStatus.RUNNING_ASR,
    AnalysisJobStatus.ALIGNING,
    AnalysisJobStatus.CALCULATING_METRICS,
    AnalysisJobStatus.RUNNING_RAG,
    AnalysisJobStatus.GENERATING_REPORT,
    AnalysisJobStatus.SAVING_RESULT,
    AnalysisJobStatus.RETRYING,
)


class AnalysisJobRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, job: AnalysisJob) -> AnalysisJob:
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def get_by_id(self, job_id: uuid.UUID) -> AnalysisJob | None:
        statement = select(AnalysisJob).where(AnalysisJob.id == job_id)
        return self.db.execute(statement).scalar_one_or_none()

    def list_visible(
        self,
        current_user: UserRead,
        session_id: uuid.UUID | None = None,
        status: AnalysisJobStatus | None = None,
    ) -> list[AnalysisJob]:
        statement = select(AnalysisJob).join(
            SessionEntity,
            AnalysisJob.session_id == SessionEntity.id,
        )
        if current_user.role != UserRole.ADMIN:
            statement = statement.where(SessionEntity.slp_id == current_user.id)
        if session_id is not None:
            statement = statement.where(AnalysisJob.session_id == session_id)
        if status is not None:
            statement = statement.where(AnalysisJob.status == status)
        statement = statement.order_by(AnalysisJob.created_at.desc())
        return list(self.db.execute(statement).scalars().all())

    def find_active_for_session(self, session_id: uuid.UUID) -> AnalysisJob | None:
        statement = (
            select(AnalysisJob)
            .where(
                AnalysisJob.session_id == session_id,
                AnalysisJob.status.in_(_ACTIVE_STATUSES),
            )
            .order_by(AnalysisJob.created_at.desc())
        )
        return self.db.execute(statement).scalar_one_or_none()

    def update(self, job: AnalysisJob) -> AnalysisJob:
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job
