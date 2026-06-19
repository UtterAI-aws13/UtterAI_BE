"""Service-layer logic for patient CRUD."""

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session as DbSession

from app.core.enums import PatientStatus, UserRole
from app.models.entities import Patient, PatientRef
from app.repositories.patient import PatientRepository
from app.repositories.patient_ref import PatientRefRepository
from app.schemas.auth import UserRead
from app.schemas.patient import PatientCreateRequest, PatientRead, PatientUpdateRequest


class PatientService:
    def __init__(self, db: DbSession) -> None:
        self.patient_repo = PatientRepository(db)
        self.ref_repo = PatientRefRepository(db)

    def create(self, request: PatientCreateRequest, current_user: UserRead) -> PatientRead:
        slp_id = request.slp_id if (current_user.role == UserRole.ADMIN and request.slp_id) else current_user.id
        ref = self.ref_repo.create(created_by_slp_id=current_user.id, current_slp_id=slp_id)
        patient = Patient(
            patient_ref_id=ref.id,
            name=request.name,
            birth_date=request.birth_date,
            gender=request.gender,
            memo=request.memo,
            status=PatientStatus.ACTIVE,
            created_at=datetime.now(timezone.utc),
        )
        patient = self.patient_repo.create(patient)
        return self._to_read(patient, ref)

    def list(self, current_user: UserRead) -> list[PatientRead]:
        if current_user.role == UserRole.ADMIN:
            patients = self.patient_repo.list_all_active()
        else:
            patients = self.patient_repo.list_by_slp(current_user.id)
        return [self._to_read(p, self.ref_repo.get_by_id(p.patient_ref_id)) for p in patients]  # type: ignore[arg-type]

    def get(self, patient_id: uuid.UUID, current_user: UserRead) -> PatientRead:
        patient, ref = self._get_accessible(patient_id, current_user)
        return self._to_read(patient, ref)

    def get_by_ref_id(self, patient_ref_id: uuid.UUID, current_user: UserRead) -> PatientRead:
        patient = self.patient_repo.get_by_ref_id(patient_ref_id)
        if patient is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found.")
        ref = self.ref_repo.get_by_id(patient.patient_ref_id)
        if ref is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient ref not found.")
        if current_user.role != UserRole.ADMIN and ref.current_slp_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
        return self._to_read(patient, ref)

    def update(self, patient_id: uuid.UUID, request: PatientUpdateRequest, current_user: UserRead) -> PatientRead:
        patient, ref = self._get_accessible(patient_id, current_user)
        for field, value in request.model_dump(exclude_unset=True).items():
            setattr(patient, field, value)
        patient = self.patient_repo.update(patient)
        return self._to_read(patient, ref)

    def delete(self, patient_id: uuid.UUID, current_user: UserRead) -> PatientRead:
        patient, ref = self._get_accessible(patient_id, current_user)
        patient.status = PatientStatus.DELETED
        patient = self.patient_repo.update(patient)
        return self._to_read(patient, ref)

    def _get_accessible(self, patient_id: uuid.UUID, current_user: UserRead) -> tuple[Patient, PatientRef]:
        patient = self.patient_repo.get_by_id(patient_id)
        if patient is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found.")
        ref = self.ref_repo.get_by_id(patient.patient_ref_id)
        if ref is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient ref not found.")
        if current_user.role == UserRole.ADMIN:
            return patient, ref
        if ref.current_slp_id == current_user.id:
            return patient, ref
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    @staticmethod
    def _to_read(patient: Patient, ref: PatientRef) -> PatientRead:
        return PatientRead(
            id=patient.id,
            patient_ref_id=patient.patient_ref_id,
            name=patient.name,
            birth_date=patient.birth_date,
            gender=patient.gender,
            memo=patient.memo,
            status=patient.status,
            created_by_slp_id=ref.created_by_slp_id,
            current_slp_id=ref.current_slp_id,
            created_at=patient.created_at,
        )
