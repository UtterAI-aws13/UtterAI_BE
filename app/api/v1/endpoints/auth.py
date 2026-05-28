"""Authentication endpoint placeholders."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def auth_health() -> dict[str, str]:
    """Temporary route confirming the auth router is mounted correctly."""

    return {"domain": "auth", "status": "pending"}
