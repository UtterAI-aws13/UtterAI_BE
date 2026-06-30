"""Repository for report chat threads, messages, and patch proposals."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import (
    Report,
    ReportChatMessage,
    ReportChatThread,
    ReportDraftRevision,
    ReportPatchProposal,
    ReportSegment,
)
from app.core.enums import ReportChatThreadStatus, ReportPatchStatus


class ReportChatRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    # ── thread ──────────────────────────────────────────────────────────────

    def get_or_create_thread(
        self,
        report_id: uuid.UUID,
        session_id: uuid.UUID,
        patient_ref_id: uuid.UUID,
        therapist_id: uuid.UUID,
    ) -> ReportChatThread:
        stmt = select(ReportChatThread).where(
            ReportChatThread.report_id == report_id,
            ReportChatThread.therapist_id == therapist_id,
            ReportChatThread.status == ReportChatThreadStatus.ACTIVE,
        )
        thread = self._db.execute(stmt).scalar_one_or_none()
        if thread:
            return thread

        now = datetime.now(timezone.utc)
        thread = ReportChatThread(
            id=uuid.uuid4(),
            report_id=report_id,
            session_id=session_id,
            patient_ref_id=patient_ref_id,
            therapist_id=therapist_id,
            status=ReportChatThreadStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        self._db.add(thread)
        self._db.flush()
        return thread

    def get_thread_by_id(self, thread_id: uuid.UUID) -> ReportChatThread | None:
        return self._db.get(ReportChatThread, thread_id)

    def get_recent_messages(
        self, thread_id: uuid.UUID, limit: int = 10
    ) -> list[ReportChatMessage]:
        stmt = (
            select(ReportChatMessage)
            .where(ReportChatMessage.thread_id == thread_id)
            .order_by(ReportChatMessage.created_at.desc())
            .limit(limit)
        )
        rows = self._db.execute(stmt).scalars().all()
        return list(reversed(rows))

    # ── message ─────────────────────────────────────────────────────────────

    def save_user_message(
        self, thread_id: uuid.UUID, content: str
    ) -> ReportChatMessage:
        msg = ReportChatMessage(
            id=uuid.uuid4(),
            thread_id=thread_id,
            role="user",
            content=content,
            intent=None,
            tool_calls=[],
            created_at=datetime.now(timezone.utc),
        )
        self._db.add(msg)
        self._db.flush()
        return msg

    def save_assistant_message(
        self,
        thread_id: uuid.UUID,
        content: str,
        intent: dict | None,
    ) -> ReportChatMessage:
        msg = ReportChatMessage(
            id=uuid.uuid4(),
            thread_id=thread_id,
            role="assistant",
            content=content,
            intent=intent,
            tool_calls=[],
            created_at=datetime.now(timezone.utc),
        )
        self._db.add(msg)
        self._db.flush()
        return msg

    # ── patch proposal ───────────────────────────────────────────────────────

    def save_patch_proposal(
        self,
        thread_id: uuid.UUID,
        report_id: uuid.UUID,
        base_report_version: int,
        target_section: str,
        original_text: str,
        proposed_text: str,
        rationale: str | None,
        evidence_refs: list,
        created_by_message_id: uuid.UUID,
    ) -> ReportPatchProposal:
        proposal = ReportPatchProposal(
            id=uuid.uuid4(),
            thread_id=thread_id,
            report_id=report_id,
            base_report_version=base_report_version,
            target_section=target_section,
            original_text=original_text,
            proposed_text=proposed_text,
            rationale=rationale,
            evidence_refs=evidence_refs,
            status=ReportPatchStatus.PENDING,
            created_by_message_id=created_by_message_id,
            applied_at=None,
            created_at=datetime.now(timezone.utc),
        )
        self._db.add(proposal)
        self._db.flush()
        return proposal

    def get_patch_proposal(self, patch_id: uuid.UUID) -> ReportPatchProposal | None:
        return self._db.get(ReportPatchProposal, patch_id)

    def apply_patch(
        self,
        proposal: ReportPatchProposal,
        report: Report,
        segment: ReportSegment,
        approved_by: uuid.UUID,
    ) -> tuple[Report, ReportDraftRevision]:
        version_before = report.version

        segment.content = proposal.proposed_text
        segment.is_edited = True
        segment.edited_by = approved_by
        segment.edited_at = datetime.now(timezone.utc)

        report.version = version_before + 1
        report.updated_at = datetime.now(timezone.utc)

        proposal.status = ReportPatchStatus.APPLIED
        proposal.applied_at = datetime.now(timezone.utc)

        revision = ReportDraftRevision(
            id=uuid.uuid4(),
            report_id=report.id,
            patch_proposal_id=proposal.id,
            version_before=version_before,
            version_after=report.version,
            changed_sections=[proposal.target_section],
            approved_by=approved_by,
            created_at=datetime.now(timezone.utc),
        )
        self._db.add(revision)
        self._db.flush()
        return report, revision

    def reject_patch(self, proposal: ReportPatchProposal) -> None:
        proposal.status = ReportPatchStatus.REJECTED
        self._db.flush()