"""HTTP endpoints for report generation, listing, reads, and download."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.db import get_db_session
from app.schemas.auth import UserRead
from app.schemas.report import ReportCreateRequest, ReportRead
from app.services.report import ReportService

router = APIRouter()


@router.post("", response_model=ReportRead, status_code=201)
def generate_report(
    request: ReportCreateRequest,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> ReportRead:
    """Generate a report from a finalized SOAP note and analysis result."""

    service = ReportService(db)
    return service.generate(request, current_user)


@router.get("", response_model=list[ReportRead])
def list_reports(
    child_id: uuid.UUID | None = Query(default=None, alias="childId"),
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> list[ReportRead]:
    """List reports visible to the current user."""

    service = ReportService(db)
    return service.list(current_user, child_id)


@router.get("/{report_id}", response_model=ReportRead)
def get_report(
    report_id: uuid.UUID,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> ReportRead:
    """Return one report after access checks."""

    service = ReportService(db)
    return service.get(report_id, current_user)


@router.get("/{report_id}/download")
def download_report(
    report_id: uuid.UUID,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> PlainTextResponse:
    """Return the report as a downloadable text attachment for the MVP."""

    service = ReportService(db)
    filename, content = service.get_download_payload(report_id, current_user)
    return PlainTextResponse(
        content,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
