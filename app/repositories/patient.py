"""Database access helpers for patient records."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import PatientStatus
from app.models.entities import Patient, PatientRef


class PatientRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, patient: Patient) -> Patient:
        self.db.add(patient)
        self.db.commit()
        self.db.refresh(patient)
        return patient

    def get_by_id(self, patient_id: uuid.UUID) -> Patient | None:
        stmt = select(Patient).where(
            Patient.id == patient_id,
            Patient.status == PatientStatus.ACTIVE,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_ref_id(self, patient_ref_id: uuid.UUID) -> Patient | None:
        stmt = select(Patient).where(Patient.patient_ref_id == patient_ref_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def list_by_slp(self, slp_id: uuid.UUID) -> list[Patient]:
        stmt = (
            select(Patient)
            .join(PatientRef, Patient.patient_ref_id == PatientRef.id)
            .where(
                PatientRef.current_slp_id == slp_id,
                Patient.status == PatientStatus.ACTIVE,
            )
        )
        return list(self.db.execute(stmt).scalars())

    def list_all_active(self) -> list[Patient]:
        stmt = select(Patient).where(Patient.status == PatientStatus.ACTIVE)
        return list(self.db.execute(stmt).scalars())

    def update(self, patient: Patient) -> Patient:
        self.db.commit()
        self.db.refresh(patient)
        return patient
