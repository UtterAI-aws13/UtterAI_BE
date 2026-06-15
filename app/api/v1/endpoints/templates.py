"""Template CRUD and file upload endpoints."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.db import get_db_session
from app.schemas.auth import UserRead
from app.schemas.template import (
    TemplateConfirmUploadRequest,
    TemplateCreateRequest,
    TemplateFileUrlResponse,
    TemplatePresignedUploadRequest,
    TemplatePresignedUploadResponse,
    TemplateRead,
    TemplateUpdateRequest,
)
from app.services.template import TemplateService

router = APIRouter()


@router.post("/", response_model=TemplateRead, status_code=201)
def create_template(
    request: TemplateCreateRequest,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> TemplateRead:
    return TemplateService(db).create(request, current_user)


@router.post("/presigned-url", response_model=TemplatePresignedUploadResponse, status_code=201)
def create_presigned_upload(
    request: TemplatePresignedUploadRequest,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> TemplatePresignedUploadResponse:
    """Create a PENDING_UPLOAD template row and return a presigned S3 PUT URL."""
    return TemplateService(db).create_presigned_upload(request, current_user)


@router.get("/", response_model=list[TemplateRead])
def list_templates(
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> list[TemplateRead]:
    return TemplateService(db).list(current_user)


@router.get("/{template_id}/file", response_model=TemplateFileUrlResponse)
def get_template_file(
    template_id: uuid.UUID,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> TemplateFileUrlResponse:
    return TemplateService(db).get_file_url(template_id, current_user)


@router.post("/{template_id}/confirm", response_model=TemplateRead)
def confirm_upload(
    template_id: uuid.UUID,
    request: TemplateConfirmUploadRequest,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> TemplateRead:
    """Verify the file was uploaded to S3 and activate the template."""
    return TemplateService(db).confirm_upload(template_id, request, current_user)


@router.get("/{template_id}", response_model=TemplateRead)
def get_template(
    template_id: uuid.UUID,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> TemplateRead:
    return TemplateService(db).get(template_id, current_user)


@router.patch("/{template_id}", response_model=TemplateRead)
def update_template(
    template_id: uuid.UUID,
    request: TemplateUpdateRequest,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> TemplateRead:
    return TemplateService(db).update(template_id, request, current_user)


@router.delete("/{template_id}", response_model=TemplateRead)
def delete_template(
    template_id: uuid.UUID,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> TemplateRead:
    return TemplateService(db).delete(template_id, current_user)
