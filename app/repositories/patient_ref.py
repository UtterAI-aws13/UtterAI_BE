"""Database access helpers for patient reference records."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import PatientRef


class PatientRefRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, created_by_slp_id: uuid.UUID, current_slp_id: uuid.UUID) -> PatientRef:
        ref = PatientRef(
            created_by_slp_id=created_by_slp_id,
            current_slp_id=current_slp_id,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(ref)
        self.db.flush()
        return ref

    def get_by_id(self, patient_ref_id: uuid.UUID) -> PatientRef | None:
        stmt = select(PatientRef).where(PatientRef.id == patient_ref_id)
        return self.db.execute(stmt).scalar_one_or_none()
