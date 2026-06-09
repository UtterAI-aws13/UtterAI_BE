"""Business-level metrics for the backend service."""

from __future__ import annotations

from functools import lru_cache

from opentelemetry import metrics


@lru_cache(maxsize=1)
def _meter():
    return metrics.get_meter("utterai.backend.metrics")


@lru_cache(maxsize=1)
def _analysis_job_created_counter():
    return _meter().create_counter(
        "utterai_analysis_jobs_created_total",
        description="Total number of analysis jobs created by the backend.",
    )


@lru_cache(maxsize=1)
def _analysis_job_dispatch_counter():
    return _meter().create_counter(
        "utterai_analysis_job_dispatch_total",
        description="Total number of analysis job dispatch attempts to the AI service.",
    )


@lru_cache(maxsize=1)
def _analysis_job_callback_counter():
    return _meter().create_counter(
        "utterai_analysis_result_callbacks_total",
        description="Total number of completed analysis callbacks stored by the backend.",
    )


@lru_cache(maxsize=1)
def _audio_upload_completed_counter():
    return _meter().create_counter(
        "utterai_audio_uploads_completed_total",
        description="Total number of audio uploads marked complete by the backend.",
    )


def record_analysis_job_created() -> None:
    _analysis_job_created_counter().add(1)


def record_analysis_job_dispatched() -> None:
    _analysis_job_dispatch_counter().add(1, {"status": "success"})


def record_analysis_job_dispatch_failed() -> None:
    _analysis_job_dispatch_counter().add(1, {"status": "failed"})


def record_analysis_job_callback_received() -> None:
    _analysis_job_callback_counter().add(1)


def record_audio_upload_completed() -> None:
    _audio_upload_completed_counter().add(1)
