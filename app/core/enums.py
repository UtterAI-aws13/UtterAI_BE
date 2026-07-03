"""Domain enums shared by models, services, and schemas."""

from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "ADMIN"
    SLP = "SLP"


class UserStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class PatientStatus(StrEnum):
    ACTIVE = "ACTIVE"
    DELETED = "DELETED"


class SessionStatus(StrEnum):
    CREATED = "CREATED"
    AUDIO_UPLOADING = "AUDIO_UPLOADING"
    AUDIO_UPLOADED = "AUDIO_UPLOADED"
    ANALYSIS_REQUESTED = "ANALYSIS_REQUESTED"
    ANALYSIS_PROCESSING = "ANALYSIS_PROCESSING"
    ANALYSIS_COMPLETED = "ANALYSIS_COMPLETED"
    REPORT_GENERATING = "REPORT_GENERATING"
    REPORT_READY = "REPORT_READY"
    FAILED = "FAILED"
    DELETED = "DELETED"


class AudioFileStatus(StrEnum):
    PENDING_UPLOAD = "PENDING_UPLOAD"
    UPLOADED = "UPLOADED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"
    DELETED = "DELETED"


class AnalysisJobStatus(StrEnum):
    PENDING = "PENDING"
    DOWNLOADING = "DOWNLOADING"
    PREPROCESSING = "PREPROCESSING"
    RUNNING_VAD = "RUNNING_VAD"
    RUNNING_DIARIZATION = "RUNNING_DIARIZATION"
    RUNNING_ASR = "RUNNING_ASR"
    ALIGNING = "ALIGNING"
    CALCULATING_METRICS = "CALCULATING_METRICS"
    RUNNING_RAG = "RUNNING_RAG"
    GENERATING_REPORT = "GENERATING_REPORT"
    SAVING_RESULT = "SAVING_RESULT"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"
    CANCELLED = "CANCELLED"


class TargetSpeaker(StrEnum):
    PATIENT = "PATIENT"
    SLP = "SLP"
    ALL = "ALL"


class SpeakerRole(StrEnum):
    PATIENT = "PATIENT"
    SLP = "SLP"
    GUARDIAN = "GUARDIAN"
    UNKNOWN = "UNKNOWN"


class TranscriptStatus(StrEnum):
    DRAFT = "DRAFT"
    EDITING = "EDITING"
    REVIEWED = "REVIEWED"
    FINALIZED = "FINALIZED"


class TemplateType(StrEnum):
    SOAP_NOTE = "SOAP_NOTE"
    CUSTOM = "CUSTOM"


class TemplateStatus(StrEnum):
    PENDING_UPLOAD = "PENDING_UPLOAD"
    ACTIVE = "ACTIVE"
    DELETED = "DELETED"


class ReportStatus(StrEnum):
    DRAFT = "DRAFT"
    REVIEWING = "REVIEWING"
    APPROVED = "APPROVED"
    FINALIZED = "FINALIZED"
    DELETED = "DELETED"


class ReportSegmentType(StrEnum):
    SUBJECTIVE = "SUBJECTIVE"
    OBJECTIVE = "OBJECTIVE"
    ASSESSMENT = "ASSESSMENT"
    PLAN = "PLAN"
    CUSTOM = "CUSTOM"


class ReportChatThreadStatus(StrEnum):
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"


class ReportPatchStatus(StrEnum):
    PENDING = "PENDING"
    APPLIED = "APPLIED"
    REJECTED = "REJECTED"


class ReportGenerationRunStatus(StrEnum):
    """report_generation_runs.status. plain VARCHAR 컬럼이라 pg ENUM으로 강제하지
    않고 애플리케이션 레벨에서만 검증한다 (5-Agent Graph가 값을 자주 갱신하므로
    ENUM 타입 변경 마이그레이션 비용을 피한다)."""
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    RESEARCHING = "RESEARCHING"
    WRITING = "WRITING"
    VALIDATING = "VALIDATING"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class ReportDraftStatus(StrEnum):
    """report_drafts.status. Agent는 DRAFT만 쓸 수 있고, 최종 확정은
    치료사가 기존 reports 워크플로에서 수행한다."""
    DRAFT = "DRAFT"


