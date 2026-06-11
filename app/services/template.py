"""Service-layer logic for template CRUD and file upload."""

from __future__ import annotations

import os
import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session as DbSession

from app.core.config import get_settings
from app.core.enums import TemplateStatus, TemplateType, UserRole
from app.infrastructure.s3.client import S3Client
from app.models.entities import Template
from app.repositories.template import TemplateRepository
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

settings = get_settings()

_ALLOWED_EXTENSIONS = {
    ".pdf",
    ".doc", ".docx",
    ".xls", ".xlsx",
    ".ppt", ".pptx",
    ".hwp", ".hwpx",
    ".txt", ".rtf", ".csv",
    ".odt", ".ods", ".odp",
}


class TemplateService:
    def __init__(self, db: DbSession) -> None:
        self.repository = TemplateRepository(db)
        self.s3_client = S3Client()

    def create(self, request: TemplateCreateRequest, current_user: UserRead) -> TemplateRead:
        template = Template(
            owner_id=current_user.id,
            name=request.name,
            template_type=request.template_type,
            description=request.description,
            sections_json=request.sections_json,
        )
        stored = self.repository.create(template)
        return TemplateRead.model_validate(stored)

    def create_presigned_upload(
        self,
        request: TemplatePresignedUploadRequest,
        current_user: UserRead,
    ) -> TemplatePresignedUploadResponse:
        ext = os.path.splitext(request.file_name)[1].lower()
        if ext not in _ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Unsupported file type. Only document files are allowed (pdf, docx, xlsx, hwp, hwpx, etc.)",
            )

        object_key = self._build_object_key(current_user.id, request.file_name)
        display_name = (request.name or os.path.splitext(request.file_name)[0]).strip() or request.file_name

        template = Template(
            owner_id=current_user.id,
            name=display_name,
            template_type=request.template_type,
            file_s3_key=object_key,
            file_original_name=request.file_name,
            status=TemplateStatus.PENDING_UPLOAD,
        )
        created = self.repository.create(template)

        upload_url = self.s3_client.generate_upload_url(
            bucket=settings.template_bucket,
            key=object_key,
            content_type=request.content_type,
        )
        return TemplatePresignedUploadResponse(
            template_id=created.id,
            upload_url=upload_url,
            object_key=object_key,
            expires_in=settings.presigned_url_expire_seconds,
        )

    def confirm_upload(
        self,
        template_id: uuid.UUID,
        request: TemplateConfirmUploadRequest,
        current_user: UserRead,
    ) -> TemplateRead:
        template = self.repository.get_by_id(template_id)
        if template is None or template.status == TemplateStatus.DELETED:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found.")
        if template.status != TemplateStatus.PENDING_UPLOAD:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Template is not in PENDING_UPLOAD state.",
            )
        if current_user.role != UserRole.ADMIN and template.owner_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this template.")

        if not template.file_s3_key or not self.s3_client.object_exists(settings.template_bucket, template.file_s3_key):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded object not found in S3. Upload the file before confirming.",
            )

        template.status = TemplateStatus.ACTIVE
        updated = self.repository.update(template)
        return TemplateRead.model_validate(updated)

    def get_file_url(self, template_id: uuid.UUID, current_user: UserRead) -> TemplateFileUrlResponse:
        template = self._get_accessible(template_id, current_user)
        if not template.file_s3_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No file is attached to this template.",
            )
        url = self.s3_client.generate_download_url(settings.template_bucket, template.file_s3_key)
        return TemplateFileUrlResponse(url=url)

    def list(self, current_user: UserRead) -> list[TemplateRead]:
        templates = self.repository.list_visible(current_user)
        return [TemplateRead.model_validate(t) for t in templates]

    def get(self, template_id: uuid.UUID, current_user: UserRead) -> TemplateRead:
        template = self._get_accessible(template_id, current_user)
        return TemplateRead.model_validate(template)

    def update(
        self,
        template_id: uuid.UUID,
        request: TemplateUpdateRequest,
        current_user: UserRead,
    ) -> TemplateRead:
        template = self._get_accessible(template_id, current_user)
        if template.is_system:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="System templates cannot be modified.",
            )
        if current_user.role != UserRole.ADMIN and template.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to edit this template.",
            )
        for field, value in request.model_dump(exclude_unset=True).items():
            setattr(template, field, value)
        updated = self.repository.update(template)
        return TemplateRead.model_validate(updated)

    def delete(self, template_id: uuid.UUID, current_user: UserRead) -> TemplateRead:
        template = self._get_accessible(template_id, current_user)
        if template.is_system:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="System templates cannot be deleted.",
            )
        if current_user.role != UserRole.ADMIN and template.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to delete this template.",
            )
        template.status = TemplateStatus.DELETED
        updated = self.repository.update(template)
        return TemplateRead.model_validate(updated)

    def _get_accessible(self, template_id: uuid.UUID, current_user: UserRead) -> Template:
        template = self.repository.get_by_id(template_id)
        if template is None or template.status in {TemplateStatus.DELETED, TemplateStatus.PENDING_UPLOAD}:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found.",
            )
        if template.is_system or current_user.role == UserRole.ADMIN:
            return template
        if template.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this template.",
            )
        return template

    @staticmethod
    def _build_object_key(owner_id: uuid.UUID, file_name: str) -> str:
        safe_name = os.path.basename(file_name).replace(" ", "_")
        return f"templates/{owner_id}/{uuid.uuid4().hex}/{safe_name}"
