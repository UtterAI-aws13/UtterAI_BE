"""Unit tests for SOAP case index concept tagging."""

import uuid
from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

from app.models.entities import OntologyConcept, Patient, Report, ReportSegment
from app.models.entities import Session as SessionEntity
from app.services.case_index_builder import _age_band, build_case_index


def _concept(concept_key: str, label: str, concept_type: str, language_area: str = "expressive_language") -> OntologyConcept:
    c = MagicMock(spec=OntologyConcept)
    c.id = uuid.uuid4()
    c.concept_key = concept_key
    c.label = label
    c.concept_type = concept_type
    c.language_area = language_area
    c.synonyms = []
    return c


def _segment(content: str) -> MagicMock:
    seg = MagicMock(spec=ReportSegment)
    seg.content = content
    seg.ai_content = None
    return seg


class TestAgeBand:
    def test_none_birth_date_returns_none(self):
        assert _age_band(None, date(2026, 1, 1)) is None

    def test_preschool_band(self):
        assert _age_band(date(2022, 1, 1), date(2026, 1, 1)) == "preschool"

    def test_adult_band(self):
        assert _age_band(date(1990, 1, 1), date(2026, 1, 1)) == "adult"


class TestBuildCaseIndex:
    def test_returns_none_when_no_text(self):
        db = MagicMock()
        report = MagicMock(spec=Report)
        session = MagicMock(spec=SessionEntity)
        result = build_case_index(db, report, session, [_segment(None)])
        assert result is None

    def test_returns_none_when_no_concepts_match(self):
        db = MagicMock()
        report = MagicMock(spec=Report)
        session = MagicMock(spec=SessionEntity)
        with patch("app.services.case_index_builder.InsightMapRepository") as MockRepo:
            MockRepo.return_value.list_concepts.return_value = [
                _concept("PCC", "자음정확도", "metric", "phonology")
            ]
            result = build_case_index(db, report, session, [_segment("전혀 관련 없는 문장입니다.")])
        assert result is None

    def test_tags_matched_concepts_and_builds_summary(self):
        db = MagicMock()
        report = MagicMock(spec=Report)
        report.id = uuid.uuid4()
        session = MagicMock(spec=SessionEntity)
        session.id = uuid.uuid4()
        session.patient_ref_id = uuid.uuid4()
        session.slp_id = uuid.uuid4()
        session.session_date = date(2026, 1, 1)

        short_utterance = _concept("short_utterance", "짧은 발화", "disorder")
        modeling = _concept("sentence_expansion_modeling", "문장 확장 모델링", "intervention")

        patient = MagicMock(spec=Patient)
        patient.birth_date = date(2022, 1, 1)

        with patch("app.services.case_index_builder.InsightMapRepository") as MockRepo, \
             patch("app.services.case_index_builder.PatientRepository") as MockPatientRepo:
            MockRepo.return_value.list_concepts.return_value = [short_utterance, modeling]
            MockRepo.return_value.get_case_index_by_report_id.return_value = None
            MockRepo.return_value.upsert_case_index.side_effect = lambda ci: ci
            MockPatientRepo.return_value.get_by_ref_id.return_value = patient

            result = build_case_index(
                db, report, session, [_segment("짧은 발화가 관찰되어 문장 확장 모델링을 적용함")]
            )

        assert result is not None
        assert "짧은 발화가 관찰됨" in result.summary
        assert "문장 확장 모델링 적용" in result.summary
        assert result.observed_issue == "짧은 발화"
        assert result.intervention == "문장 확장 모델링"
        assert result.age_band == "preschool"
        assert set(result.concept_ids) == {str(short_utterance.id), str(modeling.id)}
