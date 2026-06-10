"""Database access helpers for report persistence."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import ReportStatus, UserRole
from app.models.entities import Report, ReportSegment, Session as SessionEntity
from app.schemas.auth import UserRead


class ReportRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, report: Report) -> Report:
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        return report

    def update(self, report: Report) -> Report:
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        return report

    def get_by_id(self, report_id: uuid.UUID) -> Report | None:
        statement = select(Report).where(Report.id == report_id)
        return self.db.execute(statement).scalar_one_or_none()

    def list_visible(
        self,
        current_user: UserRead,
        session_id: uuid.UUID | None = None,
        patient_ref_id: uuid.UUID | None = None,
    ) -> list[Report]:
        statement = (
            select(Report)
            .join(SessionEntity, Report.session_id == SessionEntity.id)
            .where(Report.status != ReportStatus.DELETED)
        )
        if current_user.role != UserRole.ADMIN:
            statement = statement.where(SessionEntity.slp_id == current_user.id)
        if session_id is not None:
            statement = statement.where(Report.session_id == session_id)
        if patient_ref_id is not None:
            statement = statement.where(SessionEntity.patient_ref_id == patient_ref_id)
        statement = statement.order_by(Report.updated_at.desc())
        return list(self.db.execute(statement).scalars().all())

    def list_segments(self, report_id: uuid.UUID) -> list[ReportSegment]:
        statement = (
            select(ReportSegment)
            .where(ReportSegment.report_id == report_id)
            .order_by(ReportSegment.segment_index)
        )
        return list(self.db.execute(statement).scalars().all())

    def get_segment_by_id(self, segment_id: uuid.UUID) -> ReportSegment | None:
        statement = select(ReportSegment).where(ReportSegment.id == segment_id)
        return self.db.execute(statement).scalar_one_or_none()

    def update_segment(self, segment: ReportSegment) -> ReportSegment:
        self.db.add(segment)
        self.db.commit()
        self.db.refresh(segment)
        return segment

