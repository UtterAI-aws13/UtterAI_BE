"""Unit tests for SQSClient."""

import json
from unittest.mock import MagicMock, patch

import pytest

from app.infrastructure.sqs.client import SQSClient


@pytest.fixture
def mock_settings_with_url():
    with patch("app.infrastructure.sqs.client.settings") as s:
        s.aws_region = "ap-northeast-2"
        s.sqs_audio_preprocess_queue_url = "https://sqs.ap-northeast-2.amazonaws.com/123/test-queue"
        yield s


@pytest.fixture
def mock_settings_no_url():
    with patch("app.infrastructure.sqs.client.settings") as s:
        s.aws_region = "ap-northeast-2"
        s.sqs_audio_preprocess_queue_url = ""
        yield s


class TestSQSClientSendAnalysisJob:
    def test_sends_message_when_queue_url_configured(self, mock_settings_with_url):
        mock_boto = MagicMock()
        with patch("app.infrastructure.sqs.client.boto3") as mock_b:
            mock_b.client.return_value = mock_boto
            client = SQSClient()

        payload = {"job_id": "abc", "session_id": "xyz"}
        client.send_analysis_job(payload)

        mock_boto.send_message.assert_called_once()
        call_kwargs = mock_boto.send_message.call_args[1]
        assert call_kwargs["QueueUrl"] == mock_settings_with_url.sqs_audio_preprocess_queue_url
        assert json.loads(call_kwargs["MessageBody"]) == payload

    def test_skips_send_when_queue_url_empty(self, mock_settings_no_url):
        mock_boto = MagicMock()
        with patch("app.infrastructure.sqs.client.boto3") as mock_b:
            mock_b.client.return_value = mock_boto
            client = SQSClient()

        client.send_analysis_job({"job_id": "abc"})

        mock_boto.send_message.assert_not_called()

    def test_propagates_boto3_exception(self, mock_settings_with_url):
        mock_boto = MagicMock()
        mock_boto.send_message.side_effect = RuntimeError("SQS unavailable")
        with patch("app.infrastructure.sqs.client.boto3") as mock_b:
            mock_b.client.return_value = mock_boto
            client = SQSClient()

        with pytest.raises(RuntimeError, match="SQS unavailable"):
            client.send_analysis_job({"job_id": "abc"})

    def test_payload_serialized_as_json(self, mock_settings_with_url):
        mock_boto = MagicMock()
        with patch("app.infrastructure.sqs.client.boto3") as mock_b:
            mock_b.client.return_value = mock_boto
            client = SQSClient()

        payload = {
            "job_id": "j1",
            "audio": {"bucket": "b", "key": "k", "content_type": "audio/wav"},
            "options": {"template_id": "t1"},
        }
        client.send_analysis_job(payload)

        body = mock_boto.send_message.call_args[1]["MessageBody"]
        assert isinstance(body, str)
        assert json.loads(body)["audio"]["bucket"] == "b"
        assert json.loads(body)["options"]["template_id"] == "t1"
