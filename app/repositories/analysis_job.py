"""Database access helpers for analysis job persistence and lookup."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import AnalysisJobStatus, UserRole
from app.models.entities import AnalysisJob, Session as SessionEntity
from app.schemas.auth import UserRead


class AnalysisJobRepository:
    """Encapsulate analysis job queries and state persistence."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, job: AnalysisJob) -> AnalysisJob:
        """Persist a new job row and refresh it with DB-managed fields."""

        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def get_by_id(self, job_id: uuid.UUID) -> AnalysisJob | None:
        """Return one analysis job by its primary key."""

        statement = select(AnalysisJob).where(AnalysisJob.id == job_id)
        return self.db.execute(statement).scalar_one_or_none()

    def list_visible(
        self,
        current_user: UserRead,
        session_id: uuid.UUID | None = None,
        status: AnalysisJobStatus | None = None,
    ) -> list[AnalysisJob]:
        """List jobs visible to the current user with optional filters."""

        statement = select(AnalysisJob).join(
            SessionEntity,
            AnalysisJob.session_id == SessionEntity.id,
        )
        if current_user.role != UserRole.ADMIN:
            statement = statement.where(SessionEntity.therapist_id == current_user.id)
        if session_id is not None:
            statement = statement.where(AnalysisJob.session_id == session_id)
        if status is not None:
            statement = statement.where(AnalysisJob.status == status)
        statement = statement.order_by(AnalysisJob.created_at.desc())
        return list(self.db.execute(statement).scalars().all())

    def find_active_for_session(self, session_id: uuid.UUID) -> AnalysisJob | None:
        """Return any still-active job for the given session if it exists."""

        active_statuses = (
            AnalysisJobStatus.REQUESTED,
            AnalysisJobStatus.QUEUED,
            AnalysisJobStatus.PROCESSING,
        )
        statement = (
            select(AnalysisJob)
            .where(
                AnalysisJob.session_id == session_id,
                AnalysisJob.status.in_(active_statuses),
            )
            .order_by(AnalysisJob.created_at.desc())
        )
        return self.db.execute(statement).scalar_one_or_none()

    def update(self, job: AnalysisJob) -> AnalysisJob:
        """Commit mutations on a job row and refresh it."""

        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job
