"""Unit tests for AudioService business logic."""

import uuid
from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.core.enums import AudioFileStatus, SessionStatus, UserRole, UserStatus
from app.models.entities import AudioFile
from app.models.entities import Session as SessionEntity
from app.schemas.audio import AudioFileCompleteRequest, PresignedUploadRequest
from app.schemas.auth import UserRead
from app.services.audio import AudioService


def _make_user(role: UserRole = UserRole.THERAPIST) -> UserRead:
    return UserRead(
        id=uuid.uuid4(),
        email="slp@test.com",
        name="Test SLP",
        role=role,
        status=UserStatus.ACTIVE,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


def _make_session(slp_id: uuid.UUID, status: SessionStatus = SessionStatus.CREATED) -> MagicMock:
    s = MagicMock(spec=SessionEntity)
    s.id = uuid.uuid4()
    s.slp_id = slp_id
    s.status = status
    return s


def _make_audio(
    session_id: uuid.UUID,
    status: AudioFileStatus = AudioFileStatus.PENDING_UPLOAD,
    object_key: str = "raw-audio/test/test.wav",
    slp_id: uuid.UUID | None = None,
) -> MagicMock:
    a = MagicMock(spec=AudioFile)
    a.id = uuid.uuid4()
    a.session_id = session_id
    a.status = status
    a.object_key = object_key
    a.created_by_slp_id = slp_id or uuid.uuid4()
    a.original_filename = "test.wav"
    a.content_type = "audio/wav"
    a.actual_size_bytes = None
    a.presigned_expires_at = None
    a.uploaded_at = None
    a.created_at = datetime.now()
    return a


@pytest.fixture
def db():
    return MagicMock()


@pytest.fixture
def service(db):
    with patch("app.services.audio.AudioFileRepository") as MockAudio, \
         patch("app.services.audio.SessionRepository") as MockSession, \
         patch("app.services.audio.S3Client") as MockS3:
        svc = AudioService(db)
        svc.audio_repository = MockAudio.return_value
        svc.session_repository = MockSession.return_value
        svc.s3_client = MockS3.return_value
        yield svc


class TestAudioServiceCreatePresignedUpload:
    def test_raises_404_when_session_not_found(self, service):
        user = _make_user()
        service.session_repository.get_by_id.return_value = None

        with pytest.raises(HTTPException) as exc:
            service.create_presigned_upload(
                PresignedUploadRequest(
                    file_name="test.wav",
                    content_type="audio/wav",
                    session_id=uuid.uuid4(),
                ),
                user,
            )
        assert exc.value.status_code == 404

    def test_raises_403_when_session_belongs_to_other_slp(self, service):
        user = _make_user()
        session = _make_session(uuid.uuid4())  # different slp_id
        service.session_repository.get_by_id.return_value = session

        with pytest.raises(HTTPException) as exc:
            service.create_presigned_upload(
                PresignedUploadRequest(
                    file_name="test.wav",
                    content_type="audio/wav",
                    session_id=session.id,
                ),
                user,
            )
        assert exc.value.status_code == 403

    def test_transitions_session_to_audio_uploading(self, service):
        user = _make_user()
        session = _make_session(user.id, SessionStatus.CREATED)
        audio = _make_audio(session.id)

        service.session_repository.get_by_id.return_value = session
        service.audio_repository.create.return_value = audio
        service.s3_client.generate_upload_url.return_value = "https://s3.example.com/presigned"

        service.create_presigned_upload(
            PresignedUploadRequest(
                file_name="session.wav",
                content_type="audio/wav",
                session_id=session.id,
            ),
            user,
        )

        assert session.status == SessionStatus.AUDIO_UPLOADING

    def test_does_not_change_status_if_already_uploading(self, service):
        user = _make_user()
        session = _make_session(user.id, SessionStatus.AUDIO_UPLOADING)
        audio = _make_audio(session.id)

        service.session_repository.get_by_id.return_value = session
        service.audio_repository.create.return_value = audio
        service.s3_client.generate_upload_url.return_value = "https://s3.example.com/presigned"

        service.create_presigned_upload(
            PresignedUploadRequest(
                file_name="session2.wav",
                content_type="audio/wav",
                session_id=session.id,
            ),
            user,
        )

        service.session_repository.update.assert_not_called()

    def test_object_key_contains_slp_and_session_id(self, service):
        user = _make_user()
        session = _make_session(user.id, SessionStatus.CREATED)
        audio = _make_audio(session.id)

        service.session_repository.get_by_id.return_value = session
        service.audio_repository.create.return_value = audio
        service.s3_client.generate_upload_url.return_value = "https://s3.example.com/presigned"

        service.create_presigned_upload(
            PresignedUploadRequest(
                file_name="my file.wav",
                content_type="audio/wav",
                session_id=session.id,
            ),
            user,
        )

        created_audio = service.audio_repository.create.call_args[0][0]
        assert str(user.id) in created_audio.object_key
        assert str(session.id) in created_audio.object_key
        assert " " not in created_audio.object_key  # spaces sanitized


class TestAudioServiceCompleteUpload:
    def test_raises_404_when_object_key_not_found(self, service):
        user = _make_user()
        session = _make_session(user.id)
        service.session_repository.get_by_id.return_value = session
        service.audio_repository.get_by_object_key.return_value = None

        with pytest.raises(HTTPException) as exc:
            service.complete_upload(
                AudioFileCompleteRequest(
                    session_id=session.id,
                    object_key="raw-audio/missing.wav",
                ),
                user,
            )
        assert exc.value.status_code == 404

    def test_raises_400_when_object_not_in_s3(self, service):
        user = _make_user()
        session = _make_session(user.id)
        audio = _make_audio(session.id)

        service.session_repository.get_by_id.return_value = session
        service.audio_repository.get_by_object_key.return_value = audio
        service.s3_client.object_exists.return_value = False

        with pytest.raises(HTTPException) as exc:
            service.complete_upload(
                AudioFileCompleteRequest(
                    session_id=session.id,
                    object_key=audio.object_key,
                ),
                user,
            )
        assert exc.value.status_code == 400

    def test_raises_400_for_deleted_audio(self, service):
        user = _make_user()
        session = _make_session(user.id)
        audio = _make_audio(session.id, AudioFileStatus.DELETED)

        service.session_repository.get_by_id.return_value = session
        service.audio_repository.get_by_object_key.return_value = audio

        with pytest.raises(HTTPException) as exc:
            service.complete_upload(
                AudioFileCompleteRequest(
                    session_id=session.id,
                    object_key=audio.object_key,
                ),
                user,
            )
        assert exc.value.status_code == 400

    def test_marks_audio_uploaded_and_updates_session(self, service):
        user = _make_user()
        session = _make_session(user.id, SessionStatus.AUDIO_UPLOADING)
        audio = _make_audio(session.id, AudioFileStatus.PENDING_UPLOAD)

        service.session_repository.get_by_id.return_value = session
        service.audio_repository.get_by_object_key.return_value = audio
        service.s3_client.object_exists.return_value = True
        service.audio_repository.update.return_value = audio

        service.complete_upload(
            AudioFileCompleteRequest(
                session_id=session.id,
                object_key=audio.object_key,
                actual_size_bytes=1_048_576,
            ),
            user,
        )

        assert audio.status == AudioFileStatus.UPLOADED
        assert audio.actual_size_bytes == 1_048_576
        assert audio.uploaded_at is not None
        assert session.status == SessionStatus.AUDIO_UPLOADED


class TestAudioServiceDelete:
    def test_restores_session_to_created_when_no_more_audio(self, service):
        user = _make_user()
        session = _make_session(user.id, SessionStatus.AUDIO_UPLOADED)
        audio = _make_audio(session.id, AudioFileStatus.UPLOADED)

        service.audio_repository.get_by_id.return_value = audio
        service.session_repository.get_by_id.side_effect = [session, session]
        service.audio_repository.update.return_value = audio
        service.audio_repository.list_active_for_session.return_value = []

        service.delete_audio_file(audio.id, user)

        assert audio.status == AudioFileStatus.DELETED
        assert session.status == SessionStatus.CREATED

    def test_keeps_session_status_when_other_audio_remains(self, service):
        user = _make_user()
        session = _make_session(user.id, SessionStatus.AUDIO_UPLOADED)
        audio = _make_audio(session.id, AudioFileStatus.UPLOADED)
        other_audio = _make_audio(session.id, AudioFileStatus.UPLOADED)

        service.audio_repository.get_by_id.return_value = audio
        service.session_repository.get_by_id.return_value = session
        service.audio_repository.update.return_value = audio
        service.audio_repository.list_active_for_session.return_value = [other_audio]

        service.delete_audio_file(audio.id, user)

        assert audio.status == AudioFileStatus.DELETED
        assert session.status == SessionStatus.AUDIO_UPLOADED
