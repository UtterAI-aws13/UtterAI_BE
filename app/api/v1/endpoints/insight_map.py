"""Insight map Graph API: concept/patient-history/SOAP-case-index visualization + search."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.db import get_db_session
from app.schemas.auth import UserRead
from app.schemas.insight_map import (
    EvidenceResponse,
    InsightMapResponse,
    InsightMapSearchRequest,
    SourceLinkResponse,
)
from app.services.insight_map import InsightMapService

router = APIRouter()
case_index_router = APIRouter()

_DEFAULT_MODE = ["research", "current_patient", "my_soap"]


@router.get("", response_model=InsightMapResponse)
def get_insight_map(
    report_draft_id: uuid.UUID | None = Query(default=None),
    mode: list[str] = Query(default=_DEFAULT_MODE),
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> InsightMapResponse:
    service = InsightMapService(db)
    return service.get_insight_map(report_draft_id, mode, current_user)


@router.post("/search", response_model=InsightMapResponse)
def search_insight_map(
    request: InsightMapSearchRequest,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> InsightMapResponse:
    service = InsightMapService(db)
    return service.search(request.query, request.report_draft_id, request.mode, current_user)


@router.get("/concepts/{concept_key}/evidence", response_model=EvidenceResponse)
def get_concept_evidence(
    concept_key: str,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> EvidenceResponse:
    service = InsightMapService(db)
    return service.get_concept_evidence(concept_key, current_user)


@case_index_router.get("/{case_index_id}/source-link", response_model=SourceLinkResponse)
def get_case_index_source_link(
    case_index_id: uuid.UUID,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> SourceLinkResponse:
    service = InsightMapService(db)
    return service.get_source_link(case_index_id, current_user)
