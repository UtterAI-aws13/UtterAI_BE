"""Database access helpers for language metrics persistence."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import TargetSpeaker
from app.models.entities import LanguageMetrics


class LanguageMetricsRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, metrics: LanguageMetrics) -> LanguageMetrics:
        self.db.add(metrics)
        self.db.commit()
        self.db.refresh(metrics)
        return metrics

    def get_by_job_and_speaker(
        self, job_id: uuid.UUID, target_speaker: TargetSpeaker
    ) -> LanguageMetrics | None:
        statement = select(LanguageMetrics).where(
            LanguageMetrics.job_id == job_id,
            LanguageMetrics.target_speaker == target_speaker,
        )
        return self.db.execute(statement).scalar_one_or_none()

    def list_by_session(self, session_id: uuid.UUID) -> list[LanguageMetrics]:
        statement = (
            select(LanguageMetrics)
            .where(LanguageMetrics.session_id == session_id)
            .order_by(LanguageMetrics.created_at.desc())
        )
        return list(self.db.execute(statement).scalars().all())

    def list_by_job(self, job_id: uuid.UUID) -> list[LanguageMetrics]:
        statement = select(LanguageMetrics).where(LanguageMetrics.job_id == job_id)
        return list(self.db.execute(statement).scalars().all())
