"""Reusable API dependencies shared across routers."""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.db import get_db_session
from app.core.enums import UserStatus
from app.core.security import decode_access_token
from app.repositories.user import UserRepository
from app.schemas.auth import TokenPayload, UserRead

# The token URL points to our JSON login endpoint so the OpenAPI docs still
# describe where a client obtains bearer tokens.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db_session),
) -> UserRead:
    """Resolve the authenticated user from the bearer token.

    Authentication rules are centralized here so every protected endpoint can
    reuse the same token decoding, user loading, and inactive-account checks.
    """

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload_dict = decode_access_token(token)
        token_payload = TokenPayload.model_validate(payload_dict)
    except (JWTError, ValueError):
        raise credentials_exception

    repository = UserRepository(db)
    user = repository.get_by_id(token_payload.sub)

    if user is None or user.status != UserStatus.ACTIVE:
        raise credentials_exception

    return UserRead.model_validate(user)
