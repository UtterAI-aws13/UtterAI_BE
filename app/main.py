"""Application entrypoint for the UtterAI backend service."""

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.observability.otel import initialize_observability, instrument_fastapi_app


def create_application() -> FastAPI:
    """Create the FastAPI application with shared configuration and routers."""

    settings = get_settings()
    configure_logging(level=settings.log_level)
    initialize_observability()

    from app.api.router import api_router
    from app.core.db import get_db_session

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix=settings.api_prefix)
    instrument_fastapi_app(app)

    @app.get("/health", tags=["health"])
    def health_check() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/live", tags=["health"])
    def health_live() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/ready", tags=["health"])
    def health_ready(db: Session = Depends(get_db_session)) -> dict[str, str]:
        try:
            db.execute(text("SELECT 1"))
        except Exception:
            raise HTTPException(status_code=503, detail="database unavailable")
        return {"status": "ok"}

    return app


app = create_application()
