"""Session CRUD endpoints."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.db import get_db_session
from app.schemas.auth import UserRead
from app.schemas.report import ReportRead
from app.schemas.session import SessionCreateRequest, SessionRead, SessionUpdateRequest
from app.services.report import ReportService
from app.services.session import SessionService

router = APIRouter()


@router.post("", response_model=SessionRead, status_code=201)
def create_session(
    request: SessionCreateRequest,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> SessionRead:
    """Create a session linked to an accessible child profile."""

    service = SessionService(db)
    return service.create(request, current_user)


@router.get("", response_model=list[SessionRead])
def list_sessions(
    child_id: uuid.UUID | None = Query(default=None),
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> list[SessionRead]:
    """List sessions visible to the authenticated user."""

    service = SessionService(db)
    return service.list(current_user, child_id)


@router.get("/{session_id}", response_model=SessionRead)
def get_session(
    session_id: uuid.UUID,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> SessionRead:
    """Return a single session after ownership checks."""

    service = SessionService(db)
    return service.get(session_id, current_user)


@router.get("/{session_id}/reports", response_model=list[ReportRead])
def list_session_reports(
    session_id: uuid.UUID,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> list[ReportRead]:
    """List reports associated with one accessible session."""

    service = ReportService(db)
    return service.list(current_user, session_id=session_id)


@router.patch("/{session_id}", response_model=SessionRead)
def update_session(
    session_id: uuid.UUID,
    request: SessionUpdateRequest,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> SessionRead:
    """Update editable session fields."""

    service = SessionService(db)
    return service.update(session_id, request, current_user)


@router.delete("/{session_id}", response_model=SessionRead)
def delete_session(
    session_id: uuid.UUID,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> SessionRead:
    """Soft-delete a session by setting its status to `DELETED`."""

    service = SessionService(db)
    return service.delete(session_id, current_user)
