"""Service for the insight map: graph assembly, natural-language search, source links."""

from __future__ import annotations

import logging
import uuid

import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session as DbSession

from app.core.authorization import ensure_case_index_access, ensure_report_access
from app.core.config import get_settings
from app.models.entities import OntologyConcept
from app.repositories.insight_map import InsightMapRepository
from app.repositories.session import SessionRepository
from app.schemas.auth import UserRead
from app.schemas.insight_map import (
    EvidenceItem,
    EvidenceResponse,
    InsightMapEdge,
    InsightMapNode,
    InsightMapResponse,
    SourceLinkResponse,
)

settings = get_settings()
logger = logging.getLogger(__name__)

_DEFAULT_MODE = ["research", "current_patient", "my_soap"]


def _concept_node_id(concept: OntologyConcept) -> str:
    return f"concept_{concept.concept_key.lower()}"


class InsightMapService:
    def __init__(self, db: DbSession) -> None:
        self._db = db
        self._repo = InsightMapRepository(db)
        self._session_repo = SessionRepository(db)

    def get_insight_map(
        self,
        report_draft_id: uuid.UUID | None,
        mode: list[str],
        current_user: UserRead,
    ) -> InsightMapResponse:
        patient_ref_id: uuid.UUID | None = None
        if report_draft_id is not None:
            report = ensure_report_access(self._db, report_draft_id, current_user)
            session = self._session_repo.get_by_id(report.session_id)
            if session is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
            patient_ref_id = session.patient_ref_id
        else:
            # report_draft_id 없이 접근한 경우(사이드바에서 직접 진입) — 환자 히스토리(지표
            # 추이)는 특정 환자에 묶여 있어 노출할 수 없지만, 내 SOAP 기록은 담당 환자
            # 전체를 대상으로 둘러볼 수 있다.
            mode = [m for m in mode if m in ("research", "my_soap")]

        concepts = self._repo.list_concepts() if "research" in mode else []
        return self._build_graph(concepts, patient_ref_id, current_user, mode)

    def search(
        self,
        query: str,
        report_draft_id: uuid.UUID | None,
        mode: list[str],
        current_user: UserRead,
    ) -> InsightMapResponse:
        patient_ref_id: uuid.UUID | None = None
        if report_draft_id is not None:
            report = ensure_report_access(self._db, report_draft_id, current_user)
            session = self._session_repo.get_by_id(report.session_id)
            patient_ref_id = session.patient_ref_id if session else None

        resolved_keys = self._resolve_query(query)
        concepts = self._repo.find_concepts_by_key(resolved_keys) if resolved_keys else []
        if not concepts:
            # agent 응답이 비었거나 AI 서비스가 매칭되는 개념을 찾지 못한 경우,
            # 텍스트 포함 매칭으로 최소한의 결과를 보장한다.
            concepts = self._repo.search_concepts_by_term(query)

        # 1-hop 관련 개념도 함께 보여준다 (예: MLU 검색 시 short_utterance도 노출).
        if concepts:
            edges = self._repo.list_edges([c.id for c in concepts])
            related_ids = {e.source_concept_id for e in edges} | {e.target_concept_id for e in edges}
            related_ids -= {c.id for c in concepts}
            if related_ids:
                concepts = concepts + self._repo.list_concepts(list(related_ids))

        if patient_ref_id is None:
            # report_draft_id 없이 검색한 경우 환자 지표 추이는 노출할 수 없지만,
            # 내 SOAP 기록은 담당 환자 전체를 대상으로 검색할 수 있다.
            mode = [m for m in mode if m in ("research", "my_soap")]

        return self._build_graph(concepts, patient_ref_id, current_user, mode)

    def get_concept_evidence(self, concept_key: str, current_user: UserRead) -> EvidenceResponse:
        """개념 라벨+동의어로 문헌 근거를 검색한다. 로그인만 하면 누구나 조회 가능(환자 데이터 아님)."""
        del current_user  # 소유권 검증 불필요 — 온톨로지 개념은 환자 데이터가 아니다.
        concepts = self._repo.find_concepts_by_key([concept_key])
        if not concepts:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Concept not found.")
        concept = concepts[0]
        query = " ".join([concept.label, *concept.synonyms[:5]])
        return self._fetch_evidence(query)

    def get_source_link(self, case_index_id: uuid.UUID, current_user: UserRead) -> SourceLinkResponse:
        case_index = ensure_case_index_access(self._db, case_index_id, current_user)
        url = (
            f"/patients/{case_index.patient_ref_id}"
            f"/sessions/{case_index.session_id}"
            f"/soap-notes/{case_index.report_id}"
        )
        return SourceLinkResponse(url=url)

    # ── helpers ──────────────────────────────────────────────────────────────

    def _build_graph(
        self,
        concepts: list[OntologyConcept],
        patient_ref_id: uuid.UUID | None,
        current_user: UserRead,
        mode: list[str],
    ) -> InsightMapResponse:
        nodes: list[InsightMapNode] = []
        edges: list[InsightMapEdge] = []
        concept_by_id: dict[uuid.UUID, OntologyConcept] = {c.id: c for c in concepts}

        if "research" in mode and concepts:
            for concept in concepts:
                nodes.append(
                    InsightMapNode(
                        id=_concept_node_id(concept),
                        type=concept.concept_type,
                        label=concept.label,
                        source_layer="ontology",
                        summary=concept.description,
                    )
                )
            for edge in self._repo.list_edges([c.id for c in concepts]):
                source = concept_by_id.get(edge.source_concept_id)
                target = concept_by_id.get(edge.target_concept_id)
                if source is None or target is None:
                    continue
                edges.append(
                    InsightMapEdge(
                        source=_concept_node_id(source),
                        target=_concept_node_id(target),
                        relation=edge.relation_type,
                    )
                )

        if "current_patient" in mode and patient_ref_id is not None:
            for trend in self._repo.list_patient_metric_trends(patient_ref_id, current_user.id):
                node_id = f"trend_{trend.id}"
                nodes.append(
                    InsightMapNode(
                        id=node_id,
                        type="patient_metric_trend",
                        label=f"{trend.metric} 추이",
                        source_layer="current_patient",
                        data={"metric": trend.metric, "trend": trend.trend_json},
                    )
                )
                matching = next(
                    (c for c in concepts if c.concept_key.lower() == trend.metric.lower()), None
                )
                if matching is not None:
                    edges.append(
                        InsightMapEdge(source=_concept_node_id(matching), target=node_id, relation="observed_in")
                    )

        if "my_soap" in mode:
            concept_ids = [c.id for c in concepts] if concepts else None
            if patient_ref_id is not None:
                case_indexes = self._repo.list_case_indexes(patient_ref_id, current_user.id, concept_ids)
            else:
                # report_draft_id 없이 사이드바에서 직접 진입한 경우 — 담당 환자 전체의
                # SOAP 기록을 대상으로 한다. therapist_id는 항상 현재 사용자로 강제된다.
                case_indexes = self._repo.list_case_indexes_by_therapist(current_user.id, concept_ids)

            session_dates = self._repo.get_session_dates([ci.session_id for ci in case_indexes])

            for case_index in case_indexes:
                node_id = f"caseidx_{case_index.id}"
                session_date = session_dates.get(case_index.session_id)
                label = case_index.observed_issue or case_index.metric or "SOAP 기록"
                if session_date is not None:
                    label = f"{label} ({session_date.isoformat()})"
                nodes.append(
                    InsightMapNode(
                        id=node_id,
                        type="soap_case_index",
                        label=label,
                        source_layer="my_soap",
                        summary=case_index.summary,
                        data={
                            "session_id": str(case_index.session_id),
                            "report_id": str(case_index.report_id),
                            "session_date": session_date.isoformat() if session_date else None,
                        },
                    )
                )
                for concept_id in case_index.concept_ids or []:
                    matching = concept_by_id.get(uuid.UUID(str(concept_id)))
                    if matching is not None:
                        edges.append(
                            InsightMapEdge(
                                source=_concept_node_id(matching), target=node_id, relation="observed_in"
                            )
                        )

        return InsightMapResponse(nodes=nodes, edges=edges)

    _AI_SERVICE_MAX_ATTEMPTS = 2

    def _fetch_evidence(self, query: str) -> EvidenceResponse:
        url = f"{settings.ai_service_base_url}/ai/insight-map/evidence"
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(url, json={"query": query, "top_k": 3})
            resp.raise_for_status()
            data = resp.json()
            return EvidenceResponse(
                evidence=[EvidenceItem(**item) for item in data.get("evidence", [])]
            )
        except httpx.HTTPError as exc:
            logger.warning(f"[insight-map] 문헌 근거 조회 실패: {exc}")
            return EvidenceResponse(evidence=[])

    def _resolve_query(self, query: str) -> list[str]:
        """AI 서비스의 insight_query_resolver_agent를 호출해 concept_key 후보를 받는다.

        AI 서비스가 응답하지 않아도 검색 자체가 실패하면 안 되므로, 실패 시 빈 목록을
        반환하고 search()가 텍스트 포함 매칭으로 폴백한다.
        """
        url = f"{settings.ai_service_base_url}/ai/insight-map/resolve-query"
        for attempt in range(1, self._AI_SERVICE_MAX_ATTEMPTS + 1):
            try:
                with httpx.Client(timeout=30.0) as client:
                    resp = client.post(url, json={"query": query})
                resp.raise_for_status()
                data = resp.json()
                return [
                    c["concept_id"].removeprefix("concept_")
                    for c in data.get("resolved_concepts", [])
                ]
            except httpx.HTTPStatusError as exc:
                logger.warning(f"[insight-map] AI 서비스 오류 응답: {exc.response.status_code}")
                return []
            except httpx.RequestError as exc:
                logger.warning(
                    f"[insight-map] AI 서비스 연결 실패 (attempt {attempt}/{self._AI_SERVICE_MAX_ATTEMPTS}): {exc}"
                )
        return []