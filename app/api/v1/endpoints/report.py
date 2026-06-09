"""Report read, segment edit, and approval endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.db import get_db_session
from app.schemas.auth import UserRead
from app.schemas.report import (
    ApprovalCreateRequest,
    ApprovalHistoryRead,
    ReportRead,
    ReportSegmentRead,
    ReportSegmentUpdateRequest,
    ReportStatusUpdateRequest,
)
from app.services.report import ReportService

router = APIRouter()


@router.get("", response_model=list[ReportRead])
def list_reports(
    session_id: uuid.UUID | None = Query(default=None),
    patient_ref_id: uuid.UUID | None = Query(default=None),
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> list[ReportRead]:
    service = ReportService(db)
    return service.list(current_user, session_id, patient_ref_id)


@router.get("/{report_id}", response_model=ReportRead)
def get_report(
    report_id: uuid.UUID,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> ReportRead:
    service = ReportService(db)
    return service.get(report_id, current_user)


@router.get("/{report_id}/segments", response_model=list[ReportSegmentRead])
def list_report_segments(
    report_id: uuid.UUID,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> list[ReportSegmentRead]:
    service = ReportService(db)
    return service.get_segments(report_id, current_user)


@router.patch("/{report_id}/segments/{segment_id}", response_model=ReportSegmentRead)
def update_report_segment(
    report_id: uuid.UUID,
    segment_id: uuid.UUID,
    request: ReportSegmentUpdateRequest,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> ReportSegmentRead:
    service = ReportService(db)
    return service.update_segment(report_id, segment_id, request, current_user)


@router.patch("/{report_id}/status", response_model=ReportRead)
def update_report_status(
    report_id: uuid.UUID,
    request: ReportStatusUpdateRequest,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> ReportRead:
    service = ReportService(db)
    return service.update_status(report_id, request, current_user)


@router.post("/{report_id}/approvals", response_model=ApprovalHistoryRead, status_code=201)
def create_approval(
    report_id: uuid.UUID,
    request: ApprovalCreateRequest,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> ApprovalHistoryRead:
    service = ReportService(db)
    return service.create_approval(report_id, request, current_user)


@router.get("/{report_id}/approvals", response_model=list[ApprovalHistoryRead])
def list_approvals(
    report_id: uuid.UUID,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> list[ApprovalHistoryRead]:
    service = ReportService(db)
    return service.list_approvals(report_id, current_user)
