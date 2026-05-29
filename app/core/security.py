"""Password hashing, JWT helpers, and refresh token utilities."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from jose import jwt

from app.core.config import get_settings

settings = get_settings()


def hash_password(password: str) -> str:
    """Hash a plain-text password before it ever reaches persistent storage."""

    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Compare a login password to the stored hash safely."""

    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    """Build a signed JWT access token for the authenticated user.

    The token only stores the minimal subject and expiration claims required for
    user resolution. Additional claims can be added later if authorization needs
    become more granular.
    """

    expire_at = datetime.now(UTC) + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.access_token_expire_minutes)
    )

    to_encode = {
        "sub": subject,
        "exp": expire_at,
    }
    return jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode a bearer token and return its claims payload."""

    return jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )


def generate_refresh_token() -> str:
    """Generate a high-entropy opaque refresh token for long-lived sessions.

    Refresh tokens are intentionally opaque instead of JWTs so the server keeps
    revocation control in the database and does not rely on client-held claims.
    """

    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    """Hash a refresh token before storing it in the database.

    Storing a hash instead of the raw token limits damage if the refresh token
    table is ever exposed, while still allowing exact-match lookup on refresh.
    """

    return hashlib.sha256(token.encode("utf-8")).hexdigest()
