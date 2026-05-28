"""Authentication service logic."""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.enums import UserStatus
from app.core.security import create_access_token, hash_password, verify_password
from app.models.entities import User
from app.repositories.user import UserRepository
from app.schemas.auth import LoginRequest, SignupRequest, TokenResponse, UserRead


class AuthService:
    """Orchestrate signup and login flows using repositories and security utils."""

    def __init__(self, db: Session) -> None:
        self.repository = UserRepository(db)

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
        access_token = create_access_token(str(created_user.id))

        return TokenResponse(
            access_token=access_token,
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

        access_token = create_access_token(str(user.id))

        return TokenResponse(
            access_token=access_token,
            user=UserRead.model_validate(user),
        )
