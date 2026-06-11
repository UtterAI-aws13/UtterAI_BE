"""Unit tests for AnalysisJobService business logic."""

import uuid
from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.core.enums import (
    AnalysisJobStatus,
    AudioFileStatus,
    SessionStatus,
    UserRole,
    UserStatus,
)
from app.models.entities import AnalysisJob, AudioFile
from app.models.entities import Session as SessionEntity
from app.schemas.analysis import (
    AnalysisJobCreateRequest,
    AnalysisJobProgressCallbackRequest,
)
from app.schemas.auth import UserRead
from app.services.analysis import AnalysisJobService


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


def _make_session(slp_id: uuid.UUID, status: SessionStatus = SessionStatus.AUDIO_UPLOADED) -> MagicMock:
    s = MagicMock(spec=SessionEntity)
    s.id = uuid.uuid4()
    s.slp_id = slp_id
    s.status = status
    s.patient_ref_id = uuid.uuid4()
    s.session_date = date.today()
    return s


def _make_audio(session_id: uuid.UUID, status: AudioFileStatus = AudioFileStatus.UPLOADED) -> MagicMock:
    a = MagicMock(spec=AudioFile)
    a.id = uuid.uuid4()
    a.session_id = session_id
    a.status = status
    a.object_key = f"raw-audio/test/{uuid.uuid4()}.wav"
    return a


def _make_job(session_id: uuid.UUID, status: AnalysisJobStatus = AnalysisJobStatus.PENDING) -> MagicMock:
    j = MagicMock(spec=AnalysisJob)
    j.id = uuid.uuid4()
    j.session_id = session_id
    j.audio_file_id = uuid.uuid4()
    j.status = status
    j.pipeline_stage = None
    j.error_code = None
    j.error_message = None
    j.retry_count = 0
    j.started_at = None
    j.completed_at = None
    j.created_at = datetime.now()
    return j


@pytest.fixture
def db():
    return MagicMock()


@pytest.fixture
def service(db):
    with patch("app.services.analysis.AnalysisJobRepository") as MockJob, \
         patch("app.services.analysis.AudioFileRepository") as MockAudio, \
         patch("app.services.analysis.SessionRepository") as MockSession, \
         patch("app.services.analysis.TemplateRepository") as MockTemplate, \
         patch("app.services.analysis.SQSClient") as MockSQS:
        svc = AnalysisJobService(db)
        svc.analysis_repository = MockJob.return_value
        svc.audio_repository = MockAudio.return_value
        svc.session_repository = MockSession.return_value
        svc.template_repository = MockTemplate.return_value
        svc.sqs_client = MockSQS.return_value
        svc.sqs_client.send_analysis_job.return_value = None
        yield svc


class TestAnalysisJobServiceCreate:
    def test_raises_400_if_audio_not_uploaded(self, service):
        user = _make_user()
        session = _make_session(user.id)
        audio = _make_audio(session.id, AudioFileStatus.PENDING_UPLOAD)

        service.session_repository.get_by_id.return_value = session
        service.audio_repository.get_by_id.return_value = audio
        service.analysis_repository.find_active_for_session.return_value = None

        with pytest.raises(HTTPException) as exc:
            service.create(
                AnalysisJobCreateRequest(
                    session_id=session.id, audio_file_id=audio.id
                ),
                user,
            )
        assert exc.value.status_code == 400
        assert "uploaded" in exc.value.detail.lower()

    def test_raises_409_if_active_job_exists(self, service):
        user = _make_user()
        session = _make_session(user.id)
        audio = _make_audio(session.id, AudioFileStatus.UPLOADED)
        existing_job = _make_job(session.id, AnalysisJobStatus.RUNNING_ASR)

        service.session_repository.get_by_id.return_value = session
        service.audio_repository.get_by_id.return_value = audio
        service.analysis_repository.find_active_for_session.return_value = existing_job

        with pytest.raises(HTTPException) as exc:
            service.create(
                AnalysisJobCreateRequest(
                    session_id=session.id, audio_file_id=audio.id
                ),
                user,
            )
        assert exc.value.status_code == 409

    def test_raises_404_if_audio_belongs_to_different_session(self, service):
        user = _make_user()
        session = _make_session(user.id)
        audio = _make_audio(uuid.uuid4())  # different session_id

        service.session_repository.get_by_id.return_value = session
        service.audio_repository.get_by_id.return_value = audio
        service.analysis_repository.find_active_for_session.return_value = None

        with pytest.raises(HTTPException) as exc:
            service.create(
                AnalysisJobCreateRequest(
                    session_id=session.id, audio_file_id=audio.id
                ),
                user,
            )
        assert exc.value.status_code == 404

    def test_creates_pending_job_and_updates_session_status(self, service):
        user = _make_user()
        session = _make_session(user.id)
        audio = _make_audio(session.id, AudioFileStatus.UPLOADED)
        new_job = _make_job(session.id, AnalysisJobStatus.PENDING)

        service.session_repository.get_by_id.return_value = session
        service.audio_repository.get_by_id.return_value = audio
        service.analysis_repository.find_active_for_session.return_value = None
        service.analysis_repository.create.return_value = new_job
        service.session_repository.update.return_value = session

        service.create(
            AnalysisJobCreateRequest(session_id=session.id, audio_file_id=audio.id),
            user,
        )

        created_job = service.analysis_repository.create.call_args[0][0]
        assert created_job.status == AnalysisJobStatus.PENDING
        assert created_job.audio_file_id == audio.id
        assert session.status == SessionStatus.ANALYSIS_REQUESTED

    def test_raises_403_if_template_not_accessible(self, service):
        user = _make_user()
        session = _make_session(user.id)
        audio = _make_audio(session.id, AudioFileStatus.UPLOADED)
        template = MagicMock()
        template.is_system = False
        template.owner_id = uuid.uuid4()  # different owner

        service.session_repository.get_by_id.return_value = session
        service.audio_repository.get_by_id.return_value = audio
        service.analysis_repository.find_active_for_session.return_value = None
        service.template_repository.get_by_id.return_value = template

        with pytest.raises(HTTPException) as exc:
            service.create(
                AnalysisJobCreateRequest(
                    session_id=session.id,
                    audio_file_id=audio.id,
                    template_id=uuid.uuid4(),
                ),
                user,
            )
        assert exc.value.status_code == 403


class TestAnalysisJobServiceCancel:
    def test_cancels_pending_job(self, service):
        user = _make_user()
        session = _make_session(user.id)
        job = _make_job(session.id, AnalysisJobStatus.PENDING)

        service.analysis_repository.get_by_id.return_value = job
        service.session_repository.get_by_id.return_value = session
        service.analysis_repository.update.return_value = job

        service.cancel(job.id, user)

        assert job.status == AnalysisJobStatus.CANCELLED
        assert job.completed_at is not None

    @pytest.mark.parametrize("terminal_status", [
        AnalysisJobStatus.COMPLETED,
        AnalysisJobStatus.FAILED,
        AnalysisJobStatus.CANCELLED,
    ])
    def test_cannot_cancel_terminal_job(self, service, terminal_status):
        user = _make_user()
        session = _make_session(user.id)
        job = _make_job(session.id, terminal_status)

        service.analysis_repository.get_by_id.return_value = job
        service.session_repository.get_by_id.return_value = session

        with pytest.raises(HTTPException) as exc:
            service.cancel(job.id, user)
        assert exc.value.status_code == 400

    @pytest.mark.parametrize("non_cancellable_status", [
        AnalysisJobStatus.RUNNING_ASR,
        AnalysisJobStatus.RUNNING_VAD,
        AnalysisJobStatus.GENERATING_REPORT,
        AnalysisJobStatus.SAVING_RESULT,
    ])
    def test_cannot_cancel_in_progress_job(self, service, non_cancellable_status):
        user = _make_user()
        session = _make_session(user.id)
        job = _make_job(session.id, non_cancellable_status)

        service.analysis_repository.get_by_id.return_value = job
        service.session_repository.get_by_id.return_value = session

        with pytest.raises(HTTPException) as exc:
            service.cancel(job.id, user)
        assert exc.value.status_code == 400


class TestAnalysisJobServiceProgressUpdate:
    def test_rejects_update_on_completed_job(self, service):
        job = _make_job(uuid.uuid4(), AnalysisJobStatus.COMPLETED)
        service.analysis_repository.get_by_id.return_value = job

        with pytest.raises(HTTPException) as exc:
            service.update_progress(
                job.id,
                AnalysisJobProgressCallbackRequest(status=AnalysisJobStatus.RUNNING_ASR),
            )
        assert exc.value.status_code == 409

    def test_rejects_completed_status_via_progress_callback(self, service):
        job = _make_job(uuid.uuid4(), AnalysisJobStatus.RUNNING_ASR)
        service.analysis_repository.get_by_id.return_value = job

        with pytest.raises(HTTPException) as exc:
            service.update_progress(
                job.id,
                AnalysisJobProgressCallbackRequest(status=AnalysisJobStatus.COMPLETED),
            )
        assert exc.value.status_code == 400

    def test_updates_pipeline_stage(self, service):
        job = _make_job(uuid.uuid4(), AnalysisJobStatus.DOWNLOADING)
        service.analysis_repository.get_by_id.return_value = job
        service.analysis_repository.update.return_value = job
        service.session_repository.get_by_id.return_value = MagicMock(
            status=SessionStatus.ANALYSIS_PROCESSING
        )

        service.update_progress(
            job.id,
            AnalysisJobProgressCallbackRequest(
                status=AnalysisJobStatus.RUNNING_VAD,
                pipeline_stage="RUNNING_VAD",
            ),
        )
        assert job.status == AnalysisJobStatus.RUNNING_VAD
        assert job.pipeline_stage == "RUNNING_VAD"
