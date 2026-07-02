"""Service-layer logic for report reads and edits."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session as DbSession

from app.core.enums import ReportStatus, SessionStatus, UserRole
from app.models.entities import Session as SessionEntity
from app.repositories.report import ReportRepository
from app.repositories.session import SessionRepository
from app.schemas.auth import UserRead
from app.services.case_index_builder import build_case_index
from app.schemas.report import (
    ReportRead,
    ReportSegmentRead,
    ReportSegmentUpdateRequest,
    ReportStatusUpdateRequest,
)


class ReportService:
    def __init__(self, db: DbSession) -> None:
        self.report_repository = ReportRepository(db)
        self.session_repository = SessionRepository(db)

    def list(
        self,
        current_user: UserRead,
        session_id: uuid.UUID | None = None,
        patient_ref_id: uuid.UUID | None = None,
    ) -> list[ReportRead]:
        if session_id is not None:
            self._get_accessible_session(session_id, current_user)
        reports = self.report_repository.list_visible(current_user, session_id, patient_ref_id)
        return [ReportRead.model_validate(r) for r in reports]

    def get(self, report_id: uuid.UUID, current_user: UserRead) -> ReportRead:
        report = self._get_accessible_report(report_id, current_user)
        return ReportRead.model_validate(report)

    def get_segments(self, report_id: uuid.UUID, current_user: UserRead) -> list[ReportSegmentRead]:
        self._get_accessible_report(report_id, current_user)
        segments = self.report_repository.list_segments(report_id)
        return [ReportSegmentRead.model_validate(s) for s in segments]

    def update_segment(
        self,
        report_id: uuid.UUID,
        segment_id: uuid.UUID,
        request: ReportSegmentUpdateRequest,
        current_user: UserRead,
    ) -> ReportSegmentRead:
        report = self._get_accessible_report(report_id, current_user)
        if report.status in {ReportStatus.FINALIZED, ReportStatus.DELETED}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Finalized or deleted reports cannot be edited.",
            )

        segment = self.report_repository.get_segment_by_id(segment_id)
        if segment is None or segment.report_id != report_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report segment not found.",
            )

        now = datetime.now(UTC)
        if request.content is not None:
            segment.content = request.content
            segment.is_edited = True
            segment.edited_by = current_user.id
            segment.edited_at = now
        if request.title is not None:
            segment.title = request.title

        updated = self.report_repository.update_segment(segment)

        report.updated_at = now
        self.report_repository.update(report)

        return ReportSegmentRead.model_validate(updated)

    def update_status(
        self,
        report_id: uuid.UUID,
        request: ReportStatusUpdateRequest,
        current_user: UserRead,
    ) -> ReportRead:
        report = self._get_accessible_report(report_id, current_user)
        if report.status == ReportStatus.DELETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Deleted reports cannot be updated.",
            )
        was_finalized = report.status == ReportStatus.FINALIZED
        report.status = request.status
        report.updated_at = datetime.now(UTC)
        updated = self.report_repository.update(report)

        # FINALIZED로 전환되는 시점에만 SOAP case index를 만든다 — 초안 단계에서
        # 매번 태깅하면 계속 수정되는 리포트마다 불필요한 재계산이 일어난다.
        if not was_finalized and updated.status == ReportStatus.FINALIZED:
            session = self.session_repository.get_by_id(updated.session_id)
            segments = self.report_repository.list_segments(updated.id)
            if session is not None:
                build_case_index(self.report_repository.db, updated, session, segments)
                self.report_repository.db.commit()

        return ReportRead.model_validate(updated)

    def _get_accessible_session(self, session_id: uuid.UUID, current_user: UserRead) -> SessionEntity:
        session = self.session_repository.get_by_id(session_id)
        if session is None or session.status == SessionStatus.DELETED:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found.",
            )
        if current_user.role == UserRole.ADMIN:
            return session
        if current_user.role == UserRole.SLP and session.slp_id == current_user.id:
            return session
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this report.",
        )

    def _get_accessible_report(self, report_id: uuid.UUID, current_user: UserRead):
        report = self.report_repository.get_by_id(report_id)
        if report is None or report.status == ReportStatus.DELETED:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report not found.",
            )
        self._get_accessible_session(report.session_id, current_user)
        return report
