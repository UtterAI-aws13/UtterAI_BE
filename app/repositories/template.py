"""Repository for template persistence."""

import uuid

from sqlalchemy import or_, select
from sqlalchemy.orm import Session as DbSession

from app.core.enums import TemplateStatus, UserRole
from app.models.entities import Template
from app.schemas.auth import UserRead


class TemplateRepository:
    def __init__(self, db: DbSession) -> None:
        self.db = db

    def create(self, template: Template) -> Template:
        self.db.add(template)
        self.db.commit()
        self.db.refresh(template)
        return template

    def get_by_id(self, template_id: uuid.UUID) -> Template | None:
        statement = select(Template).where(Template.id == template_id)
        return self.db.execute(statement).scalar_one_or_none()

    def list_visible(self, current_user: UserRead) -> list[Template]:
        statement = select(Template).where(Template.status == TemplateStatus.ACTIVE)
        if current_user.role != UserRole.ADMIN:
            statement = statement.where(
                or_(
                    Template.is_system.is_(True),
                    Template.owner_id == current_user.id,
                )
            )
        statement = statement.order_by(Template.is_system.desc(), Template.created_at.desc())
        return list(self.db.execute(statement).scalars().all())

    def update(self, template: Template) -> Template:
        self.db.add(template)
        self.db.commit()
        self.db.refresh(template)
        return template

    def increment_use_count(self, template: Template) -> None:
        template.use_count += 1
        self.db.add(template)
        self.db.commit()
