"""Top-level API router composition."""

from fastapi import APIRouter

from app.api.v1.api import api_v1_router

api_router = APIRouter()

# The root API router only delegates to version-specific routers.
api_router.include_router(api_v1_router)
