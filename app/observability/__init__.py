"""Observability helpers for tracing and metrics."""

from app.observability.metrics import (
    record_analysis_job_callback_received,
    record_analysis_job_created,
    record_analysis_job_dispatched,
    record_analysis_job_dispatch_failed,
    record_audio_upload_completed,
)
from app.observability.otel import get_meter, get_tracer, initialize_observability, instrument_fastapi_app

__all__ = [
    "get_meter",
    "get_tracer",
    "initialize_observability",
    "instrument_fastapi_app",
    "record_analysis_job_callback_received",
    "record_analysis_job_created",
    "record_analysis_job_dispatched",
    "record_analysis_job_dispatch_failed",
    "record_audio_upload_completed",
]
