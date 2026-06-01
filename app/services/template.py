"""Service-layer logic for analysis template CRUD and file upload."""

from __future__ import annotations

import io
import uuid

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session as DbSession

from app.core.config import get_settings
from app.core.enums import TemplateCategory, TemplateStatus, UserRole
from app.infrastructure.s3.client import S3Client
from app.models.entities import AnalysisTemplate
from app.repositories.template import TemplateRepository
from app.schemas.auth import UserRead
from app.schemas.template import (
    TemplateCreateRequest,
    TemplateFileUrlResponse,
    TemplateRead,
    TemplateUpdateRequest,
)

settings = get_settings()

_ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
}
_ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}


class TemplateService:
    def __init__(self, db: DbSession) -> None:
        self.repository = TemplateRepository(db)

    # ------------------------------------------------------------------ #
    # Text-content template                                                #
    # ------------------------------------------------------------------ #

    def create(self, request: TemplateCreateRequest, current_user: UserRead) -> TemplateRead:
        template = AnalysisTemplate(
            therapist_id=current_user.id,
            name=request.name,
            category=request.category,
            content=request.content,
        )
        stored = self.repository.create(template)
        return TemplateRead.model_validate(stored)

    # ------------------------------------------------------------------ #
    # File-upload template                                                 #
    # ------------------------------------------------------------------ #

    def upload_file(
        self,
        file: UploadFile,
        name: str | None,
        category: TemplateCategory,
        current_user: UserRead,
    ) -> TemplateRead:
        filename = file.filename or "template"
        ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        content_type = file.content_type or "application/octet-stream"

        if ext not in _ALLOWED_EXTENSIONS and content_type not in _ALLOWED_CONTENT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Only PDF, DOCX, and TXT files are supported.",
            )

        raw_bytes = file.file.read()
        extracted = self._extract_text(raw_bytes, content_type, filename)

        s3_key = f"templates/{current_user.id}/{uuid.uuid4()}/{filename}"
        try:
            S3Client().upload_bytes(settings.template_bucket, s3_key, raw_bytes, content_type)
        except Exception:
            s3_key = None  # S3 unavailable in dev — still save the template with extracted text

        template = AnalysisTemplate(
            therapist_id=current_user.id,
            name=(name or filename).strip() or filename,
            category=category,
            content=extracted or None,
            file_s3_key=s3_key,
            file_original_name=filename,
        )
        stored = self.repository.create(template)
        return TemplateRead.model_validate(stored)

    def get_file_url(self, template_id: uuid.UUID, current_user: UserRead) -> TemplateFileUrlResponse:
        template = self._get_accessible(template_id, current_user)
        if not template.file_s3_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No file is attached to this template.",
            )
        url = S3Client().generate_download_url(settings.template_bucket, template.file_s3_key)
        return TemplateFileUrlResponse(url=url)

    # ------------------------------------------------------------------ #
    # Common CRUD                                                          #
    # ------------------------------------------------------------------ #

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
        if current_user.role != UserRole.ADMIN and template.therapist_id != current_user.id:
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
        if current_user.role != UserRole.ADMIN and template.therapist_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to delete this template.",
            )
        template.status = TemplateStatus.DELETED
        updated = self.repository.update(template)
        return TemplateRead.model_validate(updated)

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _get_accessible(self, template_id: uuid.UUID, current_user: UserRead) -> AnalysisTemplate:
        template = self.repository.get_by_id(template_id)
        if template is None or template.status == TemplateStatus.DELETED:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found.",
            )
        if template.is_system or current_user.role == UserRole.ADMIN:
            return template
        if template.therapist_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this template.",
            )
        return template

    @staticmethod
    def _extract_text(data: bytes, content_type: str, filename: str) -> str:
        lower = filename.lower()
        try:
            if lower.endswith(".pdf") or "pdf" in content_type:
                from pypdf import PdfReader  # type: ignore[import-untyped]
                reader = PdfReader(io.BytesIO(data))
                return "\n".join(page.extract_text() or "" for page in reader.pages)
            if lower.endswith(".docx") or "wordprocessingml" in content_type:
                from docx import Document  # type: ignore[import-untyped]
                doc = Document(io.BytesIO(data))
                return "\n".join(p.text for p in doc.paragraphs)
            return data.decode("utf-8", errors="replace")
        except Exception:
            return ""
