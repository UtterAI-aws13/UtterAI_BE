"""Unit tests for ReportChatService business logic."""

import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.core.enums import (
    ReportChatThreadStatus,
    ReportPatchStatus,
    ReportSegmentType,
    ReportStatus,
    SessionStatus,
    UserRole,
    UserStatus,
)
from app.models.entities import (
    Report,
    ReportChatThread,
    ReportChatMessage,
    ReportPatchProposal,
    ReportSegment,
)
from app.models.entities import Session as SessionEntity
from app.schemas.auth import UserRead
from app.schemas.report_chat import ChatMessageRequest
from app.services.report_chat import ReportChatService


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_user(role: UserRole = UserRole.SLP) -> UserRead:
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
    s.patient_ref_id = uuid.uuid4()
    s.status = SessionStatus.REPORT_READY
    return s


def _make_report(session_id: uuid.UUID, version: int = 1) -> MagicMock:
    r = MagicMock(spec=Report)
    r.id = uuid.uuid4()
    r.session_id = session_id
    r.status = ReportStatus.DRAFT
    r.version = version
    r.evidence_chunk_ids = []
    r.updated_at = datetime.now()
    return r


def _make_segment(
    report_id: uuid.UUID,
    seg_type: ReportSegmentType = ReportSegmentType.ASSESSMENT,
) -> MagicMock:
    seg = MagicMock(spec=ReportSegment)
    seg.id = uuid.uuid4()
    seg.report_id = report_id
    seg.segment_type = seg_type
    seg.segment_index = 0
    seg.title = "Assessment"
    seg.ai_content = "원본 AI 내용"
    seg.content = "현재 내용"
    seg.is_edited = False
    seg.edited_by = None
    seg.edited_at = None
    seg.created_at = datetime.now()
    return seg


def _make_thread(report_id: uuid.UUID, therapist_id: uuid.UUID) -> MagicMock:
    t = MagicMock(spec=ReportChatThread)
    t.id = uuid.uuid4()
    t.report_id = report_id
    t.therapist_id = therapist_id
    t.status = ReportChatThreadStatus.ACTIVE
    return t


def _make_patch_proposal(
    thread_id: uuid.UUID,
    report_id: uuid.UUID,
    base_version: int = 1,
    status: ReportPatchStatus = ReportPatchStatus.PENDING,
) -> MagicMock:
    p = MagicMock(spec=ReportPatchProposal)
    p.id = uuid.uuid4()
    p.thread_id = thread_id
    p.report_id = report_id
    p.base_report_version = base_version
    p.target_section = "A"
    p.original_text = "원문"
    p.proposed_text = "수정안"
    p.rationale = "임상적 표현 강화"
    p.evidence_refs = []
    p.status = status
    return p


@pytest.fixture
def db():
    return MagicMock()


@pytest.fixture
def service(db):
    with (
        patch("app.services.report_chat.ReportRepository") as MockReport,
        patch("app.services.report_chat.SessionRepository") as MockSession,
        patch("app.services.report_chat.ReportChatRepository") as MockChat,
    ):
        svc = ReportChatService(db)
        svc._report_repo = MockReport.return_value
        svc._session_repo = MockSession.return_value
        svc._chat_repo = MockChat.return_value
        yield svc


# ── send_message ──────────────────────────────────────────────────────────────

class TestSendMessage:
    def test_returns_no_patch_for_off_topic(self, service):
        user = _make_user()
        session = _make_session(user.id)
        report = _make_report(session.id)
        thread = _make_thread(report.id, user.id)
        assistant_msg = MagicMock(spec=ReportChatMessage)
        assistant_msg.id = uuid.uuid4()

        service._report_repo.get_by_id.return_value = report
        service._session_repo.get_by_id.return_value = session
        service._report_repo.list_segments.return_value = []
        service._chat_repo.get_or_create_thread.return_value = thread
        service._chat_repo.get_recent_messages.return_value = []
        service._chat_repo.save_user_message.return_value = MagicMock()
        service._chat_repo.save_assistant_message.return_value = assistant_msg

        ai_response = {
            "intent": {"intent": "off_topic", "target_section": None, "requires_patch": False},
            "assistant_message": "이 챗봇은 SOAP 리포트 수정만 지원합니다.",
            "patch_proposal": None,
        }

        with patch.object(service, "_call_ai_service", return_value=ai_response):
            result = service.send_message(report.id, ChatMessageRequest(message="저녁 메뉴 추천"), user)

        assert result.patch_proposal is None
        assert result.intent["intent"] == "off_topic"
        service._chat_repo.save_patch_proposal.assert_not_called()

    def test_returns_patch_proposal_for_rewrite_request(self, service):
        user = _make_user()
        session = _make_session(user.id)
        report = _make_report(session.id, version=2)
        thread = _make_thread(report.id, user.id)
        segment = _make_segment(report.id)
        assistant_msg = MagicMock(spec=ReportChatMessage)
        assistant_msg.id = uuid.uuid4()
        saved_proposal = _make_patch_proposal(thread.id, report.id, base_version=2)

        service._report_repo.get_by_id.return_value = report
        service._session_repo.get_by_id.return_value = session
        service._report_repo.list_segments.return_value = [segment]
        service._chat_repo.get_or_create_thread.return_value = thread
        service._chat_repo.get_recent_messages.return_value = []
        service._chat_repo.save_user_message.return_value = MagicMock()
        service._chat_repo.save_assistant_message.return_value = assistant_msg
        service._chat_repo.save_patch_proposal.return_value = saved_proposal

        ai_response = {
            "intent": {"intent": "rewrite_section", "target_section": "A", "requires_patch": True},
            "assistant_message": "A 섹션 수정 제안입니다.",
            "patch_proposal": {
                "target_section": "A",
                "original_text": "원문",
                "proposed_text": "수정안",
                "rationale": "임상 표현 강화",
                "evidence_refs": [],
            },
        }

        with patch.object(service, "_call_ai_service", return_value=ai_response):
            result = service.send_message(
                report.id, ChatMessageRequest(message="A 섹션 더 전문적으로 써줘"), user
            )

        assert result.patch_proposal is not None
        assert result.patch_proposal.target_section == "A"
        assert result.intent["intent"] == "rewrite_section"
        service._chat_repo.save_patch_proposal.assert_called_once()

    def test_raises_404_when_report_not_found(self, service):
        user = _make_user()
        service._report_repo.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc:
            service.send_message(uuid.uuid4(), ChatMessageRequest(message="질문"), user)
        assert exc.value.status_code == 404

    def test_raises_403_when_slp_accesses_other_therapist_report(self, service):
        user = _make_user()
        session = _make_session(uuid.uuid4())  # 다른 SLP 소유
        report = _make_report(session.id)

        service._report_repo.get_by_id.return_value = report
        service._session_repo.get_by_id.return_value = session

        with pytest.raises(HTTPException) as exc:
            service.send_message(report.id, ChatMessageRequest(message="질문"), user)
        assert exc.value.status_code == 403


# ── apply_patch ───────────────────────────────────────────────────────────────

class TestApplyPatch:
    def test_applies_patch_and_increments_version(self, service):
        user = _make_user()
        session = _make_session(user.id)
        report = _make_report(session.id, version=1)
        thread = _make_thread(report.id, user.id)
        proposal = _make_patch_proposal(thread.id, report.id, base_version=1)
        segment = _make_segment(report.id)

        service._chat_repo.get_patch_proposal.return_value = proposal
        service._report_repo.get_by_id.return_value = report
        service._session_repo.get_by_id.return_value = session
        service._chat_repo.get_thread_by_id.return_value = thread
        service._report_repo.list_segments.return_value = [segment]

        updated_report = MagicMock(spec=Report)
        updated_report.id = report.id
        updated_report.version = 2
        service._chat_repo.apply_patch.return_value = (updated_report, MagicMock())

        result = service.apply_patch(proposal.id, user)

        assert result.version == 2
        assert result.updated_sections == ["A"]
        service._chat_repo.apply_patch.assert_called_once()

    def test_raises_404_when_patch_not_found(self, service):
        user = _make_user()
        service._chat_repo.get_patch_proposal.return_value = None

        with pytest.raises(HTTPException) as exc:
            service.apply_patch(uuid.uuid4(), user)
        assert exc.value.status_code == 404

    def test_raises_409_when_patch_already_applied(self, service):
        user = _make_user()
        session = _make_session(user.id)
        report = _make_report(session.id, version=2)
        thread = _make_thread(report.id, user.id)
        proposal = _make_patch_proposal(
            thread.id, report.id, status=ReportPatchStatus.APPLIED
        )

        service._chat_repo.get_patch_proposal.return_value = proposal

        with pytest.raises(HTTPException) as exc:
            service.apply_patch(proposal.id, user)
        assert exc.value.status_code == 409

    def test_raises_409_on_version_mismatch(self, service):
        user = _make_user()
        session = _make_session(user.id)
        report = _make_report(session.id, version=3)  # 현재 version=3
        thread = _make_thread(report.id, user.id)
        proposal = _make_patch_proposal(
            thread.id, report.id, base_version=1  # proposal은 version=1 기준
        )

        service._chat_repo.get_patch_proposal.return_value = proposal
        service._report_repo.get_by_id.return_value = report
        service._session_repo.get_by_id.return_value = session
        service._chat_repo.get_thread_by_id.return_value = thread

        with pytest.raises(HTTPException) as exc:
            service.apply_patch(proposal.id, user)
        assert exc.value.status_code == 409
        assert "version" in exc.value.detail.lower()

    def test_raises_403_when_thread_owner_mismatch(self, service):
        user = _make_user()
        session = _make_session(user.id)
        report = _make_report(session.id, version=1)
        thread = _make_thread(report.id, uuid.uuid4())  # 다른 사람의 thread
        proposal = _make_patch_proposal(thread.id, report.id, base_version=1)

        service._chat_repo.get_patch_proposal.return_value = proposal
        service._report_repo.get_by_id.return_value = report
        service._session_repo.get_by_id.return_value = session
        service._chat_repo.get_thread_by_id.return_value = thread

        with pytest.raises(HTTPException) as exc:
            service.apply_patch(proposal.id, user)
        assert exc.value.status_code == 403