"""Schemas for the insight map Graph API."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class InsightMapNode(BaseModel):
    id: str
    type: str
    label: str
    source_layer: str
    summary: str | None = None
    data: dict = Field(default_factory=dict)


class InsightMapEdge(BaseModel):
    source: str
    target: str
    relation: str


class InsightMapResponse(BaseModel):
    nodes: list[InsightMapNode]
    edges: list[InsightMapEdge]


class InsightMapSearchRequest(BaseModel):
    query: str
    report_draft_id: uuid.UUID | None = None
    mode: list[str] = Field(default_factory=lambda: ["research", "current_patient", "my_soap"])


class SourceLinkResponse(BaseModel):
    url: str


class EvidenceItem(BaseModel):
    title: str
    content: str
    score: float
    doi_url: str | None = None


class EvidenceResponse(BaseModel):
    evidence: list[EvidenceItem]