"""Analysis job request, status, cancel, and internal progress endpoints."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, verify_internal_token
from app.core.db import get_db_session
from app.core.enums import AnalysisJobStatus
from app.schemas.analysis import (
    AnalysisJobCancelResponse,
    AnalysisJobCreateRequest,
    AnalysisJobProgressCallbackRequest,
    AnalysisJobRead,
)
from app.schemas.auth import UserRead
from app.services.analysis import AnalysisJobService

router = APIRouter()
internal_router = APIRouter()


@router.post("", response_model=AnalysisJobRead, status_code=201)
def create_analysis_job(
    request: AnalysisJobCreateRequest,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> AnalysisJobRead:
    """Create a new analysis job for an uploaded audio file."""

    service = AnalysisJobService(db)
    return service.create(request, current_user)


@router.get("", response_model=list[AnalysisJobRead])
def list_analysis_jobs(
    session_id: uuid.UUID | None = Query(default=None),
    status_filter: AnalysisJobStatus | None = Query(default=None, alias="status"),
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> list[AnalysisJobRead]:
    """List visible analysis jobs with optional session/status filters."""

    service = AnalysisJobService(db)
    return service.list(current_user, session_id, status_filter)


@router.get("/{job_id}", response_model=AnalysisJobRead)
def get_analysis_job(
    job_id: uuid.UUID,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> AnalysisJobRead:
    """Return one analysis job after ownership checks."""

    service = AnalysisJobService(db)
    return service.get(job_id, current_user)


@router.patch("/{job_id}/cancel", response_model=AnalysisJobCancelResponse)
def cancel_analysis_job(
    job_id: uuid.UUID,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> AnalysisJobCancelResponse:
    """Cancel a still-active analysis job."""

    service = AnalysisJobService(db)
    return service.cancel(job_id, current_user)


@internal_router.post("/{job_id}/progress", response_model=AnalysisJobRead)
def update_analysis_job_progress(
    job_id: uuid.UUID,
    request: AnalysisJobProgressCallbackRequest,
    _: str = Depends(verify_internal_token),
    db: Session = Depends(get_db_session),
) -> AnalysisJobRead:
    """Apply progress updates sent by the internal AI service."""

    service = AnalysisJobService(db)
    return service.update_progress(job_id, request)
