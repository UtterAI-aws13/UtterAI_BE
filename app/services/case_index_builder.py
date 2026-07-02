"""Report(=SOAP note) 확정 시 soap_case_indexes를 생성/갱신한다.

원문은 저장하지 않는다 — report_segments 텍스트는 concept 태깅에만 임시로
쓰이고, DB에는 매칭된 concept_id와 라벨 기반의 짧은 요약 문장만 남는다.
관찰 소견/중재를 임의로 창작하지 않도록, 요약과 observed_issue/intervention은
ontology_concepts에 이미 정의된 라벨만 조합한다 (LLM 호출 없음).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session as DbSession

from app.models.entities import OntologyConcept, Patient, Report, ReportSegment, Session as SessionEntity, SoapCaseIndex
from app.repositories.insight_map import InsightMapRepository
from app.repositories.patient import PatientRepository


def _age_band(birth_date: date | None, on_date: date) -> str | None:
    if birth_date is None:
        return None
    age_months = (on_date.year - birth_date.year) * 12 + (on_date.month - birth_date.month)
    if age_months < 36:
        return "toddler"
    if age_months < 84:
        return "preschool"
    if age_months < 156:
        return "school_age"
    if age_months < 216:
        return "adolescent"
    return "adult"


def _match_concepts(text: str, concepts: list[OntologyConcept]) -> list[OntologyConcept]:
    text_lower = text.lower()
    matched = []
    for concept in concepts:
        candidates = [concept.concept_key, concept.label, *(concept.synonyms or [])]
        if any(c.lower() in text_lower for c in candidates if c):
            matched.append(concept)
    return matched


def build_case_index(
    db: DbSession,
    report: Report,
    session: SessionEntity,
    segments: list[ReportSegment],
) -> SoapCaseIndex | None:
    text = "\n".join(seg.content or seg.ai_content or "" for seg in segments)
    if not text.strip():
        return None

    insight_repo = InsightMapRepository(db)
    concepts = insight_repo.list_concepts()
    matched = _match_concepts(text, concepts)
    if not matched:
        return None

    metric_concept = next((c for c in matched if c.concept_type == "metric"), None)
    issue_concept = next((c for c in matched if c.concept_type == "disorder"), None)
    intervention_concept = next((c for c in matched if c.concept_type == "intervention"), None)
    language_area = next((c.language_area for c in matched if c.language_area), None)

    summary_parts = []
    if issue_concept is not None:
        summary_parts.append(f"{issue_concept.label}가 관찰됨")
    if intervention_concept is not None:
        summary_parts.append(f"{intervention_concept.label} 적용")
    if not summary_parts and metric_concept is not None:
        summary_parts.append(f"{metric_concept.label} 관련 소견 기록")
    summary = " / ".join(summary_parts) if summary_parts else "관련 개념이 태깅된 세션 기록"

    patient = PatientRepository(db).get_by_ref_id(session.patient_ref_id)
    age_band = _age_band(patient.birth_date, session.session_date) if patient else None

    now = datetime.now(timezone.utc)
    existing = insight_repo.get_case_index_by_report_id(report.id)
    case_index = existing or SoapCaseIndex(id=uuid.uuid4(), created_at=now)

    case_index.patient_ref_id = session.patient_ref_id
    case_index.session_id = session.id
    case_index.report_id = report.id
    case_index.therapist_id = session.slp_id
    case_index.language_area = language_area
    case_index.metric = metric_concept.concept_key if metric_concept else None
    case_index.observed_issue = issue_concept.label if issue_concept else None
    case_index.intervention = intervention_concept.label if intervention_concept else None
    case_index.age_band = age_band
    case_index.summary = summary
    case_index.concept_ids = [str(c.id) for c in matched]

    return insight_repo.upsert_case_index(case_index)