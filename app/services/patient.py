"""Service-layer logic for patient CRUD."""

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session as DbSession

from app.core.enums import PatientStatus, UserRole
from app.models.entities import PatientRef
from app.repositories.patient_ref import PatientRefRepository
from app.schemas.auth import UserRead
from app.schemas.patient import PatientCreateRequest, PatientRead, PatientUpdateRequest


class PatientService:
    def __init__(self, db: DbSession) -> None:
        self.repo = PatientRefRepository(db)

    def create(self, request: PatientCreateRequest, current_user: UserRead) -> PatientRead:
        slp_id = request.slp_id if (current_user.role == UserRole.ADMIN and request.slp_id) else current_user.id
        patient = PatientRef(
            created_by_slp_id=current_user.id,
            current_slp_id=slp_id,
            name=request.name,
            birth_date=request.birth_date,
            gender=request.gender,
            memo=request.memo,
            status=PatientStatus.ACTIVE,
            created_at=datetime.now(timezone.utc),
        )
        return PatientRead.model_validate(self.repo.create(patient))

    def list(self, current_user: UserRead) -> list[PatientRead]:
        if current_user.role == UserRole.ADMIN:
            patients = self.repo.list_all_active()
        else:
            patients = self.repo.list_by_slp(current_user.id)
        return [PatientRead.model_validate(p) for p in patients]

    def get(self, patient_id: uuid.UUID, current_user: UserRead) -> PatientRead:
        patient = self._get_accessible(patient_id, current_user)
        return PatientRead.model_validate(patient)

    def update(
        self,
        patient_id: uuid.UUID,
        request: PatientUpdateRequest,
        current_user: UserRead,
    ) -> PatientRead:
        patient = self._get_accessible(patient_id, current_user)
        for field, value in request.model_dump(exclude_unset=True).items():
            setattr(patient, field, value)
        return PatientRead.model_validate(self.repo.update(patient))

    def delete(self, patient_id: uuid.UUID, current_user: UserRead) -> PatientRead:
        patient = self._get_accessible(patient_id, current_user)
        patient.status = PatientStatus.DELETED
        return PatientRead.model_validate(self.repo.update(patient))

    def _get_accessible(self, patient_id: uuid.UUID, current_user: UserRead) -> PatientRef:
        patient = self.repo.get_by_id(patient_id)
        if patient is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found.")
        if current_user.role == UserRole.ADMIN:
            return patient
        if patient.current_slp_id == current_user.id:
            return patient
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")