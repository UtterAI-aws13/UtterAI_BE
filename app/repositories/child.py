"""Database access helpers for child profiles."""

from __future__ import annotations

import uuid

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.core.enums import ChildStatus
from app.models.entities import Child


class ChildRepository:
    """Encapsulate child-profile queries and persistence rules."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, child: Child) -> Child:
        """Persist a new child profile and return the refreshed ORM object."""

        self.db.add(child)
        self.db.commit()
        self.db.refresh(child)
        return child

    def get_by_id(self, child_id: uuid.UUID) -> Child | None:
        """Return a child regardless of status for service-layer decisions."""

        statement = select(Child).where(Child.id == child_id)
        return self.db.execute(statement).scalar_one_or_none()

    def list_active(self, therapist_id: uuid.UUID | None = None) -> list[Child]:
        """Return active children optionally filtered to one therapist owner."""

        statement: Select[tuple[Child]] = select(Child).where(
            Child.status == ChildStatus.ACTIVE
        )
        if therapist_id is not None:
            statement = statement.where(Child.therapist_id == therapist_id)
        statement = statement.order_by(Child.created_at.desc())
        return list(self.db.execute(statement).scalars().all())

    def update(self, child: Child) -> Child:
        """Commit already-mutated child fields and return the refreshed object."""

        self.db.add(child)
        self.db.commit()
        self.db.refresh(child)
        return child
