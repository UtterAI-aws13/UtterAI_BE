"""Database access helpers for report persistence and role-filtered queries."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import ReportStatus, UserRole
from app.models.entities import Report, Session as SessionEntity
from app.schemas.auth import UserRead


class ReportRepository:
    """Wrap report CRUD-style queries behind a small persistence surface."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, report: Report) -> Report:
        """Persist a new report row and refresh it for immediate API use."""

        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        return report

    def update(self, report: Report) -> Report:
        """Commit already-mutated report fields and refresh the row."""

        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        return report

    def get_by_id(self, report_id: uuid.UUID) -> Report | None:
        """Return one report row by primary key."""

        statement = select(Report).where(Report.id == report_id)
        return self.db.execute(statement).scalar_one_or_none()

    def list_visible(
        self,
        current_user: UserRead,
        child_id: uuid.UUID | None = None,
    ) -> list[Report]:
        """List non-deleted reports visible to the current user."""

        statement = select(Report).join(
            SessionEntity,
            Report.session_id == SessionEntity.id,
        ).where(Report.status != ReportStatus.DELETED)
        if current_user.role != UserRole.ADMIN:
            statement = statement.where(SessionEntity.therapist_id == current_user.id)
        if child_id is not None:
            statement = statement.where(SessionEntity.child_id == child_id)
        statement = statement.order_by(Report.created_at.desc())
        return list(self.db.execute(statement).scalars().all())
