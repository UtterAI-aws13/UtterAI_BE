"""Unit tests for TranscriptService finalize and list_segments changes."""

import json
import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.core.enums import SessionStatus, SpeakerRole, TranscriptStatus, UserRole, UserStatus
from app.models.entities import Session, Transcript, TranscriptSegment
from app.schemas.auth import UserRead
from app.services.transcript import TranscriptService


def _make_user(role: UserRole = UserRole.SLP) -> UserRead:
    return UserRead(
        id=uuid.uuid4(),
        email="slp@test.com",
        name="Test SLP",
        role=role,
        status=UserStatus.ACTIVE,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


def _make_session(slp_id: uuid.UUID, status: SessionStatus = SessionStatus.ANALYSIS_COMPLETED) -> Session:
    s = MagicMock(spec=Session)
    s.id = uuid.uuid4()
    s.slp_id = slp_id
    s.status = status
    return s


def _make_transcript(session_id: uuid.UUID, status: TranscriptStatus = TranscriptStatus.DRAFT) -> Transcript:
    t = MagicMock(spec=Transcript)
    t.id = uuid.uuid4()
    t.session_id = session_id
    t.job_id = uuid.uuid4()
    t.audio_file_id = uuid.uuid4()
    t.status = status
    t.final_s3_key = None
    return t


def _make_segment(transcript_id: uuid.UUID, session_id: uuid.UUID, idx: int = 0) -> TranscriptSegment:
    seg = MagicMock(spec=TranscriptSegment)
    seg.id = uuid.uuid4()
    seg.transcript_id = transcript_id
    seg.session_id = session_id
    seg.segment_index = idx
    seg.speaker_label = "SPEAKER_0"
    seg.speaker_role = SpeakerRole.PATIENT
    seg.start_ms = idx * 1000
    seg.end_ms = (idx + 1) * 1000
    seg.original_text = f"발화 {idx}"
    seg.text = f"발화 {idx}"
    seg.confidence = 0.9
    seg.is_edited = False
    seg.edited_by = None
    seg.edited_at = None
    seg.created_at = datetime.now()
    return seg


@pytest.fixture
def service():
    db = MagicMock()
    svc = TranscriptService(db)
    svc.transcript_repository = MagicMock()
    svc.analysis_job_repository = MagicMock()
    svc.session_repository = MagicMock()
    svc.s3_client = MagicMock()
    return svc


class TestFinalize:
    def test_uploads_segments_to_s3_and_clears_rds(self, service):
        user = _make_user()
        session = _make_session(slp_id=user.id)
        transcript = _make_transcript(session_id=session.id)

        segments = [_make_segment(transcript.id, session.id, i) for i in range(3)]
        service.transcript_repository.get_by_id.return_value = transcript
        service.transcript_repository.list_segments.return_value = segments
        service.transcript_repository.update.return_value = transcript
        service.transcript_repository.delete_segments.return_value = 3
        service.session_repository.get_by_id.return_value = session
        service.analysis_job_repository.get_by_id.return_value = None  # SQS 생략

        with patch("app.services.transcript.settings") as mock_settings:
            mock_settings.s3_bucket_transcript = "utterai-dev-transcripts"
            mock_settings.sqs_report_analysis_queue_url = ""
            service.finalize(transcript.id, user)

        service.s3_client.upload_bytes.assert_called_once()
        call_kwargs = service.s3_client.upload_bytes.call_args[1]
        assert call_kwargs["bucket"] == "utterai-dev-transcripts"
        assert call_kwargs["content_type"] == "application/json"
        uploaded = json.loads(call_kwargs["data"])
        assert len(uploaded) == 3

        service.transcript_repository.delete_segments.assert_called_once_with(transcript.id)

    def test_final_s3_key_saved_on_transcript(self, service):
        user = _make_user()
        session = _make_session(slp_id=user.id)
        transcript = _make_transcript(session_id=session.id)

        service.transcript_repository.get_by_id.return_value = transcript
        service.transcript_repository.list_segments.return_value = []
        service.transcript_repository.update.return_value = transcript
        service.session_repository.get_by_id.return_value = session
        service.analysis_job_repository.get_by_id.return_value = None

        with patch("app.services.transcript.settings") as mock_settings:
            mock_settings.s3_bucket_transcript = "utterai-dev-transcripts"
            mock_settings.sqs_report_analysis_queue_url = ""
            service.finalize(transcript.id, user)

        assert transcript.final_s3_key == f"finals/{transcript.session_id}/{transcript.id}.json"
        assert transcript.status == TranscriptStatus.FINALIZED

    def test_raises_409_when_already_finalized(self, service):
        user = _make_user()
        session = _make_session(slp_id=user.id)
        transcript = _make_transcript(session_id=session.id, status=TranscriptStatus.FINALIZED)

        service.transcript_repository.get_by_id.return_value = transcript
        service.session_repository.get_by_id.return_value = session

        with pytest.raises(HTTPException) as exc_info:
            service.finalize(transcript.id, user)
        assert exc_info.value.status_code == 409

    def test_sends_final_s3_key_in_sqs(self, service):
        user = _make_user()
        session = _make_session(slp_id=user.id)
        transcript = _make_transcript(session_id=session.id)
        job = MagicMock()
        job.id = uuid.uuid4()

        service.transcript_repository.get_by_id.return_value = transcript
        service.transcript_repository.list_segments.return_value = []
        service.transcript_repository.update.return_value = transcript
        service.session_repository.get_by_id.return_value = session
        service.analysis_job_repository.get_by_id.return_value = job

        with patch("app.services.transcript.settings") as mock_settings, \
             patch("app.services.transcript.SQSClient") as mock_sqs_cls:
            mock_settings.s3_bucket_transcript = "utterai-dev-transcripts"
            mock_settings.sqs_report_analysis_queue_url = "https://sqs/queue"
            mock_sqs = MagicMock()
            mock_sqs_cls.return_value = mock_sqs

            service.finalize(transcript.id, user)

        mock_sqs.send_report_job.assert_called_once()
        call_kwargs = mock_sqs.send_report_job.call_args[1]
        assert call_kwargs["final_s3_key"] == f"finals/{transcript.session_id}/{transcript.id}.json"


class TestListSegments:
    def test_reads_from_rds_when_draft(self, service):
        user = _make_user()
        session = _make_session(slp_id=user.id)
        transcript = _make_transcript(session_id=session.id, status=TranscriptStatus.DRAFT)
        segments = [_make_segment(transcript.id, session.id)]

        service.transcript_repository.get_by_id.return_value = transcript
        service.transcript_repository.list_segments.return_value = segments
        service.session_repository.get_by_id.return_value = session

        result = service.list_segments(transcript.id, user)

        service.transcript_repository.list_segments.assert_called_once_with(transcript.id)
        service.s3_client.get_object_bytes.assert_not_called()
        assert len(result) == 1

    def test_reads_from_s3_when_finalized(self, service):
        user = _make_user()
        session = _make_session(slp_id=user.id)
        transcript = _make_transcript(session_id=session.id, status=TranscriptStatus.FINALIZED)
        transcript.final_s3_key = f"finals/{session.id}/{transcript.id}.json"

        seg_id = uuid.uuid4()
        s3_payload = json.dumps([{
            "id": str(seg_id),
            "transcript_id": str(transcript.id),
            "session_id": str(session.id),
            "segment_index": 0,
            "speaker_label": "SPEAKER_0",
            "speaker_role": "PATIENT",
            "start_ms": 0,
            "end_ms": 1000,
            "original_text": "안녕",
            "text": "안녕",
            "confidence": 0.95,
            "is_edited": False,
            "edited_by": None,
            "edited_at": None,
            "created_at": datetime.now().isoformat(),
        }]).encode()

        service.transcript_repository.get_by_id.return_value = transcript
        service.session_repository.get_by_id.return_value = session
        service.s3_client.get_object_bytes.return_value = s3_payload

        with patch("app.services.transcript.settings") as mock_settings:
            mock_settings.s3_bucket_transcript = "utterai-dev-transcripts"
            result = service.list_segments(transcript.id, user)

        service.s3_client.get_object_bytes.assert_called_once_with(
            "utterai-dev-transcripts", transcript.final_s3_key
        )
        service.transcript_repository.list_segments.assert_not_called()
        assert len(result) == 1
        assert str(result[0].id) == str(seg_id)

    def test_falls_back_to_rds_when_finalized_but_no_s3_key(self, service):
        user = _make_user()
        session = _make_session(slp_id=user.id)
        transcript = _make_transcript(session_id=session.id, status=TranscriptStatus.FINALIZED)
        transcript.final_s3_key = None
        segments = [_make_segment(transcript.id, session.id)]

        service.transcript_repository.get_by_id.return_value = transcript
        service.transcript_repository.list_segments.return_value = segments
        service.session_repository.get_by_id.return_value = session

        result = service.list_segments(transcript.id, user)

        service.transcript_repository.list_segments.assert_called_once()
        service.s3_client.get_object_bytes.assert_not_called()
        assert len(result) == 1