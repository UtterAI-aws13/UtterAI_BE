"""Service-layer logic for session CRUD."""

import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session as DbSession

from app.core.enums import ChildStatus, SessionStatus, UserRole
from app.models.entities import Session
from app.repositories.child import ChildRepository
from app.repositories.session import SessionRepository
from app.schemas.auth import UserRead
from app.schemas.session import SessionCreateRequest, SessionRead, SessionUpdateRequest


class SessionService:
    """Apply ownership and lifecycle rules around session operations."""

    def __init__(self, db: DbSession) -> None:
        self.child_repository = ChildRepository(db)
        self.session_repository = SessionRepository(db)

    def create(self, request: SessionCreateRequest, current_user: UserRead) -> SessionRead:
        """Create a session bound to an accessible child profile.

        The session inherits its therapist owner from the child profile so the
        parent-child ownership graph stays consistent across the domain.
        """

        child = self._get_accessible_child(request.child_id, current_user)

        session = Session(
            child_id=child.id,
            therapist_id=child.therapist_id,
            session_date=request.session_date,
            session_type=request.session_type,
            memo=request.memo,
            status=SessionStatus.CREATED,
        )
        return SessionRead.model_validate(self.session_repository.create(session))

    def list(
        self,
        current_user: UserRead,
        child_id: uuid.UUID | None = None,
    ) -> list[SessionRead]:
        """List sessions visible to the current user, optionally by child."""

        if child_id is not None:
            self._get_accessible_child(child_id, current_user)

        if current_user.role == UserRole.ADMIN:
            sessions = self.session_repository.list_active(child_id=child_id)
        elif current_user.role == UserRole.THERAPIST:
            sessions = self.session_repository.list_active(
                therapist_id=current_user.id,
                child_id=child_id,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only therapists or admins can view sessions.",
            )
        return [SessionRead.model_validate(session) for session in sessions]

    def get(self, session_id: uuid.UUID, current_user: UserRead) -> SessionRead:
        """Return a single accessible session."""

        session = self._get_accessible_session(session_id, current_user)
        return SessionRead.model_validate(session)

    def update(
        self,
        session_id: uuid.UUID,
        request: SessionUpdateRequest,
        current_user: UserRead,
    ) -> SessionRead:
        """Update editable session fields with guarded status changes."""

        session = self._get_accessible_session(session_id, current_user)
        update_data = request.model_dump(exclude_unset=True)

        if "status" in update_data and update_data["status"] == SessionStatus.DELETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Use the delete endpoint to remove a session.",
            )

        for field_name, value in update_data.items():
            setattr(session, field_name, value)

        return SessionRead.model_validate(self.session_repository.update(session))

    def delete(self, session_id: uuid.UUID, current_user: UserRead) -> SessionRead:
        """Soft-delete a session by setting its status to `DELETED`."""

        session = self._get_accessible_session(session_id, current_user)
        session.status = SessionStatus.DELETED
        return SessionRead.model_validate(self.session_repository.update(session))

    def _get_accessible_child(self, child_id: uuid.UUID, current_user: UserRead):
        """Load a child and verify that the current user can create sessions on it."""

        child = self.child_repository.get_by_id(child_id)
        if child is None or child.status == ChildStatus.DELETED:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Child profile not found.",
            )

        if current_user.role == UserRole.ADMIN:
            return child

        if current_user.role == UserRole.THERAPIST and child.therapist_id == current_user.id:
            return child

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this child profile.",
        )

    def _get_accessible_session(
        self,
        session_id: uuid.UUID,
        current_user: UserRead,
    ) -> Session:
        """Load a session and enforce therapist ownership or admin override."""

        session = self.session_repository.get_by_id(session_id)
        if session is None or session.status == SessionStatus.DELETED:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found.",
            )

        if current_user.role == UserRole.ADMIN:
            return session

        if current_user.role == UserRole.THERAPIST and session.therapist_id == current_user.id:
            return session

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this session.",
        )
