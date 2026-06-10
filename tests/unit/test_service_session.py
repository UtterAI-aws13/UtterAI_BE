"""Unit tests for SessionService business logic."""

import uuid
from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.core.enums import SessionStatus, UserRole, UserStatus
from app.models.entities import Session as SessionEntity
from app.schemas.auth import UserRead
from app.schemas.session import SessionCreateRequest, SessionUpdateRequest
from app.services.session import SessionService


def _make_user(role: UserRole = UserRole.THERAPIST) -> UserRead:
    return UserRead(
        id=uuid.uuid4(),
        email="slp@test.com",
        name="Test SLP",
        role=role,
        status=UserStatus.ACTIVE,
        created_at=__import__("datetime").datetime.now(),
        updated_at=__import__("datetime").datetime.now(),
    )


def _make_session(slp_id: uuid.UUID, status: SessionStatus = SessionStatus.CREATED) -> SessionEntity:
    s = MagicMock(spec=SessionEntity)
    s.id = uuid.uuid4()
    s.slp_id = slp_id
    s.status = status
    s.patient_ref_id = uuid.uuid4()
    s.session_date = date.today()
    s.session_type = None
    s.session_goal = None
    s.memo = None
    s.completed_at = None
    return s


@pytest.fixture
def db():
    return MagicMock()


@pytest.fixture
def service(db):
    with patch("app.services.session.PatientRefRepository") as MockPatient, \
         patch("app.services.session.SessionRepository") as MockSession:
        svc = SessionService(db)
        svc.patient_ref_repository = MockPatient.return_value
        svc.session_repository = MockSession.return_value
        yield svc


class TestSessionServiceCreate:
    def test_raises_404_when_patient_ref_not_found(self, service):
        service.patient_ref_repository.get_by_id.return_value = None
        user = _make_user()

        with pytest.raises(HTTPException) as exc:
            service.create(
                SessionCreateRequest(patient_ref_id=uuid.uuid4(), session_date=date.today()),
                user,
            )
        assert exc.value.status_code == 404

    def test_creates_session_with_slp_id_from_current_user(self, service):
        user = _make_user()
        service.patient_ref_repository.get_by_id.return_value = MagicMock()

        created = _make_session(user.id)
        service.session_repository.create.return_value = created

        req = SessionCreateRequest(
            patient_ref_id=uuid.uuid4(),
            session_date=date.today(),
            session_goal="발화 수 늘리기",
        )
        service.create(req, user)

        call_args = service.session_repository.create.call_args[0][0]
        assert call_args.slp_id == user.id
        assert call_args.session_goal == "발화 수 늘리기"
        assert call_args.status == SessionStatus.CREATED


class TestSessionServiceList:
    def test_therapist_filters_by_own_slp_id(self, service):
        user = _make_user(UserRole.THERAPIST)
        service.session_repository.list_active.return_value = []

        service.list(user)

        service.session_repository.list_active.assert_called_once_with(
            slp_id=user.id,
            patient_ref_id=None,
        )

    def test_admin_does_not_filter_by_slp_id(self, service):
        user = _make_user(UserRole.ADMIN)
        service.session_repository.list_active.return_value = []

        service.list(user)

        service.session_repository.list_active.assert_called_once_with(
            patient_ref_id=None,
        )

    def test_viewer_raises_403(self, service):
        user = _make_user(UserRole.VIEWER)
        with pytest.raises(HTTPException) as exc:
            service.list(user)
        assert exc.value.status_code == 403


class TestSessionServiceGet:
    def test_admin_can_access_any_session(self, service):
        admin = _make_user(UserRole.ADMIN)
        session = _make_session(uuid.uuid4())  # different slp_id
        service.session_repository.get_by_id.return_value = session

        result = service._get_accessible_session(session.id, admin)
        assert result is session

    def test_therapist_can_access_own_session(self, service):
        user = _make_user()
        session = _make_session(user.id)
        service.session_repository.get_by_id.return_value = session

        result = service._get_accessible_session(session.id, user)
        assert result is session

    def test_therapist_cannot_access_other_session(self, service):
        user = _make_user()
        session = _make_session(uuid.uuid4())  # different owner
        service.session_repository.get_by_id.return_value = session

        with pytest.raises(HTTPException) as exc:
            service._get_accessible_session(session.id, user)
        assert exc.value.status_code == 403

    def test_deleted_session_raises_404(self, service):
        user = _make_user()
        session = _make_session(user.id, status=SessionStatus.DELETED)
        service.session_repository.get_by_id.return_value = session

        with pytest.raises(HTTPException) as exc:
            service._get_accessible_session(session.id, user)
        assert exc.value.status_code == 404

    def test_missing_session_raises_404(self, service):
        user = _make_user()
        service.session_repository.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc:
            service._get_accessible_session(uuid.uuid4(), user)
        assert exc.value.status_code == 404


class TestSessionServiceUpdate:
    def test_cannot_set_status_to_deleted_via_update(self, service):
        user = _make_user()
        session = _make_session(user.id)
        service.session_repository.get_by_id.return_value = session

        with pytest.raises(HTTPException) as exc:
            service.update(
                session.id,
                SessionUpdateRequest(status=SessionStatus.DELETED),
                user,
            )
        assert exc.value.status_code == 400

    def test_delete_sets_status_to_deleted(self, service):
        user = _make_user()
        session = _make_session(user.id)
        service.session_repository.get_by_id.return_value = session
        service.session_repository.update.return_value = session

        service.delete(session.id, user)
        assert session.status == SessionStatus.DELETED
