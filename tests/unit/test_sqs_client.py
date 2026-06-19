"""Unit tests for SQSClient."""

import json
from unittest.mock import MagicMock, patch

import pytest

from app.infrastructure.sqs.client import SQSClient


@pytest.fixture(autouse=True)
def reset_sqs_singleton():
    SQSClient._client = None
    yield
    SQSClient._client = None


@pytest.fixture
def mock_boto():
    mock = MagicMock()
    with patch("app.infrastructure.sqs.client.boto3") as mock_b:
        mock_b.client.return_value = mock
        yield mock


@pytest.fixture
def mock_settings_with_url():
    with patch("app.infrastructure.sqs.client.settings") as s:
        s.aws_region = "ap-northeast-2"
        s.sqs_audio_preprocess_queue_url = "https://sqs.ap-northeast-2.amazonaws.com/123/test-queue"
        s.sqs_report_analysis_queue_url = ""
        yield s


@pytest.fixture
def mock_settings_no_url():
    with patch("app.infrastructure.sqs.client.settings") as s:
        s.aws_region = "ap-northeast-2"
        s.sqs_audio_preprocess_queue_url = ""
        s.sqs_report_analysis_queue_url = ""
        yield s


class TestSQSClientSendAnalysisJob:
    def test_sends_message_when_queue_url_configured(self, mock_boto, mock_settings_with_url):
        client = SQSClient()
        payload = {"job_id": "abc", "session_id": "xyz"}
        client.send_analysis_job(payload)

        mock_boto.send_message.assert_called_once()
        call_kwargs = mock_boto.send_message.call_args[1]
        assert call_kwargs["QueueUrl"] == mock_settings_with_url.sqs_audio_preprocess_queue_url
        assert json.loads(call_kwargs["MessageBody"]) == payload

    def test_skips_send_when_queue_url_empty(self, mock_boto, mock_settings_no_url):
        client = SQSClient()
        client.send_analysis_job({"job_id": "abc"})

        mock_boto.send_message.assert_not_called()

    def test_propagates_boto3_exception(self, mock_boto, mock_settings_with_url):
        mock_boto.send_message.side_effect = RuntimeError("SQS unavailable")
        client = SQSClient()

        with pytest.raises(RuntimeError, match="SQS unavailable"):
            client.send_analysis_job({"job_id": "abc"})

    def test_payload_serialized_as_json(self, mock_boto, mock_settings_with_url):
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

    def test_boto3_client_reused_across_instances(self, mock_boto, mock_settings_with_url):
        SQSClient().send_analysis_job({"job_id": "a"})
        SQSClient().send_analysis_job({"job_id": "b"})

        import app.infrastructure.sqs.client as sqs_module
        sqs_module.boto3.client.assert_called_once()