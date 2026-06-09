"""Import ORM models so Alembic can discover metadata reliably."""

from app.models.base import Base
from app.models.entities import (
    AnalysisJob,
    ApprovalHistory,
    AudioFile,
    LanguageMetrics,
    PatientRef,
    RefreshToken,
    Report,
    ReportSegment,
    Session,
    Template,
    Transcript,
    TranscriptSegment,
    User,
)

__all__ = [
    "AnalysisJob",
    "ApprovalHistory",
    "AudioFile",
    "Base",
    "LanguageMetrics",
    "PatientRef",
    "RefreshToken",
    "Report",
    "ReportSegment",
    "Session",
    "Template",
    "Transcript",
    "TranscriptSegment",
    "User",
]
