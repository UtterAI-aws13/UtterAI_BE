"""Database access helpers for user entities."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import User


class UserRepository:
    """Encapsulate user queries so auth services stay business-focused."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_email(self, email: str) -> User | None:
        """Return a user by email or `None` if the account does not exist."""

        statement = select(User).where(User.email == email)
        return self.db.execute(statement).scalar_one_or_none()

    def get_by_id(self, user_id: uuid.UUID) -> User | None:
        """Return a user by primary key for token-based authentication."""

        statement = select(User).where(User.id == user_id)
        return self.db.execute(statement).scalar_one_or_none()

    def create(self, user: User) -> User:
        """Persist a new user and refresh it so callers receive DB defaults."""

        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
