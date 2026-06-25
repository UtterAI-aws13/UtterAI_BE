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


# ── presigned URL 생성 ─────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _audio_upload_presign_counter():
    return _meter().create_counter(
        "audio_upload_total",
        description="presigned URL 발급 요청 수 (labels: status=success|error)",
    )


@lru_cache(maxsize=1)
def _audio_upload_presign_duration():
    return _meter().create_histogram(
        "audio_upload_presign_duration_seconds",
        description="presigned URL 생성 소요 시간",
        unit="s",
    )


def record_audio_presign_result(status: str) -> None:
    _audio_upload_presign_counter().add(1, {"status": status})


def record_audio_presign_duration(seconds: float) -> None:
    _audio_upload_presign_duration().record(seconds)


# ── SQS 디스패치 ──────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _sqs_dispatch_counter():
    return _meter().create_counter(
        "sqs_dispatch_total",
        description="SQS 메시지 발송 결과 (labels: queue, status=success|error)",
    )


def record_sqs_dispatch(queue: str, status: str) -> None:
    _sqs_dispatch_counter().add(1, {"queue": queue, "status": status})


# ── 세션 상태 전이 ────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _session_status_transition_counter():
    return _meter().create_counter(
        "session_status_transition_total",
        description="세션 상태 변경 횟수 (labels: from_status, to_status)",
    )


def record_session_status_transition(from_status: str, to_status: str) -> None:
    _session_status_transition_counter().add(1, {"from_status": from_status, "to_status": to_status})


# ── GPU 추론 큐 대기 시간 ─────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _gpu_inference_queue_wait():
    return _meter().create_histogram(
        "gpu_inference_queue_wait_seconds",
        description="SQS enqueue → GPU worker 처리 시작까지 대기 시간",
        unit="s",
    )


def record_gpu_inference_queue_wait(seconds: float) -> None:
    _gpu_inference_queue_wait().record(seconds)
