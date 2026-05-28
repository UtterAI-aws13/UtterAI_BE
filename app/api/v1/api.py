"""Version 1 router registry."""

from fastapi import APIRouter

from app.api.v1.endpoints.audio import router as audio_router
from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.children import router as children_router
from app.api.v1.endpoints.sessions import router as sessions_router

api_v1_router = APIRouter()

# Routers are registered early even if endpoints are placeholders so that the
# final URL structure is stable while the domain implementations grow.
api_v1_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_v1_router.include_router(children_router, prefix="/children", tags=["children"])
api_v1_router.include_router(sessions_router, prefix="/sessions", tags=["sessions"])
api_v1_router.include_router(audio_router, prefix="/audio-files", tags=["audio-files"])
