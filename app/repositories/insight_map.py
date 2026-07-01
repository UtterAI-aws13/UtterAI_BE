"""Database access helpers for the insight map (ontology + patient history + case index)."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.entities import OntologyConcept, OntologyEdge, PatientMetricTrend, SoapCaseIndex


class InsightMapRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_concepts(self, concept_ids: list[uuid.UUID] | None = None) -> list[OntologyConcept]:
        statement = select(OntologyConcept)
        if concept_ids is not None:
            statement = statement.where(OntologyConcept.id.in_(concept_ids))
        return list(self.db.execute(statement).scalars().all())

    def find_concepts_by_key(self, concept_keys: list[str]) -> list[OntologyConcept]:
        """concept_key 대소문자를 구분하지 않고 매칭한다.

        AI agent가 반환하는 concept_id(예: 'concept_mlu')는 소문자인 반면
        ontology_concepts.concept_key는 ontology.yaml 원본 표기(예: 'MLU')를
        그대로 쓰기 때문에, 대소문자를 무시하지 않으면 매칭이 항상 실패한다.
        """
        if not concept_keys:
            return []
        lowered = [k.lower() for k in concept_keys]
        statement = select(OntologyConcept).where(func.lower(OntologyConcept.concept_key).in_(lowered))
        return list(self.db.execute(statement).scalars().all())

    def search_concepts_by_term(self, term: str) -> list[OntologyConcept]:
        """concept_key/label/synonyms 중 term을 포함하는 concept을 찾는다 (대소문자 무시)."""
        term_lower = term.lower()
        matches = []
        for concept in self.list_concepts():
            haystack = [concept.concept_key.lower(), concept.label.lower()]
            haystack += [s.lower() for s in (concept.synonyms or [])]
            if any(term_lower in h or h in term_lower for h in haystack):
                matches.append(concept)
        return matches

    def list_edges(self, concept_ids: list[uuid.UUID] | None = None) -> list[OntologyEdge]:
        statement = select(OntologyEdge)
        if concept_ids is not None:
            statement = statement.where(
                OntologyEdge.source_concept_id.in_(concept_ids) | OntologyEdge.target_concept_id.in_(concept_ids)
            )
        return list(self.db.execute(statement).scalars().all())

    def list_patient_metric_trends(self, patient_ref_id: uuid.UUID, therapist_id: uuid.UUID) -> list[PatientMetricTrend]:
        statement = select(PatientMetricTrend).where(
            PatientMetricTrend.patient_ref_id == patient_ref_id,
            PatientMetricTrend.therapist_id == therapist_id,
        )
        return list(self.db.execute(statement).scalars().all())

    def get_case_index_by_report_id(self, report_id: uuid.UUID) -> SoapCaseIndex | None:
        statement = select(SoapCaseIndex).where(SoapCaseIndex.report_id == report_id)
        return self.db.execute(statement).scalar_one_or_none()

    def upsert_case_index(self, case_index: SoapCaseIndex) -> SoapCaseIndex:
        self.db.add(case_index)
        self.db.flush()
        return case_index

    def list_case_indexes(
        self,
        patient_ref_id: uuid.UUID,
        therapist_id: uuid.UUID,
        concept_ids: list[uuid.UUID] | None = None,
    ) -> list[SoapCaseIndex]:
        """내 SOAP 기록만 반환한다 — therapist_id는 항상 현재 사용자로 강제한다 (IDOR 방지)."""
        statement = select(SoapCaseIndex).where(
            SoapCaseIndex.patient_ref_id == patient_ref_id,
            SoapCaseIndex.therapist_id == therapist_id,
        )
        case_indexes = list(self.db.execute(statement).scalars().all())
        if concept_ids is None:
            return case_indexes
        concept_id_strs = {str(cid) for cid in concept_ids}
        return [ci for ci in case_indexes if concept_id_strs & {str(c) for c in (ci.concept_ids or [])}]