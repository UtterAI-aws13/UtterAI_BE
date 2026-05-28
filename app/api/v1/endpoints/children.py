"""Child-profile CRUD endpoints."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.db import get_db_session
from app.schemas.auth import UserRead
from app.schemas.child import ChildCreateRequest, ChildRead, ChildUpdateRequest
from app.services.child import ChildService

router = APIRouter()


@router.post("", response_model=ChildRead, status_code=201)
def create_child(
    request: ChildCreateRequest,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> ChildRead:
    """Create a child profile owned by the current therapist or chosen admin."""

    service = ChildService(db)
    return service.create(request, current_user)


@router.get("", response_model=list[ChildRead])
def list_children(
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> list[ChildRead]:
    """List child profiles visible to the authenticated user."""

    service = ChildService(db)
    return service.list(current_user)


@router.get("/{child_id}", response_model=ChildRead)
def get_child(
    child_id: uuid.UUID,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> ChildRead:
    """Return one child profile after ownership checks."""

    service = ChildService(db)
    return service.get(child_id, current_user)


@router.patch("/{child_id}", response_model=ChildRead)
def update_child(
    child_id: uuid.UUID,
    request: ChildUpdateRequest,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> ChildRead:
    """Update editable child metadata."""

    service = ChildService(db)
    return service.update(child_id, request, current_user)


@router.delete("/{child_id}", response_model=ChildRead)
def delete_child(
    child_id: uuid.UUID,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> ChildRead:
    """Soft-delete a child profile by changing its lifecycle status."""

    service = ChildService(db)
    return service.delete(child_id, current_user)
