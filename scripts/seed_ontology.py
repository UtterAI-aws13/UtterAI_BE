"""ontology_seed.yaml을 ontology_concepts/ontology_edges 테이블에 upsert한다.

concept_key 기준으로 존재하면 갱신, 없으면 생성한다 (idempotent).
edges는 concept_key 쌍 + relation_type 기준으로 존재 여부를 확인한다.

사용법:
    python scripts/seed_ontology.py
"""

from __future__ import annotations

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import yaml

# Running this file directly (`python scripts/seed_ontology.py`) puts scripts/
# on sys.path instead of the project root, so `app` is not importable without this.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.db import SessionLocal
from app.models.entities import OntologyConcept, OntologyEdge

_SEED_PATH = Path(__file__).parent / "ontology_seed.yaml"


def _load_seed() -> dict:
    with open(_SEED_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def seed_ontology() -> None:
    data = _load_seed()
    now = datetime.now(timezone.utc)

    with SessionLocal() as db:
        concept_id_by_key: dict[str, uuid.UUID] = {}

        for concept_key, fields in data["concepts"].items():
            existing = db.query(OntologyConcept).filter_by(concept_key=concept_key).one_or_none()
            if existing is None:
                existing = OntologyConcept(
                    id=uuid.uuid4(),
                    concept_key=concept_key,
                    created_at=now,
                )
                db.add(existing)
            existing.label = fields["label"]
            existing.synonyms = fields.get("synonyms", [])
            existing.language_area = fields.get("language_area")
            existing.concept_type = fields["concept_type"]
            existing.description = fields.get("description")
            concept_id_by_key[concept_key] = existing.id

        db.flush()

        for edge in data.get("edges", []):
            source_id = concept_id_by_key[edge["source"]]
            target_id = concept_id_by_key[edge["target"]]
            relation_type = edge["relation_type"]

            existing_edge = (
                db.query(OntologyEdge)
                .filter_by(source_concept_id=source_id, target_concept_id=target_id, relation_type=relation_type)
                .one_or_none()
            )
            if existing_edge is None:
                db.add(
                    OntologyEdge(
                        id=uuid.uuid4(),
                        source_concept_id=source_id,
                        target_concept_id=target_id,
                        relation_type=relation_type,
                        evidence_source_ids=edge.get("evidence_source_ids", []),
                        confidence=edge.get("confidence"),
                        created_at=now,
                    )
                )
            else:
                existing_edge.confidence = edge.get("confidence")
                existing_edge.evidence_source_ids = edge.get("evidence_source_ids", existing_edge.evidence_source_ids)

        db.commit()

    print(f"Seeded {len(data['concepts'])} concepts and {len(data.get('edges', []))} edges.")


if __name__ == "__main__":
    seed_ontology()