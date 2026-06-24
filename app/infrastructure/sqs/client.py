"""AWS SQS helper for dispatching analysis job messages."""

from __future__ import annotations

import json
from typing import Any

import boto3
from opentelemetry.propagate import inject

from app.core.config import get_settings
from app.observability.metrics import record_sqs_dispatch

settings = get_settings()


def _build_trace_message_attributes() -> dict[str, dict[str, str]]:
    """Inject the active OTel span context into SQS MessageAttributes (W3C traceparent)."""
    carrier: dict[str, str] = {}
    inject(carrier)
    return {k: {"DataType": "String", "StringValue": v} for k, v in carrier.items()}


class SQSClient:
    """Publish analysis job messages to the audio preprocess queue."""

    _client: Any = None

    @classmethod
    def _get_client(cls) -> Any:
        if cls._client is None:
            cls._client = boto3.client("sqs", region_name=settings.aws_region)
        return cls._client

    def send_analysis_job(self, payload: dict[str, Any]) -> None:
        """Send an analysis job message to the SQS queue.

        Returns without sending when the queue URL is not configured so that
        local development can still create job rows without AWS credentials.
        """
        if not settings.sqs_audio_preprocess_queue_url:
            return

        carrier: dict[str, str] = {}
        inject(carrier)
        if carrier.get("traceparent"):
            payload = {**payload, "traceparent": carrier["traceparent"]}

        queue = "audio-preprocess"
        try:
            self._get_client().send_message(
                QueueUrl=settings.sqs_audio_preprocess_queue_url,
                MessageBody=json.dumps(payload),
                MessageAttributes=_build_trace_message_attributes(),
            )
            record_sqs_dispatch(queue, "success")
        except Exception:
            record_sqs_dispatch(queue, "error")
            raise

    def send_report_job(
        self,
        job_id: str,
        session_id: str,
        transcript_id: str,
        template_id: str | None = None,
        final_s3_key: str | None = None,
    ) -> None:
        """Publish a report generation request to the report analysis queue.

        Returns without sending when the queue URL is not configured.
        """
        if not settings.sqs_report_analysis_queue_url:
            return

        payload: dict = {
            "job_id": job_id,
            "session_id": session_id,
            "transcript_id": transcript_id,
        }
        if template_id is not None:
            payload["template_id"] = template_id
        if final_s3_key is not None:
            payload["final_s3_key"] = final_s3_key

        carrier: dict[str, str] = {}
        inject(carrier)
        if carrier.get("traceparent"):
            payload["traceparent"] = carrier["traceparent"]

        queue = "report-analysis"
        try:
            self._get_client().send_message(
                QueueUrl=settings.sqs_report_analysis_queue_url,
                MessageBody=json.dumps(payload),
                MessageAttributes=_build_trace_message_attributes(),
            )
            record_sqs_dispatch(queue, "success")
        except Exception:
            record_sqs_dispatch(queue, "error")
            raise
