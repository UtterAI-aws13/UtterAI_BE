"""Authentication service logic."""

from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.enums import UserStatus
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models.entities import RefreshToken, User
from app.repositories.refresh_token import RefreshTokenRepository
from app.repositories.user import UserRepository
from app.schemas.auth import (
    LoginRequest,
    LogoutResponse,
    RefreshRequest,
    SignupRequest,
    TokenResponse,
    UserRead,
)

settings = get_settings()


class AuthService:
    """Orchestrate signup and login flows using repositories and security utils."""

    def __init__(self, db: Session) -> None:
        self.repository = UserRepository(db)
        self.refresh_token_repository = RefreshTokenRepository(db)

    def signup(self, request: SignupRequest) -> TokenResponse:
        """Create a new user account and immediately issue an access token.

        Issuing the token here removes the extra login round-trip after signup
        while still ensuring the password is hashed before persistence.
        """

        if self.repository.get_by_email(str(request.email)) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists.",
            )

        user = User(
            email=str(request.email),
            password_hash=hash_password(request.password),
            name=request.name,
            role=request.role,
            status=UserStatus.ACTIVE,
        )
        created_user = self.repository.create(user)
        access_token, refresh_token = self._issue_token_pair(created_user)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserRead.model_validate(created_user),
        )

    def login(self, request: LoginRequest) -> TokenResponse:
        """Authenticate a user and return a signed bearer token."""

        user = self.repository.get_by_email(str(request.email))
        if user is None or not verify_password(request.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if user.status != UserStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This account is inactive.",
            )

        access_token, refresh_token = self._issue_token_pair(user)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserRead.model_validate(user),
        )

    def refresh(self, request: RefreshRequest) -> TokenResponse:
        """Rotate a refresh token and return a fresh token pair.

        Rotation means the incoming refresh token is revoked immediately after
        validation, then a brand-new refresh token is issued. This prevents one
        stolen token from being reused indefinitely.
        """

        token_hash = hash_refresh_token(request.refresh_token)
        stored_token = self.refresh_token_repository.get_active_by_hash(token_hash)
        if stored_token is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = self.repository.get_by_id(stored_token.user_id)
        if user is None or user.status != UserStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token owner.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        self.refresh_token_repository.revoke_by_id(stored_token.id)
        access_token, refresh_token = self._issue_token_pair(user)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserRead.model_validate(user),
        )

    def logout(self, current_user: UserRead) -> LogoutResponse:
        """Revoke all active refresh tokens for the authenticated user.

        Access tokens are stateless JWTs, so logout is defined as revoking every
        stored refresh token for the current user. Existing access tokens expire
        naturally, but no new access token can be minted from old sessions.
        """

        revoked_sessions = self.refresh_token_repository.revoke_all_for_user(current_user.id)
        return LogoutResponse(
            revoked_sessions=revoked_sessions,
            message="Refresh tokens revoked successfully.",
        )

    def _issue_token_pair(self, user: User) -> tuple[str, str]:
        """Issue and persist a new access/refresh token pair for one user."""

        access_token = create_access_token(str(user.id))
        raw_refresh_token = generate_refresh_token()
        refresh_token = RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(raw_refresh_token),
            expires_at=datetime.now(UTC)
            + timedelta(days=settings.refresh_token_expire_days),
            created_at=datetime.now(UTC),
        )
        self.refresh_token_repository.create(refresh_token)
        return access_token, raw_refresh_token
