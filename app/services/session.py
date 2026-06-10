"""Service-layer logic for session CRUD."""

import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session as DbSession

from app.core.enums import SessionStatus, UserRole
from app.models.entities import Session as SessionEntity
from app.repositories.patient_ref import PatientRefRepository
from app.repositories.session import SessionRepository
from app.schemas.auth import UserRead
from app.schemas.session import SessionCreateRequest, SessionRead, SessionUpdateRequest


class SessionService:
    def __init__(self, db: DbSession) -> None:
        self.patient_ref_repository = PatientRefRepository(db)
        self.session_repository = SessionRepository(db)

    def create(self, request: SessionCreateRequest, current_user: UserRead) -> SessionRead:
        patient_ref = self.patient_ref_repository.get_by_id(request.patient_ref_id)
        if patient_ref is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient reference not found.",
            )

        session = SessionEntity(
            patient_ref_id=request.patient_ref_id,
            slp_id=current_user.id,
            session_date=request.session_date,
            session_type=request.session_type,
            session_goal=request.session_goal,
            memo=request.memo,
            status=SessionStatus.CREATED,
        )
        return SessionRead.model_validate(self.session_repository.create(session))

    def list(
        self,
        current_user: UserRead,
        patient_ref_id: uuid.UUID | None = None,
    ) -> list[SessionRead]:
        if current_user.role == UserRole.ADMIN:
            sessions = self.session_repository.list_active(patient_ref_id=patient_ref_id)
        elif current_user.role == UserRole.THERAPIST:
            sessions = self.session_repository.list_active(
                slp_id=current_user.id,
                patient_ref_id=patient_ref_id,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only therapists or admins can view sessions.",
            )
        return [SessionRead.model_validate(s) for s in sessions]

    def get(self, session_id: uuid.UUID, current_user: UserRead) -> SessionRead:
        session = self._get_accessible_session(session_id, current_user)
        return SessionRead.model_validate(session)

    def update(
        self,
        session_id: uuid.UUID,
        request: SessionUpdateRequest,
        current_user: UserRead,
    ) -> SessionRead:
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
        session = self._get_accessible_session(session_id, current_user)
        session.status = SessionStatus.DELETED
        return SessionRead.model_validate(self.session_repository.update(session))

    def _get_accessible_session(self, session_id: uuid.UUID, current_user: UserRead) -> SessionEntity:
        session = self.session_repository.get_by_id(session_id)
        if session is None or session.status == SessionStatus.DELETED:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found.",
            )
        if current_user.role == UserRole.ADMIN:
            return session
        if current_user.role == UserRole.THERAPIST and session.slp_id == current_user.id:
            return session
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this session.",
        )
