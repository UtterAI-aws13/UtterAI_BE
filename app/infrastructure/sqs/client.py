"""AWS SQS helper for dispatching analysis job messages."""

from __future__ import annotations

import json
from typing import Any

import boto3

from app.core.config import get_settings

settings = get_settings()


class SQSClient:
    """Publish analysis job messages to the audio preprocess queue."""

    def __init__(self) -> None:
        self.client = boto3.client("sqs", region_name=settings.aws_region)

    def send_analysis_job(self, payload: dict[str, Any]) -> None:
        """Send an analysis job message to the SQS queue.

        Returns without sending when the queue URL is not configured so that
        local development can still create job rows without AWS credentials.
        """
        if not settings.sqs_audio_preprocess_queue_url:
            return

        self.client.send_message(
            QueueUrl=settings.sqs_audio_preprocess_queue_url,
            MessageBody=json.dumps(payload),
        )