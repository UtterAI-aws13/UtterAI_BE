"""Schemas for analysis result read APIs."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AnalysisResultRead(BaseModel):
    """Public analysis result representation returned to clients."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID
    session_id: uuid.UUID
    summary_json: dict[str, Any] | None
    metrics_json: dict[str, Any] | None
    interpretation_text: str | None
    transcript_s3_key: str | None
    metrics_s3_key: str | None
    raw_result_s3_key: str | None
    report_s3_key: str | None
    created_at: datetime
    updated_at: datetime


class AnalysisMetricsRead(BaseModel):
    """Wrapper response for metrics-specific reads."""

    result_id: uuid.UUID
    session_id: uuid.UUID
    metrics: dict[str, Any] | None
