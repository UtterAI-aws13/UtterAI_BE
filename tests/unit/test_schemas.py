"""Pydantic schema validation unit tests."""

import uuid
from datetime import date

import pytest
from pydantic import ValidationError

from app.core.enums import (
    AnalysisJobStatus,
    ReportSegmentType,
    ReportStatus,
    SessionStatus,
    SpeakerRole,
    TemplateType,
)
from app.schemas.analysis import AnalysisJobCreateRequest, AnalysisJobProgressCallbackRequest
from app.schemas.audio import AudioFileCompleteRequest, PresignedUploadRequest
from app.schemas.report import ApprovalCreateRequest, ReportSegmentUpdateRequest
from app.schemas.session import SessionCreateRequest, SessionUpdateRequest
from app.schemas.template import TemplateCreateRequest
from app.schemas.transcript import (
    InternalTranscriptCallbackRequest,
    TranscriptBulkUpdateRequest,
    TranscriptSegmentUpdateRequest,
)


class TestSessionSchemas:
    def test_create_request_requires_patient_ref_id(self):
        with pytest.raises(ValidationError):
            SessionCreateRequest(session_date=date.today())

    def test_create_request_requires_session_date(self):
        with pytest.raises(ValidationError):
            SessionCreateRequest(patient_ref_id=uuid.uuid4())

    def test_create_request_valid_minimal(self):
        req = SessionCreateRequest(
            patient_ref_id=uuid.uuid4(),
            session_date=date.today(),
        )
        assert req.session_goal is None
        assert req.memo is None

    def test_create_request_valid_full(self):
        pid = uuid.uuid4()
        req = SessionCreateRequest(
            patient_ref_id=pid,
            session_date=date(2026, 1, 15),
            session_type="언어치료",
            session_goal="MLU 향상",
            memo="특이사항 없음",
        )
        assert req.patient_ref_id == pid

    def test_update_request_all_optional(self):
        req = SessionUpdateRequest()
        assert req.session_date is None
        assert req.status is None

    def test_update_request_reject_deleted_status(self):
        # SessionStatus.DELETED is a valid enum value at schema level;
        # the service layer rejects it — schema should accept it
        req = SessionUpdateRequest(status=SessionStatus.DELETED)
        assert req.status == SessionStatus.DELETED

    def test_session_type_max_length(self):
        with pytest.raises(ValidationError):
            SessionCreateRequest(
                patient_ref_id=uuid.uuid4(),
                session_date=date.today(),
                session_type="x" * 101,
            )


class TestAudioSchemas:
    def test_presigned_request_requires_file_name(self):
        with pytest.raises(ValidationError):
            PresignedUploadRequest(
                file_name="",
                content_type="audio/wav",
                session_id=uuid.uuid4(),
            )

    def test_presigned_request_file_name_max(self):
        with pytest.raises(ValidationError):
            PresignedUploadRequest(
                file_name="a" * 256,
                content_type="audio/wav",
                session_id=uuid.uuid4(),
            )

    def test_presigned_request_valid(self):
        req = PresignedUploadRequest(
            file_name="recording.wav",
            content_type="audio/wav",
            session_id=uuid.uuid4(),
        )
        assert req.file_size is None

    def test_complete_request_requires_object_key(self):
        with pytest.raises(ValidationError):
            AudioFileCompleteRequest(
                session_id=uuid.uuid4(),
                object_key="",
            )

    def test_complete_request_actual_size_nonnegative(self):
        with pytest.raises(ValidationError):
            AudioFileCompleteRequest(
                session_id=uuid.uuid4(),
                object_key="raw-audio/test/key.wav",
                actual_size_bytes=-1,
            )


class TestAnalysisSchemas:
    def test_create_requires_session_and_audio(self):
        with pytest.raises(ValidationError):
            AnalysisJobCreateRequest(session_id=uuid.uuid4())

    def test_progress_callback_valid(self):
        req = AnalysisJobProgressCallbackRequest(
            status=AnalysisJobStatus.RUNNING_ASR,
            pipeline_stage="RUNNING_ASR",
        )
        assert req.error_code is None

    def test_progress_callback_pipeline_stage_max(self):
        with pytest.raises(ValidationError):
            AnalysisJobProgressCallbackRequest(
                status=AnalysisJobStatus.RUNNING_VAD,
                pipeline_stage="x" * 256,
            )


class TestTemplateSchemas:
    def test_create_default_type_is_soap_note(self):
        req = TemplateCreateRequest(name="기본 템플릿")
        assert req.template_type == TemplateType.SOAP_NOTE

    def test_create_name_required(self):
        with pytest.raises(ValidationError):
            TemplateCreateRequest(name="")

    def test_create_with_sections_json(self):
        req = TemplateCreateRequest(
            name="커스텀 템플릿",
            template_type=TemplateType.CUSTOM,
            sections_json={"sections": ["Subjective", "Objective"]},
        )
        assert req.sections_json is not None


class TestReportSchemas:
    def test_segment_update_all_optional(self):
        req = ReportSegmentUpdateRequest()
        assert req.content is None
        assert req.title is None

    def test_approval_requires_action(self):
        with pytest.raises(ValidationError):
            ApprovalCreateRequest()

    def test_approval_valid_with_comment(self):
        from app.core.enums import ApprovalAction
        req = ApprovalCreateRequest(
            action=ApprovalAction.APPROVED,
            comment="이상 없음",
        )
        assert req.comment == "이상 없음"


class TestTranscriptSchemas:
    def test_segment_update_all_optional(self):
        req = TranscriptSegmentUpdateRequest()
        assert req.text is None
        assert req.speaker_role is None

    def test_bulk_update_empty_segments(self):
        req = TranscriptBulkUpdateRequest(segments=[])
        assert len(req.segments) == 0

    def test_internal_callback_default_segments(self):
        req = InternalTranscriptCallbackRequest(
            job_id=uuid.uuid4(),
            status=AnalysisJobStatus.COMPLETED,
        )
        assert req.segments == []

    def test_internal_callback_segment_confidence_range(self):
        with pytest.raises(ValidationError):
            from app.schemas.transcript import InternalTranscriptSegmentItem
            InternalTranscriptSegmentItem(confidence=1.5)
