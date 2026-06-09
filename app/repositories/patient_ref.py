"""Database access helpers for patient reference records."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

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
        statement = select(PatientRef).where(PatientRef.id == patient_ref_id)
        return self.db.execute(statement).scalar_one_or_none()
