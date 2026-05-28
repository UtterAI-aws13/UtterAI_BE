"""Database access helpers for refresh token persistence."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.entities import RefreshToken


class RefreshTokenRepository:
    """Encapsulate refresh token lookup, creation, and revocation logic."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, refresh_token: RefreshToken) -> RefreshToken:
        """Persist a refresh token row and return the refreshed object."""

        self.db.add(refresh_token)
        self.db.commit()
        self.db.refresh(refresh_token)
        return refresh_token

    def get_active_by_hash(self, token_hash: str) -> RefreshToken | None:
        """Return a non-revoked, non-expired refresh token by its stored hash."""

        now = datetime.now(UTC)
        statement = select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > now,
        )
        return self.db.execute(statement).scalar_one_or_none()

    def revoke_by_id(self, refresh_token_id: uuid.UUID) -> None:
        """Revoke a single refresh token without deleting audit history."""

        statement = (
            update(RefreshToken)
            .where(
                RefreshToken.id == refresh_token_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC))
        )
        self.db.execute(statement)
        self.db.commit()

    def revoke_all_for_user(self, user_id: uuid.UUID) -> int:
        """Revoke all active refresh tokens owned by one user.

        Logout is implemented as revocation of every active refresh token for the
        authenticated user. This keeps the endpoint bodyless while still making
        future session continuation impossible from old refresh tokens.
        """

        statement = (
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=datetime.now(UTC))
        )
        result = self.db.execute(statement)
        self.db.commit()
        return int(result.rowcount or 0)
