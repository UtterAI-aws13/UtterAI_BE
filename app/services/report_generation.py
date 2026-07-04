"""5-Agent 리포트 생성: 세션 접근권한 확인 후 AI 서비스로 프록시한다.

report_chat.py의 _call_ai_service()와 동일한 재시도/에러 매핑 패턴을 따른다.
AI 서비스는 session_id/patient_ref_id/therapist_id로 자체 권한도 다시
검증하므로(app.services.authorization_service), 여기서의 권한 확인은
"이 요청 자체를 보낼 자격"만 확인하는 1차 관문이다.
"""

from __future__ import annotations

import logging
import uuid

import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session as DbSession

from app.core.config import get_settings
from app.core.enums import SessionStatus, UserRole
from app.repositories.session import SessionRepository
from app.schemas.auth import UserRead
from app.schemas.report_generation import (
    ReportGenerationCreateRequest,
    ReportGenerationCreateResponse,
    ReportGenerationStatusResponse,
)

settings = get_settings()
logger = logging.getLogger(__name__)

_AI_SERVICE_MAX_ATTEMPTS = 2


class ReportGenerationService:
    def __init__(self, db: DbSession) -> None:
        self._db = db
        self._session_repository = SessionRepository(db)

    def create_run(
        self,
        session_id: uuid.UUID,
        request: ReportGenerationCreateRequest,
        current_user: UserRead,
    ) -> ReportGenerationCreateResponse:
        session = self._get_accessible_session(session_id, current_user)

        payload = {
            "patient_ref_id": str(session.patient_ref_id),
            "therapist_id": str(session.slp_id),
            "selected_analysis": request.selected_analysis,
            "history_session_count": request.history_session_count,
        }
        result = self._call_ai_service(
            "post", f"/internal/ai/sessions/{session_id}/reports/generate", json=payload
        )
        return ReportGenerationCreateResponse(**result)

    def get_run(
        self, run_id: uuid.UUID, current_user: UserRead
    ) -> ReportGenerationStatusResponse:
        result = self._call_ai_service(
            "get",
            f"/internal/ai/report-generation-runs/{run_id}",
            params={"therapist_id": str(current_user.id)},
        )
        return ReportGenerationStatusResponse(**result)

    def _get_accessible_session(self, session_id: uuid.UUID, current_user: UserRead):
        session = self._session_repository.get_by_id(session_id)
        if session is None or session.status == SessionStatus.DELETED:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found.",
            )
        if current_user.role == UserRole.ADMIN:
            return session
        if current_user.role == UserRole.SLP and session.slp_id == current_user.id:
            return session
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this session.",
        )

    # ai-service는 cpu-worker와 spot NodePool을 공유한다 - report_chat.py의
    # _call_ai_service()와 동일한 이유로, 연결 자체가 끊긴 경우(RequestError)에
    # 한해 한 번만 재시도한다.
    def _call_ai_service(self, method: str, path: str, **kwargs) -> dict:
        url = f"{settings.ai_service_base_url}{path}"
        last_exc: httpx.RequestError | None = None
        for attempt in range(1, _AI_SERVICE_MAX_ATTEMPTS + 1):
            try:
                with httpx.Client(timeout=60.0) as client:
                    resp = client.request(method, url, **kwargs)
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 404:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND, detail="Run not found."
                    ) from exc
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"AI service error: {exc.response.status_code}",
                ) from exc
            except httpx.RequestError as exc:
                last_exc = exc
                logger.warning(
                    f"[report-generation] AI 서비스 연결 실패 (attempt {attempt}/"
                    f"{_AI_SERVICE_MAX_ATTEMPTS}): {exc}"
                )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service is unreachable.",
        ) from last_exc
