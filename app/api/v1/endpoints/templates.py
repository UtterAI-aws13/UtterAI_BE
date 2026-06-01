"""Analysis template CRUD and file upload endpoints."""

import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.db import get_db_session
from app.core.enums import TemplateCategory
from app.schemas.auth import UserRead
from app.schemas.template import (
    TemplateCreateRequest,
    TemplateFileUrlResponse,
    TemplateRead,
    TemplateUpdateRequest,
)
from app.services.template import TemplateService

router = APIRouter()


@router.post("", response_model=TemplateRead, status_code=201)
def create_template(
    request: TemplateCreateRequest,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> TemplateRead:
    """Create a new text-content template owned by the current therapist."""

    service = TemplateService(db)
    return service.create(request, current_user)


@router.post("/upload", response_model=TemplateRead, status_code=201)
def upload_template(
    file: UploadFile = File(..., description="PDF, DOCX, or TXT file"),
    name: str | None = Form(default=None),
    category: str = Form(...),
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> TemplateRead:
    """Upload a PDF/DOCX/TXT file as a template. Text is extracted automatically."""

    service = TemplateService(db)
    return service.upload_file(file, name, TemplateCategory(category), current_user)


@router.get("", response_model=list[TemplateRead])
def list_templates(
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> list[TemplateRead]:
    """List templates visible to the authenticated user (own + system templates)."""

    service = TemplateService(db)
    return service.list(current_user)


@router.get("/{template_id}/file", response_model=TemplateFileUrlResponse)
def get_template_file(
    template_id: uuid.UUID,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> TemplateFileUrlResponse:
    """Return a presigned GET URL to download the uploaded template file."""

    service = TemplateService(db)
    return service.get_file_url(template_id, current_user)


@router.get("/{template_id}", response_model=TemplateRead)
def get_template(
    template_id: uuid.UUID,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> TemplateRead:
    """Return one template after access checks."""

    service = TemplateService(db)
    return service.get(template_id, current_user)


@router.patch("/{template_id}", response_model=TemplateRead)
def update_template(
    template_id: uuid.UUID,
    request: TemplateUpdateRequest,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> TemplateRead:
    """Update template name, category, or content (system templates are immutable)."""

    service = TemplateService(db)
    return service.update(template_id, request, current_user)


@router.delete("/{template_id}", response_model=TemplateRead)
def delete_template(
    template_id: uuid.UUID,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> TemplateRead:
    """Soft-delete a template (system templates cannot be deleted)."""

    service = TemplateService(db)
    return service.delete(template_id, current_user)
