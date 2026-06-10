"""Database access helpers for therapy sessions."""

from __future__ import annotations

import uuid

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.core.enums import SessionStatus
from app.models.entities import Session as SessionEntity


class SessionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, session: SessionEntity) -> SessionEntity:
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def get_by_id(self, session_id: uuid.UUID) -> SessionEntity | None:
        statement = select(SessionEntity).where(SessionEntity.id == session_id)
        return self.db.execute(statement).scalar_one_or_none()

    def list_active(
        self,
        slp_id: uuid.UUID | None = None,
        patient_ref_id: uuid.UUID | None = None,
    ) -> list[SessionEntity]:
        statement: Select[tuple[SessionEntity]] = select(SessionEntity).where(
            SessionEntity.status != SessionStatus.DELETED
        )
        if slp_id is not None:
            statement = statement.where(SessionEntity.slp_id == slp_id)
        if patient_ref_id is not None:
            statement = statement.where(SessionEntity.patient_ref_id == patient_ref_id)
        statement = statement.order_by(
            SessionEntity.session_date.desc(), SessionEntity.created_at.desc()
        )
        return list(self.db.execute(statement).scalars().all())

    def update(self, session: SessionEntity) -> SessionEntity:
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session
