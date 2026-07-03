"""ORM entities based on ERD.md / DB Schema.md architecture."""

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Enum, Float, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import (
    AnalysisJobStatus,
    AudioFileStatus,
    PatientStatus,
    ReportChatThreadStatus,
    ReportPatchStatus,
    ReportSegmentType,
    ReportStatus,
    SessionStatus,
    SpeakerRole,
    TargetSpeaker,
    TemplateStatus,
    TemplateType,
    TranscriptStatus,
    UserRole,
    UserStatus,
)
from app.models.base import Base, TimestampMixin


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), nullable=False)
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus, name="user_status"),
        nullable=False,
        default=UserStatus.ACTIVE,
        server_default=UserStatus.ACTIVE.value,
    )


class PatientRef(Base):
    """Cloud-to-on-prem patient reference pointer."""

    __tablename__ = "patient_refs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_by_slp_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    current_slp_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Patient(Base):
    """Cloud-side patient info. 1:1 with PatientRef."""

    __tablename__ = "patients"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_ref_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patient_refs.id", ondelete="RESTRICT"), nullable=False, unique=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(1), nullable=True)
    memo: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[PatientStatus] = mapped_column(
        Enum(PatientStatus, name="patient_status"),
        nullable=False,
        default=PatientStatus.ACTIVE,
        server_default=PatientStatus.ACTIVE.value,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Session(TimestampMixin, Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_ref_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patient_refs.id", ondelete="RESTRICT"), nullable=False
    )
    slp_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    session_date: Mapped[date] = mapped_column(Date, nullable=False)
    session_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    session_goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    memo: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus, name="session_status"),
        nullable=False,
        default=SessionStatus.CREATED,
        server_default=SessionStatus.CREATED.value,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AudioFile(Base):
    __tablename__ = "audio_files"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="RESTRICT"), nullable=False
    )
    created_by_slp_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    object_key: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    original_filename: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    actual_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    presigned_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[AudioFileStatus] = mapped_column(
        Enum(AudioFileStatus, name="audio_file_status"),
        nullable=False,
        default=AudioFileStatus.PENDING_UPLOAD,
        server_default=AudioFileStatus.PENDING_UPLOAD.value,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="RESTRICT"), nullable=False
    )
    audio_file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("audio_files.id", ondelete="RESTRICT"), nullable=False
    )
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("templates.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[AnalysisJobStatus] = mapped_column(
        Enum(AnalysisJobStatus, name="analysis_job_status"),
        nullable=False,
        default=AnalysisJobStatus.PENDING,
        server_default=AnalysisJobStatus.PENDING.value,
    )
    pipeline_stage: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class LanguageMetrics(Base):
    __tablename__ = "language_metrics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="RESTRICT"), nullable=False
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("analysis_jobs.id", ondelete="RESTRICT"), nullable=False
    )
    target_speaker: Mapped[TargetSpeaker] = mapped_column(
        Enum(TargetSpeaker, name="target_speaker"), nullable=False
    )
    total_utterances: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ntw: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ndw: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ttr: Mapped[float | None] = mapped_column(Float, nullable=True)
    mlu_morpheme: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_response_latency_sec: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_response_latency_sec: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Transcript(TimestampMixin, Base):
    __tablename__ = "transcripts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="RESTRICT"), nullable=False
    )
    audio_file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("audio_files.id", ondelete="RESTRICT"), nullable=False
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("analysis_jobs.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[TranscriptStatus] = mapped_column(
        Enum(TranscriptStatus, name="transcript_status"),
        nullable=False,
        default=TranscriptStatus.DRAFT,
        server_default=TranscriptStatus.DRAFT.value,
    )
    raw_draft_s3_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_s3_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    finalized_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transcript_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transcripts.id", ondelete="CASCADE"), nullable=False
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="RESTRICT"), nullable=False
    )
    segment_index: Mapped[int] = mapped_column(Integer, nullable=False)
    speaker_label: Mapped[str | None] = mapped_column(String(50), nullable=True)
    speaker_role: Mapped[SpeakerRole] = mapped_column(
        Enum(SpeakerRole, name="speaker_role"),
        nullable=False,
        default=SpeakerRole.UNKNOWN,
        server_default=SpeakerRole.UNKNOWN.value,
    )
    start_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    original_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_edited: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    edited_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Template(TimestampMixin, Base):
    __tablename__ = "templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    template_type: Mapped[TemplateType] = mapped_column(
        Enum(TemplateType, name="template_type"), nullable=False
    )
    sections_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    file_s3_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_original_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    use_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    status: Mapped[TemplateStatus] = mapped_column(
        Enum(TemplateStatus, name="template_status"),
        nullable=False,
        default=TemplateStatus.ACTIVE,
        server_default=TemplateStatus.ACTIVE.value,
    )


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="RESTRICT"), nullable=False
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("analysis_jobs.id", ondelete="RESTRICT"), nullable=False
    )
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("templates.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[ReportStatus] = mapped_column(
        Enum(ReportStatus, name="report_status"),
        nullable=False,
        default=ReportStatus.DRAFT,
        server_default="DRAFT",
    )
    model_used: Mapped[str | None] = mapped_column(String(255), nullable=True)
    clinical_flags: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    evidence_chunk_ids: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    requires_human_review: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    s3_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


class ReportSegment(Base):
    __tablename__ = "report_segments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("reports.id", ondelete="CASCADE"), nullable=False
    )
    segment_type: Mapped[ReportSegmentType] = mapped_column(
        Enum(ReportSegmentType, name="report_segment_type"), nullable=False
    )
    segment_index: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ai_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_edited: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    edited_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

class ReportChatThread(Base):
    __tablename__ = "report_chat_threads"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("reports.id", ondelete="RESTRICT"), nullable=False
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="RESTRICT"), nullable=False
    )
    patient_ref_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patient_refs.id", ondelete="RESTRICT"), nullable=False
    )
    therapist_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[ReportChatThreadStatus] = mapped_column(
        Enum(ReportChatThreadStatus, name="report_chat_thread_status"),
        nullable=False,
        default=ReportChatThreadStatus.ACTIVE,
        server_default=ReportChatThreadStatus.ACTIVE.value,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ReportChatMessage(Base):
    __tablename__ = "report_chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thread_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("report_chat_threads.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    intent: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    tool_calls: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ReportPatchProposal(Base):
    __tablename__ = "report_patch_proposals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thread_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("report_chat_threads.id", ondelete="RESTRICT"), nullable=False
    )
    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("reports.id", ondelete="RESTRICT"), nullable=False
    )
    base_report_version: Mapped[int] = mapped_column(Integer, nullable=False)
    target_section: Mapped[str] = mapped_column(String(20), nullable=False)
    original_text: Mapped[str] = mapped_column(Text, nullable=False)
    proposed_text: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_refs: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    status: Mapped[ReportPatchStatus] = mapped_column(
        Enum(ReportPatchStatus, name="report_patch_status"),
        nullable=False,
        default=ReportPatchStatus.PENDING,
        server_default=ReportPatchStatus.PENDING.value,
    )
    created_by_message_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("report_chat_messages.id", ondelete="SET NULL"), nullable=True
    )
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ReportDraftRevision(Base):
    __tablename__ = "report_draft_revisions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("reports.id", ondelete="RESTRICT"), nullable=False
    )
    patch_proposal_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("report_patch_proposals.id", ondelete="SET NULL"), nullable=True
    )
    version_before: Mapped[int] = mapped_column(Integer, nullable=False)
    version_after: Mapped[int] = mapped_column(Integer, nullable=False)
    changed_sections: Mapped[list] = mapped_column(JSONB, nullable=False)
    approved_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class OntologyConcept(Base):
    """근거 기반 임상 인사이트맵의 기준 지식 레이어(노드).

    논문/가이드에서 추출한 개념(MLU, TTR, expressive_language 등)을 저장한다.
    concept_type 예: metric, language_area, observed_issue, intervention.
    """

    __tablename__ = "ontology_concepts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    concept_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    synonyms: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    language_area: Mapped[str | None] = mapped_column(String(100), nullable=True)
    concept_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class OntologyEdge(Base):
    """개념 간 관계(엣지). relation_type 예: measures, belongs_to, related_to, related_intervention."""

    __tablename__ = "ontology_edges"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_concept_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ontology_concepts.id", ondelete="CASCADE"), nullable=False
    )
    target_concept_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ontology_concepts.id", ondelete="CASCADE"), nullable=False
    )
    relation_type: Mapped[str] = mapped_column(String(50), nullable=False)
    evidence_source_ids: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    confidence: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SoapCaseIndex(Base):
    """SOAP note(=Report) 원문에서 추출한 구조화 색인.

    원문은 저장하지 않는다 — report_id만 참조하고, 상세 조회는 별도 권한 검증 API를 거친다.
    """

    __tablename__ = "soap_case_indexes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_ref_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patient_refs.id", ondelete="RESTRICT"), nullable=False
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="RESTRICT"), nullable=False
    )
    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("reports.id", ondelete="RESTRICT"), nullable=False
    )
    therapist_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    language_area: Mapped[str | None] = mapped_column(String(100), nullable=True)
    metric: Mapped[str | None] = mapped_column(String(100), nullable=True)
    observed_issue: Mapped[str | None] = mapped_column(String(255), nullable=True)
    intervention: Mapped[str | None] = mapped_column(String(255), nullable=True)
    age_band: Mapped[str | None] = mapped_column(String(50), nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    concept_ids: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PatientMetricTrend(Base):
    """환자별 지표 추이 스냅샷. trend_json에 세션별 시계열 값을 저장한다."""

    __tablename__ = "patient_metric_trends"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_ref_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patient_refs.id", ondelete="RESTRICT"), nullable=False
    )
    therapist_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    metric: Mapped[str] = mapped_column(String(100), nullable=False)
    trend_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ReportGenerationRun(Base):
    """Strands Graph 기반 5-Agent 리포트 생성 1회 실행 기록.

    status는 pg ENUM이 아니라 plain VARCHAR다 — Graph 실행 중 자주 갱신되므로
    ENUM 타입 변경 마이그레이션 비용을 피한다. 값은 ReportGenerationRunStatus로
    애플리케이션 레벨에서 검증한다.
    """

    __tablename__ = "report_generation_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="RESTRICT"), nullable=False
    )
    patient_ref_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patient_refs.id", ondelete="RESTRICT"), nullable=False
    )
    therapist_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    status: Mapped[str] = mapped_column(String(32), nullable=False)
    current_node: Mapped[str | None] = mapped_column(String(64), nullable=True)
    agent_runtime: Mapped[str] = mapped_column(String(64), nullable=False, default="agentcore", server_default="agentcore")
    graph_version: Mapped[str] = mapped_column(String(64), nullable=False)

    context_agent_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    research_agent_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    critic_agent_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    report_agent_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    qa_agent_version: Mapped[str | None] = mapped_column(String(64), nullable=True)

    model_config_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    retry_budget_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    quality_scores_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    failure_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    failure_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ReportDraft(Base):
    """5-Agent Graph가 생성한 SOAP 리포트 초안.

    QA/deterministic validation을 모두 통과한 결과만 status='DRAFT'로 저장된다.
    Agent는 이 테이블을 최종 확정(FINALIZED)하지 않는다 — 치료사가 기존
    reports 워크플로에서 검토 후 확정한다. report_draft_revisions와는 무관하다
    (그쪽은 이미 확정된 reports 행의 수정 이력).
    """

    __tablename__ = "report_drafts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    generation_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("report_generation_runs.id", ondelete="RESTRICT"), nullable=False
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="RESTRICT"), nullable=False
    )
    patient_ref_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patient_refs.id", ondelete="RESTRICT"), nullable=False
    )
    therapist_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT", server_default="DRAFT")
    soap_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    reasoning_summary_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    claims_json: Mapped[list] = mapped_column(JSONB, nullable=False)
    evidence_trace_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    validation_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    quality_scores_json: Mapped[dict] = mapped_column(JSONB, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ReportGenerationEvent(Base):
    """report_generation_runs의 노드별 진행 이벤트. 민감 원문 없이 실행 상태만 기록한다."""

    __tablename__ = "report_generation_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("report_generation_runs.id", ondelete="CASCADE"), nullable=False
    )
    node_name: Mapped[str] = mapped_column(String(64), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    decision: Mapped[str | None] = mapped_column(String(64), nullable=True)
    retry_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    token_usage_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
