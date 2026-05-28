"""Child domain endpoint placeholders."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def children_health() -> dict[str, str]:
    """Temporary route confirming the child router is mounted correctly."""

    return {"domain": "children", "status": "pending"}
