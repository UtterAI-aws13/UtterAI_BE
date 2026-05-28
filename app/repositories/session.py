"""Database access helpers for therapy sessions."""

from __future__ import annotations

import uuid

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.core.enums import SessionStatus
from app.models.entities import Session


class SessionRepository:
    """Encapsulate session queries and persistence operations."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, session: Session) -> Session:
        """Persist a new session and return the refreshed ORM object."""

        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def get_by_id(self, session_id: uuid.UUID) -> Session | None:
        """Return a session regardless of status for authorization checks."""

        statement = select(Session).where(Session.id == session_id)
        return self.db.execute(statement).scalar_one_or_none()

    def list_active(
        self,
        therapist_id: uuid.UUID | None = None,
        child_id: uuid.UUID | None = None,
    ) -> list[Session]:
        """Return non-deleted sessions filtered by owner and/or child."""

        statement: Select[tuple[Session]] = select(Session).where(
            Session.status != SessionStatus.DELETED
        )
        if therapist_id is not None:
            statement = statement.where(Session.therapist_id == therapist_id)
        if child_id is not None:
            statement = statement.where(Session.child_id == child_id)
        statement = statement.order_by(Session.session_date.desc(), Session.created_at.desc())
        return list(self.db.execute(statement).scalars().all())

    def update(self, session: Session) -> Session:
        """Commit already-mutated session fields and return the refreshed row."""

        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session
