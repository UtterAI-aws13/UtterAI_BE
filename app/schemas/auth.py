"""Request and response schemas for authentication endpoints."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.core.enums import UserRole, UserStatus


class SignupRequest(BaseModel):
    """Payload for self-service account creation."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=100)
    role: UserRole = UserRole.THERAPIST


class LoginRequest(BaseModel):
    """Payload for password-based login."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserRead(BaseModel):
    """Public user shape returned to authenticated clients."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    name: str
    role: UserRole
    status: UserStatus
    created_at: datetime
    updated_at: datetime


class TokenResponse(BaseModel):
    """Access and refresh token response shape used after auth operations."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserRead


class RefreshRequest(BaseModel):
    """Payload for exchanging a refresh token for a new token pair."""

    refresh_token: str = Field(min_length=32, max_length=512)


class LogoutResponse(BaseModel):
    """Simple logout response acknowledging refresh token revocation."""

    revoked_sessions: int
    message: str


class TokenPayload(BaseModel):
    """JWT claims required to resolve the current user."""

    sub: uuid.UUID
