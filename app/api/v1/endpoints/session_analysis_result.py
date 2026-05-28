"""Session-centric analysis result lookup endpoints."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.db import get_db_session
from app.schemas.analysis_result import AnalysisResultRead
from app.schemas.auth import UserRead
from app.services.analysis_result_read import AnalysisResultReadService

router = APIRouter()


@router.get("/{session_id}/analysis-results", response_model=AnalysisResultRead)
def get_session_analysis_result(
    session_id: uuid.UUID,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> AnalysisResultRead:
    """Return the latest analysis result for a session."""

    service = AnalysisResultReadService(db)
    return service.get_result_by_session(session_id, current_user)
