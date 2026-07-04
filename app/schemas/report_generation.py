"""5-Agent 리포트 생성 트리거/조회 스키마 (AI 서비스 프록시)."""

from __future__ import annotations

import uuid

from pydantic import BaseModel


class ReportGenerationCreateRequest(BaseModel):
    """session_id는 path param으로 받으므로 patient_ref_id/therapist_id는
    서버가 세션 row에서 직접 채운다 (report_chat/audio 서비스와 동일 신뢰 경계).
    """

    selected_analysis: list[str] = ["MLU", "TTR", "NDW"]
    history_session_count: int = 5


class ReportGenerationCreateResponse(BaseModel):
    run_id: uuid.UUID
    status: str


class ReportGenerationStatusResponse(BaseModel):
    run_id: uuid.UUID
    status: str
    current_node: str | None = None
    retry_summary: dict[str, int] | None = None
    report_draft_id: uuid.UUID | None = None
    quality_scores: dict[str, float] | None = None
    failure_code: str | None = None
    reason_codes: list[str] | None = None
