"""AWS SQS helper for dispatching analysis job messages."""

from __future__ import annotations

import json
from typing import Any

import boto3
from opentelemetry import trace
from opentelemetry.propagate import inject

from app.core.config import get_settings
from app.observability.metrics import record_sqs_dispatch

settings = get_settings()

_tracer = trace.get_tracer(__name__)


def _carrier_to_message_attributes(carrier: dict[str, str]) -> dict[str, dict[str, str]]:
    return {k: {"DataType": "String", "StringValue": v} for k, v in carrier.items()}


class SQSClient:
    _client: Any = None

    @classmethod
    def _get_client(cls) -> Any:
        if cls._client is None:
            cls._client = boto3.client("sqs", region_name=settings.aws_region)
        return cls._client

    def send_analysis_job(self, payload: dict[str, Any]) -> None:
        if not settings.sqs_audio_preprocess_queue_url:
            return

        queue = "audio-preprocess"
        # PRODUCER span: service_map 프로세서가 backend → cpu-worker 엣지를 생성하려면
        # inject()가 캡처하는 span의 kind가 PRODUCER여야 한다.
        with _tracer.start_as_current_span(
            "sqs.publish.analysis_job",
            kind=trace.SpanKind.PRODUCER,
        ) as span:
            span.set_attribute("messaging.system", "aws_sqs")
            span.set_attribute("messaging.destination.name", queue)

            carrier: dict[str, str] = {}
            inject(carrier)
            if carrier.get("traceparent"):
                payload = {**payload, "traceparent": carrier["traceparent"]}

            try:
                self._get_client().send_message(
                    QueueUrl=settings.sqs_audio_preprocess_queue_url,
                    MessageBody=json.dumps(payload),
                    MessageAttributes=_carrier_to_message_attributes(carrier),
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

        queue = "report-analysis"
        with _tracer.start_as_current_span(
            "sqs.publish.report_job",
            kind=trace.SpanKind.PRODUCER,
        ) as span:
            span.set_attribute("messaging.system", "aws_sqs")
            span.set_attribute("messaging.destination.name", queue)

            carrier: dict[str, str] = {}
            inject(carrier)
            if carrier.get("traceparent"):
                payload["traceparent"] = carrier["traceparent"]

            try:
                self._get_client().send_message(
                    QueueUrl=settings.sqs_report_analysis_queue_url,
                    MessageBody=json.dumps(payload),
                    MessageAttributes=_carrier_to_message_attributes(carrier),
                )
                record_sqs_dispatch(queue, "success")
            except Exception:
                record_sqs_dispatch(queue, "error")
                raise
