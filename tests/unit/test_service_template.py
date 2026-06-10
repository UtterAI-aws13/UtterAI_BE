"""Unit tests for TemplateService business logic."""

import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.core.enums import TemplateStatus, TemplateType, UserRole, UserStatus
from app.models.entities import Template
from app.schemas.auth import UserRead
from app.schemas.template import TemplateCreateRequest, TemplateUpdateRequest
from app.services.template import TemplateService


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


def _make_template(
    owner_id: uuid.UUID | None = None,
    is_system: bool = False,
    status: TemplateStatus = TemplateStatus.ACTIVE,
) -> MagicMock:
    t = MagicMock(spec=Template)
    t.id = uuid.uuid4()
    t.owner_id = owner_id
    t.is_system = is_system
    t.status = status
    t.name = "테스트 템플릿"
    t.description = None
    t.template_type = TemplateType.SOAP_NOTE
    t.sections_json = None
    t.file_s3_key = None
    t.file_original_name = None
    t.use_count = 0
    return t


@pytest.fixture
def db():
    return MagicMock()


@pytest.fixture
def service(db):
    with patch("app.services.template.TemplateRepository") as MockRepo:
        svc = TemplateService(db)
        svc.repository = MockRepo.return_value
        yield svc


class TestTemplateServiceCreate:
    def test_creates_with_owner_id_from_current_user(self, service):
        user = _make_user()
        template = _make_template(owner_id=user.id)
        service.repository.create.return_value = template

        service.create(TemplateCreateRequest(name="SOAP 기본"), user)

        created = service.repository.create.call_args[0][0]
        assert created.owner_id == user.id
        assert created.template_type == TemplateType.SOAP_NOTE


class TestTemplateServiceGet:
    def test_raises_404_when_not_found(self, service):
        service.repository.get_by_id.return_value = None
        with pytest.raises(HTTPException) as exc:
            service.get(uuid.uuid4(), _make_user())
        assert exc.value.status_code == 404

    def test_raises_404_for_deleted_template(self, service):
        template = _make_template(status=TemplateStatus.DELETED)
        service.repository.get_by_id.return_value = template
        with pytest.raises(HTTPException) as exc:
            service.get(template.id, _make_user())
        assert exc.value.status_code == 404

    def test_slp_can_access_own_template(self, service):
        user = _make_user()
        template = _make_template(owner_id=user.id)
        service.repository.get_by_id.return_value = template
        result = service._get_accessible(template.id, user)
        assert result is template

    def test_slp_can_access_system_template(self, service):
        user = _make_user()
        template = _make_template(is_system=True)
        service.repository.get_by_id.return_value = template
        result = service._get_accessible(template.id, user)
        assert result is template

    def test_slp_cannot_access_other_slp_template(self, service):
        user = _make_user()
        template = _make_template(owner_id=uuid.uuid4(), is_system=False)
        service.repository.get_by_id.return_value = template
        with pytest.raises(HTTPException) as exc:
            service._get_accessible(template.id, user)
        assert exc.value.status_code == 403

    def test_admin_can_access_any_template(self, service):
        admin = _make_user(UserRole.ADMIN)
        template = _make_template(owner_id=uuid.uuid4())
        service.repository.get_by_id.return_value = template
        result = service._get_accessible(template.id, admin)
        assert result is template


class TestTemplateServiceUpdate:
    def test_cannot_modify_system_template(self, service):
        user = _make_user()
        template = _make_template(is_system=True)
        service.repository.get_by_id.return_value = template

        with pytest.raises(HTTPException) as exc:
            service.update(template.id, TemplateUpdateRequest(name="수정"), user)
        assert exc.value.status_code == 403

    def test_cannot_modify_other_slp_template(self, service):
        user = _make_user()
        template = _make_template(owner_id=uuid.uuid4(), is_system=False)
        service.repository.get_by_id.return_value = template

        with pytest.raises(HTTPException) as exc:
            service.update(template.id, TemplateUpdateRequest(name="수정"), user)
        assert exc.value.status_code == 403

    def test_owner_can_update_own_template(self, service):
        user = _make_user()
        template = _make_template(owner_id=user.id)
        service.repository.get_by_id.return_value = template
        service.repository.update.return_value = template

        service.update(template.id, TemplateUpdateRequest(name="새 이름"), user)

        assert template.name == "새 이름"


class TestTemplateServiceDelete:
    def test_cannot_delete_system_template(self, service):
        user = _make_user()
        template = _make_template(is_system=True)
        service.repository.get_by_id.return_value = template

        with pytest.raises(HTTPException) as exc:
            service.delete(template.id, user)
        assert exc.value.status_code == 403

    def test_sets_status_to_deleted(self, service):
        user = _make_user()
        template = _make_template(owner_id=user.id, is_system=False)
        service.repository.get_by_id.return_value = template
        service.repository.update.return_value = template

        service.delete(template.id, user)

        assert template.status == TemplateStatus.DELETED

    def test_admin_can_delete_any_template(self, service):
        admin = _make_user(UserRole.ADMIN)
        template = _make_template(owner_id=uuid.uuid4(), is_system=False)
        service.repository.get_by_id.return_value = template
        service.repository.update.return_value = template

        service.delete(template.id, admin)

        assert template.status == TemplateStatus.DELETED
