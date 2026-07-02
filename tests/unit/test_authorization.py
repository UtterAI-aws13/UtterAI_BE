"""Unit tests for shared object-level authorization helpers."""

import uuid
from datetime import datetime
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.core.authorization import (
    ensure_case_index_access,
    ensure_patient_ref_access,
    ensure_report_access,
    ensure_session_access,
)
from app.core.enums import SessionStatus, UserRole, UserStatus
from app.models.entities import PatientRef, Report, Session as SessionEntity, SoapCaseIndex
from app.schemas.auth import UserRead


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
    s.status = SessionStatus.CREATED
    return s


class TestEnsureSessionAccess:
    def test_404_when_session_missing(self):
        db = MagicMock()
        db.get.return_value = None
        with pytest.raises(HTTPException) as exc:
            ensure_session_access(db, uuid.uuid4(), _make_user())
        assert exc.value.status_code == 404

    def test_403_when_other_slp_owns_session(self):
        db = MagicMock()
        session = _make_session(uuid.uuid4())
        db.get.return_value = session
        with pytest.raises(HTTPException) as exc:
            ensure_session_access(db, session.id, _make_user())
        assert exc.value.status_code == 403

    def test_admin_bypasses_ownership_check(self):
        db = MagicMock()
        session = _make_session(uuid.uuid4())
        db.get.return_value = session
        result = ensure_session_access(db, session.id, _make_user(UserRole.ADMIN))
        assert result is session

    def test_owner_slp_is_allowed(self):
        db = MagicMock()
        user = _make_user()
        session = _make_session(user.id)
        db.get.return_value = session
        result = ensure_session_access(db, session.id, user)
        assert result is session


class TestEnsureReportAccess:
    def test_404_when_report_missing(self):
        db = MagicMock()
        db.get.return_value = None
        with pytest.raises(HTTPException) as exc:
            ensure_report_access(db, uuid.uuid4(), _make_user())
        assert exc.value.status_code == 404

    def test_403_when_session_not_owned(self):
        db = MagicMock()
        user = _make_user()
        session = _make_session(uuid.uuid4())
        report = MagicMock(spec=Report)
        report.session_id = session.id
        db.get.side_effect = lambda model, _id: report if model is Report else session
        with pytest.raises(HTTPException) as exc:
            ensure_report_access(db, uuid.uuid4(), user)
        assert exc.value.status_code == 403


class TestEnsurePatientRefAccess:
    def test_404_when_patient_ref_missing(self):
        db = MagicMock()
        db.get.return_value = None
        with pytest.raises(HTTPException) as exc:
            ensure_patient_ref_access(db, uuid.uuid4(), _make_user())
        assert exc.value.status_code == 404

    def test_403_when_not_current_slp(self):
        db = MagicMock()
        ref = MagicMock(spec=PatientRef)
        ref.current_slp_id = uuid.uuid4()
        db.get.return_value = ref
        with pytest.raises(HTTPException) as exc:
            ensure_patient_ref_access(db, uuid.uuid4(), _make_user())
        assert exc.value.status_code == 403

    def test_current_slp_is_allowed(self):
        db = MagicMock()
        user = _make_user()
        ref = MagicMock(spec=PatientRef)
        ref.current_slp_id = user.id
        db.get.return_value = ref
        result = ensure_patient_ref_access(db, uuid.uuid4(), user)
        assert result is ref


class TestEnsureCaseIndexAccess:
    def test_404_when_case_index_missing(self):
        db = MagicMock()
        db.get.return_value = None
        with pytest.raises(HTTPException) as exc:
            ensure_case_index_access(db, uuid.uuid4(), _make_user())
        assert exc.value.status_code == 404

    def test_403_when_different_therapist(self):
        db = MagicMock()
        case_index = MagicMock(spec=SoapCaseIndex)
        case_index.therapist_id = uuid.uuid4()
        db.get.return_value = case_index
        with pytest.raises(HTTPException) as exc:
            ensure_case_index_access(db, uuid.uuid4(), _make_user())
        assert exc.value.status_code == 403

    def test_owning_therapist_is_allowed(self):
        db = MagicMock()
        user = _make_user()
        case_index = MagicMock(spec=SoapCaseIndex)
        case_index.therapist_id = user.id
        db.get.return_value = case_index
        result = ensure_case_index_access(db, uuid.uuid4(), user)
        assert result is case_index
