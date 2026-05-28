"""Database access helpers for SOAP note persistence and listing."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import SoapNoteStatus, UserRole
from app.models.entities import Session as SessionEntity, SoapNote
from app.schemas.auth import UserRead


class SoapNoteRepository:
    """Encapsulate SOAP note creation and role-filtered queries."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, note: SoapNote) -> SoapNote:
        """Persist a generated SOAP note and refresh the row."""

        self.db.add(note)
        self.db.commit()
        self.db.refresh(note)
        return note

    def get_by_id(self, note_id: uuid.UUID) -> SoapNote | None:
        """Return one SOAP note by its primary key."""

        statement = select(SoapNote).where(SoapNote.id == note_id)
        return self.db.execute(statement).scalar_one_or_none()

    def list_visible(
        self,
        current_user: UserRead,
        session_id: uuid.UUID | None = None,
        child_id: uuid.UUID | None = None,
    ) -> list[SoapNote]:
        """List notes visible to the current user with optional filters."""

        statement = select(SoapNote).join(
            SessionEntity,
            SoapNote.session_id == SessionEntity.id,
        ).where(SoapNote.status != SoapNoteStatus.DELETED)
        if current_user.role != UserRole.ADMIN:
            statement = statement.where(SessionEntity.therapist_id == current_user.id)
        if session_id is not None:
            statement = statement.where(SoapNote.session_id == session_id)
        if child_id is not None:
            statement = statement.where(SessionEntity.child_id == child_id)
        statement = statement.order_by(SoapNote.created_at.desc())
        return list(self.db.execute(statement).scalars().all())
