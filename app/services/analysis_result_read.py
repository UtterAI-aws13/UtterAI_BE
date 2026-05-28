"""Read-only service logic for analysis result APIs."""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status

from app.core.enums import SessionStatus, UserRole
from app.repositories.analysis_result import AnalysisResultRepository
from app.repositories.session import SessionRepository
from app.schemas.analysis_result import AnalysisMetricsRead, AnalysisResultRead
from app.schemas.auth import UserRead


class AnalysisResultReadService:
    """Provide access-controlled read APIs for stored analysis results."""

    def __init__(self, db) -> None:
        self.analysis_result_repository = AnalysisResultRepository(db)
        self.session_repository = SessionRepository(db)

    def get_result(self, result_id: uuid.UUID, current_user: UserRead) -> AnalysisResultRead:
        """Return one analysis result after session-level access checks."""

        result = self.analysis_result_repository.get_result_by_id(result_id)
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis result not found.",
            )
        self._get_accessible_session(result.session_id, current_user)
        return AnalysisResultRead.model_validate(result)

    def get_result_by_session(
        self,
        session_id: uuid.UUID,
        current_user: UserRead,
    ) -> AnalysisResultRead:
        """Return the latest analysis result for a session."""

        self._get_accessible_session(session_id, current_user)
        result = self.analysis_result_repository.get_result_by_session_id(session_id)
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis result not found for this session.",
            )
        return AnalysisResultRead.model_validate(result)

    def get_metrics(self, result_id: uuid.UUID, current_user: UserRead) -> AnalysisMetricsRead:
        """Return only the metrics payload for one analysis result."""

        result = self.analysis_result_repository.get_result_by_id(result_id)
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis result not found.",
            )
        self._get_accessible_session(result.session_id, current_user)
        return AnalysisMetricsRead(
            result_id=result.id,
            session_id=result.session_id,
            metrics=result.metrics_json,
        )

    def _get_accessible_session(self, session_id: uuid.UUID, current_user: UserRead):
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
            detail="You do not have access to this analysis result.",
        )
