"""Authentication endpoints for signup, login, and current-user lookup."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.db import get_db_session
from app.schemas.auth import (
    LoginRequest,
    LogoutResponse,
    PasswordChangeRequest,
    ProfileUpdateRequest,
    RefreshRequest,
    SignupRequest,
    TokenResponse,
    UserRead,
)
from app.services.auth import AuthService

router = APIRouter()


@router.post("/signup", response_model=TokenResponse, status_code=201)
def signup(
    request: SignupRequest,
    db: Session = Depends(get_db_session),
) -> TokenResponse:
    """Create a new account and return the first bearer token.

    The service owns conflict checks and password hashing so the router remains
    responsible only for request parsing and response typing.
    """

    service = AuthService(db)
    return service.signup(request)


@router.post("/login", response_model=TokenResponse)
def login(
    request: LoginRequest,
    db: Session = Depends(get_db_session),
) -> TokenResponse:
    """Authenticate user credentials and return an access token."""

    service = AuthService(db)
    return service.login(request)


@router.get("/me", response_model=UserRead)
def read_me(current_user: UserRead = Depends(get_current_user)) -> UserRead:
    """Return the authenticated user profile derived from the bearer token."""

    return current_user


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(
    request: RefreshRequest,
    db: Session = Depends(get_db_session),
) -> TokenResponse:
    """Rotate a refresh token and return a fresh access/refresh pair."""

    service = AuthService(db)
    return service.refresh(request)


@router.post("/logout", response_model=LogoutResponse)
def logout(
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> LogoutResponse:
    """Revoke active refresh tokens for the authenticated user."""

    service = AuthService(db)
    return service.logout(current_user)


@router.patch("/me", response_model=UserRead)
def update_profile(
    request: ProfileUpdateRequest,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> UserRead:
    """Update the authenticated user's display name."""

    service = AuthService(db)
    return service.update_profile(request, current_user)


@router.patch("/password", response_model=LogoutResponse)
def change_password(
    request: PasswordChangeRequest,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> LogoutResponse:
    """Change the authenticated user's password and revoke all sessions."""

    service = AuthService(db)
    return service.change_password(request, current_user)
