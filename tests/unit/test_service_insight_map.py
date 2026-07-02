"""Unit tests for InsightMapService."""

import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.core.enums import UserRole, UserStatus
from app.models.entities import OntologyConcept, OntologyEdge, Report, Session as SessionEntity, SoapCaseIndex
from app.schemas.auth import UserRead
from app.services.insight_map import InsightMapService


def _make_user() -> UserRead:
    return UserRead(
        id=uuid.uuid4(),
        email="slp@test.com",
        name="Test SLP",
        role=UserRole.SLP,
        status=UserStatus.ACTIVE,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


def _concept(concept_key: str, concept_type: str = "metric") -> MagicMock:
    c = MagicMock(spec=OntologyConcept)
    c.id = uuid.uuid4()
    c.concept_key = concept_key
    c.label = concept_key
    c.concept_type = concept_type
    c.language_area = "expressive_language"
    c.description = None
    c.synonyms = ["동의어"]
    return c


@pytest.fixture
def db():
    return MagicMock()


@pytest.fixture
def service(db):
    with patch("app.services.insight_map.InsightMapRepository") as MockRepo, \
         patch("app.services.insight_map.SessionRepository") as MockSession:
        svc = InsightMapService(db)
        svc._repo = MockRepo.return_value
        svc._session_repo = MockSession.return_value
        yield svc


class TestGetInsightMap:
    def test_research_mode_returns_concept_nodes_and_edges(self, service):
        user = _make_user()
        report = MagicMock(spec=Report)
        session = MagicMock(spec=SessionEntity)
        session.patient_ref_id = uuid.uuid4()

        mlu = _concept("MLU")
        short_utterance = _concept("short_utterance", "disorder")
        edge = MagicMock(spec=OntologyEdge)
        edge.source_concept_id = mlu.id
        edge.target_concept_id = short_utterance.id
        edge.relation_type = "related_to"

        service._repo.list_concepts.return_value = [mlu, short_utterance]
        service._repo.list_edges.return_value = [edge]
        service._repo.list_patient_metric_trends.return_value = []
        service._repo.list_case_indexes.return_value = []
        service._session_repo.get_by_id.return_value = session

        with patch("app.services.insight_map.ensure_report_access", return_value=report):
            result = service.get_insight_map(uuid.uuid4(), ["research"], user)

        node_ids = {n.id for n in result.nodes}
        assert node_ids == {"concept_mlu", "concept_short_utterance"}
        assert result.edges[0].source == "concept_mlu"
        assert result.edges[0].target == "concept_short_utterance"
        assert result.edges[0].relation == "related_to"

    def test_my_soap_mode_only_queries_current_user_case_indexes(self, service):
        user = _make_user()
        report = MagicMock(spec=Report)
        session = MagicMock(spec=SessionEntity)
        session.patient_ref_id = uuid.uuid4()

        service._repo.list_concepts.return_value = []
        service._repo.list_patient_metric_trends.return_value = []
        service._repo.list_case_indexes.return_value = []
        service._session_repo.get_by_id.return_value = session

        with patch("app.services.insight_map.ensure_report_access", return_value=report):
            service.get_insight_map(uuid.uuid4(), ["my_soap"], user)

        service._repo.list_case_indexes.assert_called_once_with(session.patient_ref_id, user.id, None)

    def test_without_report_draft_id_drops_current_patient_but_keeps_my_soap(self, service):
        user = _make_user()
        mlu = _concept("MLU")
        service._repo.list_concepts.return_value = [mlu]
        service._repo.list_edges.return_value = []
        service._repo.list_case_indexes_by_therapist.return_value = []
        service._repo.get_session_dates.return_value = {}

        result = service.get_insight_map(None, ["research", "current_patient", "my_soap"], user)

        service._session_repo.get_by_id.assert_not_called()
        service._repo.list_case_indexes.assert_not_called()
        service._repo.list_patient_metric_trends.assert_not_called()
        service._repo.list_case_indexes_by_therapist.assert_called_once_with(user.id, [mlu.id])
        assert {n.id for n in result.nodes} == {"concept_mlu"}

    def test_without_report_draft_id_my_soap_lists_all_patients_for_therapist(self, service):
        user = _make_user()
        case_index = MagicMock(spec=SoapCaseIndex)
        case_index.id = uuid.uuid4()
        case_index.session_id = uuid.uuid4()
        case_index.report_id = uuid.uuid4()
        case_index.observed_issue = "짧은 발화"
        case_index.metric = None
        case_index.summary = "요약"
        case_index.concept_ids = []

        service._repo.list_concepts.return_value = []
        service._repo.list_case_indexes_by_therapist.return_value = [case_index]
        service._repo.get_session_dates.return_value = {}

        result = service.get_insight_map(None, ["my_soap"], user)

        service._repo.list_case_indexes_by_therapist.assert_called_once_with(user.id, None)
        assert len(result.nodes) == 1
        assert result.nodes[0].label == "짧은 발화"


class TestSearch:
    def test_falls_back_to_term_match_when_resolver_returns_nothing(self, service):
        user = _make_user()
        mlu = _concept("MLU")
        service._repo.list_edges.return_value = []
        service._repo.search_concepts_by_term.return_value = [mlu]
        service._repo.find_concepts_by_key.return_value = []

        with patch.object(service, "_resolve_query", return_value=[]):
            result = service.search("낮은 MLU", None, ["research"], user)

        service._repo.search_concepts_by_term.assert_called_once_with("낮은 MLU")
        assert {n.id for n in result.nodes} == {"concept_mlu"}

    def test_uses_resolved_concepts_when_available(self, service):
        user = _make_user()
        mlu = _concept("MLU")
        service._repo.find_concepts_by_key.return_value = [mlu]
        service._repo.list_edges.return_value = []

        with patch.object(service, "_resolve_query", return_value=["mlu"]):
            result = service.search("낮은 MLU", None, ["research"], user)

        service._repo.find_concepts_by_key.assert_called_once_with(["mlu"])
        assert {n.id for n in result.nodes} == {"concept_mlu"}

    def test_without_report_draft_id_drops_current_patient_but_keeps_my_soap(self, service):
        user = _make_user()
        service._repo.find_concepts_by_key.return_value = []
        service._repo.search_concepts_by_term.return_value = []
        service._repo.list_case_indexes_by_therapist.return_value = []
        service._repo.get_session_dates.return_value = {}

        with patch.object(service, "_resolve_query", return_value=[]):
            service.search("아무개념", None, ["research", "current_patient", "my_soap"], user)

        service._repo.list_case_indexes.assert_not_called()
        service._repo.list_patient_metric_trends.assert_not_called()
        service._repo.list_case_indexes_by_therapist.assert_called_once_with(user.id, None)


class TestGetConceptEvidence:
    def test_404_when_concept_not_found(self, service):
        user = _make_user()
        service._repo.find_concepts_by_key.return_value = []

        with pytest.raises(HTTPException) as exc:
            service.get_concept_evidence("unknown", user)
        assert exc.value.status_code == 404

    def test_fetches_evidence_using_concept_label_and_synonyms(self, service):
        user = _make_user()
        mlu = _concept("MLU")
        mlu.synonyms = ["평균 발화 길이", "MLU-w"]
        service._repo.find_concepts_by_key.return_value = [mlu]

        with patch.object(service, "_fetch_evidence") as mock_fetch:
            service.get_concept_evidence("MLU", user)

        mock_fetch.assert_called_once_with("MLU 평균 발화 길이 MLU-w")

    def test_returns_empty_evidence_when_ai_service_unreachable(self, service):
        import httpx

        with patch("app.services.insight_map.httpx.Client") as MockClient:
            MockClient.return_value.__enter__.return_value.post.side_effect = httpx.ConnectError("refused")
            result = service._fetch_evidence("MLU")

        assert result.evidence == []


class TestGetSourceLink:
    def test_builds_url_from_case_index(self, service):
        user = _make_user()
        case_index = MagicMock(spec=SoapCaseIndex)
        case_index.patient_ref_id = uuid.uuid4()
        case_index.session_id = uuid.uuid4()
        case_index.report_id = uuid.uuid4()

        with patch("app.services.insight_map.ensure_case_index_access", return_value=case_index):
            result = service.get_source_link(uuid.uuid4(), user)

        assert result.url == (
            f"/patients/{case_index.patient_ref_id}"
            f"/sessions/{case_index.session_id}"
            f"/soap-notes/{case_index.report_id}"
        )
