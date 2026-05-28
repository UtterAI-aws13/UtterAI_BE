"""Application entrypoint for the UtterAI backend service."""

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import get_settings


def create_application() -> FastAPI:
    """Create the FastAPI application with shared configuration and routers.

    The factory pattern keeps startup wiring in one place and makes it easier
    to reuse the same app configuration in tests later.
    """

    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Every versioned router is attached here so the entrypoint stays thin.
    app.include_router(api_router, prefix=settings.api_prefix)

    @app.get("/health", tags=["health"])
    def health_check() -> dict[str, str]:
        """Return a minimal liveness payload for load balancers and probes."""

        return {"status": "ok"}

    return app


app = create_application()
