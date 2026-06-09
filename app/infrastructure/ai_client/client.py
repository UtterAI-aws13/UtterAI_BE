"""HTTP client wrapper for dispatching analysis jobs to the AI service."""

from __future__ import annotations

from typing import Any

import httpx
from opentelemetry import trace

from app.core.config import get_settings

settings = get_settings()


class AIClient:
    """Dispatch analysis job requests to the external AI service.

    The backend owns job persistence and status tracking, while the AI service
    performs VAD, diarization, STT, and later result generation.
    """

    def dispatch_analysis_job(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        """Send an analysis job request if an AI service base URL is configured.

        When no AI base URL is configured, local development can still create a
        requested job row. The service returns `None` so callers know dispatch
        was intentionally skipped rather than silently failed.
        """

        if not settings.ai_service_base_url:
            return None

        url = f"{settings.ai_service_base_url.rstrip('/')}{settings.ai_service_analysis_path}"
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("ai_client.dispatch_analysis_job") as span:
            span.set_attribute("http.request.method", "POST")
            span.set_attribute("http.request.url", url)
            span.set_attribute("ai.service.base_url", settings.ai_service_base_url)
            response = httpx.post(
                url,
                json=payload,
                headers={"X-Internal-Token": settings.internal_callback_token},
                timeout=30.0,
            )
            span.set_attribute("http.response.status_code", response.status_code)
            response.raise_for_status()
            return response.json() if response.content else {}
