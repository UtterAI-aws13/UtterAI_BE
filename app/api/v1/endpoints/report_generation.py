"""5-Agent 리포트 생성 트리거/조회 엔드포인트 (AI 서비스 프록시)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.db import get_db_session
from app.schemas.auth import UserRead
from app.schemas.report_generation import (
    ReportGenerationCreateRequest,
    ReportGenerationCreateResponse,
    ReportGenerationStatusResponse,
)
from app.services.report_generation import ReportGenerationService

router = APIRouter()


@router.post(
    "/sessions/{session_id}/reports/generate", response_model=ReportGenerationCreateResponse
)
def create_report_generation_run(
    session_id: uuid.UUID,
    request: ReportGenerationCreateRequest,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> ReportGenerationCreateResponse:
    service = ReportGenerationService(db)
    return service.create_run(session_id, request, current_user)


@router.get(
    "/report-generation-runs/{run_id}", response_model=ReportGenerationStatusResponse
)
def get_report_generation_run(
    run_id: uuid.UUID,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> ReportGenerationStatusResponse:
    service = ReportGenerationService(db)
    return service.get_run(run_id, current_user)
