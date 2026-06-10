"""Unit tests for ReportService business logic."""

import uuid
from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.core.enums import (
    ApprovalAction,
    ReportStatus,
    SessionStatus,
    UserRole,
    UserStatus,
)
from app.models.entities import Report, ReportSegment
from app.models.entities import Session as SessionEntity
from app.schemas.auth import UserRead
from app.schemas.report import (
    ApprovalCreateRequest,
    ReportSegmentUpdateRequest,
    ReportStatusUpdateRequest,
)
from app.services.report import ReportService


def _make_user(role: UserRole = UserRole.THERAPIST) -> UserRead:
    return UserRead(
        id=uuid.uuid4(),
        email="slp@test.com",
        name="Test SLP",
        role=role,
        status=UserStatus.ACTIVE,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


def _make_session(slp_id: uuid.UUID) -> MagicMock:
    s = MagicMock(spec=SessionEntity)
    s.id = uuid.uuid4()
    s.slp_id = slp_id
    s.status = SessionStatus.REPORT_READY
    return s


def _make_report(session_id: uuid.UUID, status: ReportStatus = ReportStatus.DRAFT) -> MagicMock:
    r = MagicMock(spec=Report)
    r.id = uuid.uuid4()
    r.session_id = session_id
    r.status = status
    r.job_id = uuid.uuid4()
    r.template_id = None
    r.model_used = "claude-sonnet-4-6"
    r.clinical_flags = []
    r.evidence_chunk_ids = []
    r.requires_human_review = True
    r.s3_key = None
    r.generated_at = datetime.now()
    r.updated_at = datetime.now()
    return r


def _make_approval(
    report_id: uuid.UUID,
    approved_by: uuid.UUID,
    action: ApprovalAction = ApprovalAction.APPROVED,
) -> MagicMock:
    from app.models.entities import ApprovalHistory
    a = MagicMock(spec=ApprovalHistory)
    a.id = uuid.uuid4()
    a.report_id = report_id
    a.approved_by = approved_by
    a.action = action
    a.comment = None
    a.created_at = datetime.now()
    return a


def _make_segment(report_id: uuid.UUID) -> MagicMock:
    from app.core.enums import ReportSegmentType
    seg = MagicMock(spec=ReportSegment)
    seg.id = uuid.uuid4()
    seg.report_id = report_id
    seg.segment_type = ReportSegmentType.SUBJECTIVE
    seg.segment_index = 0
    seg.title = None
    seg.ai_content = None
    seg.content = None
    seg.is_edited = False
    seg.edited_by = None
    seg.edited_at = None
    seg.created_at = datetime.now()
    return seg


@pytest.fixture
def db():
    return MagicMock()


@pytest.fixture
def service(db):
    with patch("app.services.report.ReportRepository") as MockReport, \
         patch("app.services.report.SessionRepository") as MockSession:
        svc = ReportService(db)
        svc.report_repository = MockReport.return_value
        svc.session_repository = MockSession.return_value
        yield svc


class TestReportServiceAccess:
    def test_raises_404_when_report_not_found(self, service):
        user = _make_user()
        service.report_repository.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc:
            service.get(uuid.uuid4(), user)
        assert exc.value.status_code == 404

    def test_raises_404_for_deleted_report(self, service):
        user = _make_user()
        session = _make_session(user.id)
        report = _make_report(session.id, ReportStatus.DELETED)

        service.report_repository.get_by_id.return_value = report

        with pytest.raises(HTTPException) as exc:
            service.get(report.id, user)
        assert exc.value.status_code == 404

    def test_raises_403_when_slp_accesses_other_session_report(self, service):
        user = _make_user()
        session = _make_session(uuid.uuid4())  # different slp_id
        report = _make_report(session.id)

        service.report_repository.get_by_id.return_value = report
        service.session_repository.get_by_id.return_value = session

        with pytest.raises(HTTPException) as exc:
            service.get(report.id, user)
        assert exc.value.status_code == 403


class TestReportServiceUpdateSegment:
    def test_updates_segment_content_and_marks_edited(self, service):
        user = _make_user()
        session = _make_session(user.id)
        report = _make_report(session.id, ReportStatus.DRAFT)
        segment = _make_segment(report.id)

        service.report_repository.get_by_id.return_value = report
        service.session_repository.get_by_id.return_value = session
        service.report_repository.get_segment_by_id.return_value = segment
        service.report_repository.update_segment.return_value = segment
        service.report_repository.update.return_value = report

        service.update_segment(
            report.id, segment.id,
            ReportSegmentUpdateRequest(content="수정된 내용입니다."),
            user,
        )

        assert segment.content == "수정된 내용입니다."
        assert segment.is_edited is True
        assert segment.edited_by == user.id
        assert segment.edited_at is not None

    def test_raises_400_for_finalized_report(self, service):
        user = _make_user()
        session = _make_session(user.id)
        report = _make_report(session.id, ReportStatus.FINALIZED)

        service.report_repository.get_by_id.return_value = report
        service.session_repository.get_by_id.return_value = session

        with pytest.raises(HTTPException) as exc:
            service.update_segment(
                report.id, uuid.uuid4(),
                ReportSegmentUpdateRequest(content="변경 불가"),
                user,
            )
        assert exc.value.status_code == 400

    def test_raises_404_when_segment_belongs_to_different_report(self, service):
        user = _make_user()
        session = _make_session(user.id)
        report = _make_report(session.id, ReportStatus.REVIEWING)
        segment = _make_segment(uuid.uuid4())  # different report_id

        service.report_repository.get_by_id.return_value = report
        service.session_repository.get_by_id.return_value = session
        service.report_repository.get_segment_by_id.return_value = segment

        with pytest.raises(HTTPException) as exc:
            service.update_segment(
                report.id, segment.id,
                ReportSegmentUpdateRequest(content="변경"),
                user,
            )
        assert exc.value.status_code == 404


class TestReportServiceApproval:
    def test_approved_action_sets_report_status_to_approved(self, service):
        user = _make_user()
        session = _make_session(user.id)
        report = _make_report(session.id, ReportStatus.REVIEWING)
        approval = _make_approval(report.id, user.id, ApprovalAction.APPROVED)

        service.report_repository.get_by_id.return_value = report
        service.session_repository.get_by_id.return_value = session
        service.report_repository.create_approval.return_value = approval
        service.report_repository.update.return_value = report

        service.create_approval(
            report.id,
            ApprovalCreateRequest(action=ApprovalAction.APPROVED, comment="승인"),
            user,
        )

        assert report.status == ReportStatus.APPROVED

    def test_rejected_action_keeps_reviewing_status(self, service):
        user = _make_user()
        session = _make_session(user.id)
        report = _make_report(session.id, ReportStatus.REVIEWING)
        approval = _make_approval(report.id, user.id, ApprovalAction.REJECTED)

        service.report_repository.get_by_id.return_value = report
        service.session_repository.get_by_id.return_value = session
        service.report_repository.create_approval.return_value = approval
        service.report_repository.update.return_value = report

        service.create_approval(
            report.id,
            ApprovalCreateRequest(action=ApprovalAction.REJECTED, comment="수정 필요"),
            user,
        )

        assert report.status == ReportStatus.REVIEWING

    def test_approval_sets_approved_by_to_current_user(self, service):
        user = _make_user()
        session = _make_session(user.id)
        report = _make_report(session.id, ReportStatus.REVIEWING)
        approval = _make_approval(report.id, user.id, ApprovalAction.APPROVED)

        service.report_repository.get_by_id.return_value = report
        service.session_repository.get_by_id.return_value = session
        service.report_repository.create_approval.return_value = approval
        service.report_repository.update.return_value = report

        service.create_approval(
            report.id,
            ApprovalCreateRequest(action=ApprovalAction.APPROVED),
            user,
        )

        created = service.report_repository.create_approval.call_args[0][0]
        assert created.approved_by == user.id
        assert created.action == ApprovalAction.APPROVED
