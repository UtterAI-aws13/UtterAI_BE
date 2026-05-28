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


class AccessGrantLevel(StrEnum):
    """Child sharing permission levels for guardians and viewers."""

    VIEW_RESULT = "VIEW_RESULT"
    VIEW_AND_DOWNLOAD = "VIEW_AND_DOWNLOAD"


class AccessGrantStatus(StrEnum):
    """Access grant lifecycle states."""

    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"
