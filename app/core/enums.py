"""Domain enums shared by models, services, and validation rules."""

from enum import StrEnum


class UserRole(StrEnum):
    """Supported application roles from the architecture document."""

    ADMIN = "ADMIN"
    THERAPIST = "THERAPIST"
    GUARDIAN = "GUARDIAN"
    VIEWER = "VIEWER"


class UserStatus(StrEnum):
    """User lifecycle states. `INACTIVE` is used as soft delete/inactivation."""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class ChildStatus(StrEnum):
    """Child profile lifecycle states."""

    ACTIVE = "ACTIVE"
    DELETED = "DELETED"


class SessionStatus(StrEnum):
    """Session state machine values documented for upload and analysis flow."""

    CREATED = "CREATED"
    AUDIO_UPLOADING = "AUDIO_UPLOADING"
    AUDIO_UPLOADED = "AUDIO_UPLOADED"
    ANALYSIS_REQUESTED = "ANALYSIS_REQUESTED"
    ANALYSIS_PROCESSING = "ANALYSIS_PROCESSING"
    ANALYSIS_COMPLETED = "ANALYSIS_COMPLETED"
    REPORT_READY = "REPORT_READY"
    FAILED = "FAILED"
    DELETED = "DELETED"


class AudioFileStatus(StrEnum):
    """Audio file lifecycle states from presigned upload to soft delete."""

    PENDING = "PENDING"
    UPLOADED = "UPLOADED"
    DELETED = "DELETED"


class AnalysisJobStatus(StrEnum):
    """Analysis job lifecycle states aligned with the architecture document."""

    REQUESTED = "REQUESTED"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class SpeakerRole(StrEnum):
    """Speaker-role mapping values used in transcript views and editing."""

    CHILD = "CHILD"
    THERAPIST = "THERAPIST"
    UNKNOWN = "UNKNOWN"


class AccessGrantLevel(StrEnum):
    """Child sharing permission levels for guardians and viewers."""

    VIEW_RESULT = "VIEW_RESULT"
    VIEW_AND_DOWNLOAD = "VIEW_AND_DOWNLOAD"


class AccessGrantStatus(StrEnum):
    """Access grant lifecycle states."""

    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"


class SoapNoteStatus(StrEnum):
    """SOAP note lifecycle states from draft creation to final retention."""

    DRAFT = "DRAFT"
    SAVED = "SAVED"
    FINALIZED = "FINALIZED"
    DELETED = "DELETED"


class ReportStatus(StrEnum):
    """Report lifecycle states kept intentionally small for the MVP."""

    READY = "READY"
    REGENERATING = "REGENERATING"
    DELETED = "DELETED"
