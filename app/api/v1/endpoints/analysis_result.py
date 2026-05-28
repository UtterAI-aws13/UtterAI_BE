"""Analysis result read endpoints."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.db import get_db_session
from app.schemas.analysis_result import AnalysisMetricsRead, AnalysisResultRead
from app.schemas.auth import UserRead
from app.services.analysis_result_read import AnalysisResultReadService

router = APIRouter()


@router.get("/{result_id}", response_model=AnalysisResultRead)
def get_analysis_result(
    result_id: uuid.UUID,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> AnalysisResultRead:
    """Return one stored analysis result."""

    service = AnalysisResultReadService(db)
    return service.get_result(result_id, current_user)


@router.get("/{result_id}/metrics", response_model=AnalysisMetricsRead)
def get_analysis_result_metrics(
    result_id: uuid.UUID,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> AnalysisMetricsRead:
    """Return the metrics payload for one analysis result."""

    service = AnalysisResultReadService(db)
    return service.get_metrics(result_id, current_user)
