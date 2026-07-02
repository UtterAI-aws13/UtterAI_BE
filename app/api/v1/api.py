"""Version 1 router registry."""

from fastapi import APIRouter

from app.api.v1.endpoints.analysis import internal_router as analysis_internal_router
from app.api.v1.endpoints.analysis import router as analysis_router
from app.api.v1.endpoints.audio import router as audio_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.insight_map import case_index_router as soap_case_index_router
from app.api.v1.endpoints.insight_map import router as insight_map_router
from app.api.v1.endpoints.patients import router as patients_router
from app.api.v1.endpoints.report import router as report_router
from app.api.v1.endpoints.report_chat import router as report_chat_router
from app.api.v1.endpoints.session_transcript import router as session_transcript_router
from app.api.v1.endpoints.sessions import router as sessions_router
from app.api.v1.endpoints.templates import router as templates_router
from app.api.v1.endpoints.transcript import internal_result_router as transcript_internal_result_router
from app.api.v1.endpoints.transcript import router as transcript_router

api_v1_router = APIRouter()

api_v1_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_v1_router.include_router(patients_router, prefix="/patients", tags=["patients"])
api_v1_router.include_router(sessions_router, prefix="/sessions", tags=["sessions"])
api_v1_router.include_router(session_transcript_router, prefix="/sessions", tags=["sessions"])
api_v1_router.include_router(audio_router, prefix="/audio-files", tags=["audio-files"])
api_v1_router.include_router(analysis_router, prefix="/analysis-jobs", tags=["analysis-jobs"])
api_v1_router.include_router(report_router, prefix="/reports", tags=["reports"])
api_v1_router.include_router(report_chat_router, prefix="/reports", tags=["report-chat"])
api_v1_router.include_router(templates_router, prefix="/templates", tags=["templates"])
api_v1_router.include_router(transcript_router, prefix="/transcripts", tags=["transcripts"])
api_v1_router.include_router(insight_map_router, prefix="/insight-map", tags=["insight-map"])
api_v1_router.include_router(
    soap_case_index_router, prefix="/soap-case-indexes", tags=["insight-map"]
)
api_v1_router.include_router(
    analysis_internal_router,
    prefix="/internal/analysis-jobs",
    tags=["internal-analysis-jobs"],
)
api_v1_router.include_router(
    transcript_internal_result_router,
    prefix="/internal/analysis-results",
    tags=["internal-analysis-results"],
)
