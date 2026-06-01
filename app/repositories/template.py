"""Repository for analysis template persistence."""

import uuid

from sqlalchemy import or_
from sqlalchemy.orm import Session as DbSession

from app.core.enums import TemplateStatus, UserRole
from app.models.entities import AnalysisTemplate
from app.schemas.auth import UserRead


class TemplateRepository:
    def __init__(self, db: DbSession) -> None:
        self.db = db

    def create(self, template: AnalysisTemplate) -> AnalysisTemplate:
        self.db.add(template)
        self.db.commit()
        self.db.refresh(template)
        return template

    def get_by_id(self, template_id: uuid.UUID) -> AnalysisTemplate | None:
        return self.db.get(AnalysisTemplate, template_id)

    def list_visible(self, current_user: UserRead) -> list[AnalysisTemplate]:
        query = self.db.query(AnalysisTemplate).filter(
            AnalysisTemplate.status == TemplateStatus.ACTIVE,
        )
        if current_user.role != UserRole.ADMIN:
            query = query.filter(
                or_(
                    AnalysisTemplate.is_system == True,  # noqa: E712
                    AnalysisTemplate.therapist_id == current_user.id,
                )
            )
        return (
            query
            .order_by(AnalysisTemplate.is_system.desc(), AnalysisTemplate.created_at.desc())
            .all()
        )

    def update(self, template: AnalysisTemplate) -> AnalysisTemplate:
        self.db.add(template)
        self.db.commit()
        self.db.refresh(template)
        return template

    def increment_use_count(self, template: AnalysisTemplate) -> None:
        template.use_count += 1
        self.db.add(template)
        self.db.commit()
