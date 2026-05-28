"""Version 1 router registry."""

from fastapi import APIRouter

from app.api.v1.endpoints.analysis import internal_router as analysis_internal_router
from app.api.v1.endpoints.analysis import router as analysis_router
from app.api.v1.endpoints.audio import router as audio_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.children import router as children_router
from app.api.v1.endpoints.session_transcript import router as session_transcript_router
from app.api.v1.endpoints.sessions import router as sessions_router
from app.api.v1.endpoints.transcript import internal_result_router as transcript_internal_result_router
from app.api.v1.endpoints.transcript import router as transcript_router

api_v1_router = APIRouter()

# Routers are registered early even if endpoints are placeholders so that the
# final URL structure is stable while the domain implementations grow.
api_v1_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_v1_router.include_router(children_router, prefix="/children", tags=["children"])
api_v1_router.include_router(sessions_router, prefix="/sessions", tags=["sessions"])
api_v1_router.include_router(session_transcript_router, prefix="/sessions", tags=["sessions"])
api_v1_router.include_router(audio_router, prefix="/audio-files", tags=["audio-files"])
api_v1_router.include_router(analysis_router, prefix="/analysis-jobs", tags=["analysis-jobs"])
api_v1_router.include_router(transcript_router, prefix="/transcripts", tags=["transcripts"])
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
