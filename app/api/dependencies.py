"""Reusable API dependencies shared across routers."""

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from opentelemetry import trace
from sqlalchemy.orm import Session

from app.core.db import get_db_session
from app.core.enums import UserStatus
from app.core.config import get_settings
from app.core.logging import set_request_user_email
from app.core.security import decode_access_token
from app.repositories.user import UserRepository
from app.schemas.auth import TokenPayload, UserRead

# The token URL points to our JSON login endpoint so the OpenAPI docs still
# describe where a client obtains bearer tokens.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
settings = get_settings()


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

    resolved = UserRead.model_validate(user)
    span = trace.get_current_span()
    span.set_attribute("user.id", str(resolved.id))
    span.set_attribute("user.email", resolved.email)
    set_request_user_email(resolved.email)
    return resolved


def verify_internal_token(
    x_internal_token: str = Header(alias="X-Internal-Token"),
) -> str:
    """Verify internal callback requests coming from the AI service.

    Internal callback endpoints are not user-authenticated. They rely on a
    shared secret header so external clients cannot mutate job state directly.
    """

    if x_internal_token != settings.internal_callback_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid internal token.",
        )
    return x_internal_token
