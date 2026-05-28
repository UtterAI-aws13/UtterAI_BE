"""Session domain endpoint placeholders."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def sessions_health() -> dict[str, str]:
    """Temporary route confirming the session router is mounted correctly."""

    return {"domain": "sessions", "status": "pending"}
