"""Database access helpers for patient reference records."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import PatientStatus
from app.models.entities import PatientRef


class PatientRefRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, patient_ref: PatientRef) -> PatientRef:
        self.db.add(patient_ref)
        self.db.commit()
        self.db.refresh(patient_ref)
        return patient_ref

    def get_by_id(self, patient_ref_id: uuid.UUID) -> PatientRef | None:
        stmt = select(PatientRef).where(
            PatientRef.id == patient_ref_id,
            PatientRef.status == PatientStatus.ACTIVE,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list_by_slp(self, slp_id: uuid.UUID) -> list[PatientRef]:
        stmt = select(PatientRef).where(
            PatientRef.current_slp_id == slp_id,
            PatientRef.status == PatientStatus.ACTIVE,
        )
        return list(self.db.execute(stmt).scalars())

    def list_all_active(self) -> list[PatientRef]:
        stmt = select(PatientRef).where(PatientRef.status == PatientStatus.ACTIVE)
        return list(self.db.execute(stmt).scalars())

    def update(self, patient_ref: PatientRef) -> PatientRef:
        self.db.commit()
        self.db.refresh(patient_ref)
        return patient_ref