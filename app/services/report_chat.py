"""Service for report chat: authorization, AI call, persistence."""

from __future__ import annotations

import uuid

import httpx
from fastapi import HTTPException, status
from sqlalchemy.orm import Session as DbSession

from app.core.config import get_settings
from app.core.enums import ReportPatchStatus, ReportSegmentType, ReportStatus, UserRole
from app.models.entities import ReportPatchProposal, ReportSegment
from app.repositories.report import ReportRepository
from app.repositories.report_chat import ReportChatRepository
from app.repositories.session import SessionRepository
from app.schemas.auth import UserRead
from app.schemas.report_chat import (
    ChatMessageRequest,
    ChatMessageResponse,
    EvidenceItem,
    EvidenceResponse,
    PatchApplyResponse,
    PatchProposalRead,
    PatientEvidenceItem,
)

_SECTION_TYPE_MAP: dict[str, ReportSegmentType] = {
    "S": ReportSegmentType.SUBJECTIVE,
    "O": ReportSegmentType.OBJECTIVE,
    "A": ReportSegmentType.ASSESSMENT,
    "P": ReportSegmentType.PLAN,
}

settings = get_settings()


class ReportChatService:
    def __init__(self, db: DbSession) -> None:
        self._db = db
        self._report_repo = ReportRepository(db)
        self._session_repo = SessionRepository(db)
        self._chat_repo = ReportChatRepository(db)

    def send_message(
        self,
        report_id: uuid.UUID,
        request: ChatMessageRequest,
        current_user: UserRead,
    ) -> ChatMessageResponse:
        report = self._get_accessible_report(report_id, current_user)
        session = self._session_repo.get_by_id(report.session_id)

        thread = self._chat_repo.get_or_create_thread(
            report_id=report_id,
            session_id=report.session_id,
            patient_ref_id=session.patient_ref_id,
            therapist_id=current_user.id,
        )

        self._chat_repo.save_user_message(thread.id, request.message)
        self._db.flush()

        segments = self._report_repo.list_segments(report_id)
        history = self._chat_repo.get_recent_messages(thread.id, limit=10)

        ai_payload = {
            "report_id": str(report_id),
            "report_version": report.version,
            "message": request.message,
            "segments": [
                {
                    "section": seg.segment_type,
                    "title": seg.title,
                    "content": seg.content or seg.ai_content or "",
                }
                for seg in segments
            ],
            "history": [
                {"role": m.role, "content": m.content}
                for m in history[:-1]  # 마지막은 방금 저장한 user 메시지이므로 제외
            ],
        }

        ai_response = self._call_ai_service(ai_payload)

        intent = ai_response.get("intent")
        assistant_text = ai_response.get("assistant_message", "")
        patch_data = ai_response.get("patch_proposal")

        assistant_msg = self._chat_repo.save_assistant_message(
            thread_id=thread.id,
            content=assistant_text,
            intent=intent,
        )

        patch_read: PatchProposalRead | None = None
        if patch_data:
            proposal = self._chat_repo.save_patch_proposal(
                thread_id=thread.id,
                report_id=report_id,
                base_report_version=report.version,
                target_section=patch_data["target_section"],
                original_text=patch_data["original_text"],
                proposed_text=patch_data["proposed_text"],
                rationale=patch_data.get("rationale"),
                evidence_refs=patch_data.get("evidence_refs", []),
                created_by_message_id=assistant_msg.id,
            )
            patch_read = PatchProposalRead(
                patch_id=proposal.id,
                target_section=proposal.target_section,
                original_text=proposal.original_text,
                proposed_text=proposal.proposed_text,
                rationale=proposal.rationale,
                evidence_refs=proposal.evidence_refs,
                base_report_version=proposal.base_report_version,
                status=proposal.status,
            )

        self._db.commit()

        return ChatMessageResponse(
            thread_id=thread.id,
            assistant_message=assistant_text,
            intent=intent,
            patch_proposal=patch_read,
        )

    def apply_patch(
        self,
        patch_id: uuid.UUID,
        current_user: UserRead,
    ) -> PatchApplyResponse:
        proposal = self._chat_repo.get_patch_proposal(patch_id)
        if proposal is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patch proposal not found.")

        if proposal.status != ReportPatchStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Patch is already {proposal.status}.",
            )

        report = self._get_accessible_report(proposal.report_id, current_user)

        # 스레드 소유권 검증
        thread = self._chat_repo.get_thread_by_id(proposal.thread_id)
        if thread is None or thread.therapist_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

        # 낙관적 잠금: proposal 생성 시점 version과 현재 report version이 다르면 충돌
        if proposal.base_report_version != report.version:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Report has been modified since this proposal was created "
                    f"(expected version {proposal.base_report_version}, current {report.version}). "
                    "Please review the latest report and request again."
                ),
            )

        segment = self._find_segment_for_section(report.id, proposal.target_section)
        if segment is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Target section '{proposal.target_section}' not found in report.",
            )

        updated_report, _ = self._chat_repo.apply_patch(proposal, report, segment, current_user.id)
        self._db.commit()

        return PatchApplyResponse(
            report_id=updated_report.id,
            version=updated_report.version,
            updated_sections=[proposal.target_section],
        )

    def get_evidence(
        self,
        report_id: uuid.UUID,
        metric: str | None,
        current_user: UserRead,
    ) -> EvidenceResponse:
        report = self._get_accessible_report(report_id, current_user)

        lit_evidence: list[EvidenceItem] = []
        pat_evidence: list[PatientEvidenceItem] = []

        if report.evidence_chunk_ids:
            lit_evidence = [
                EvidenceItem(
                    title=None,
                    section=None,
                    summary=f"chunk_id={cid}" + (f" metric={metric}" if metric else ""),
                    source_id=str(cid),
                    page=None,
                )
                for cid in report.evidence_chunk_ids
                if metric is None or (isinstance(cid, str) and metric.lower() in cid.lower())
            ]

        return EvidenceResponse(
            literature_evidence=lit_evidence,
            patient_evidence=pat_evidence,
        )

    # ── helpers ──────────────────────────────────────────────────────────────

    def _get_accessible_report(self, report_id: uuid.UUID, current_user: UserRead):
        report = self._report_repo.get_by_id(report_id)
        if report is None or report.status == ReportStatus.DELETED:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")

        session = self._session_repo.get_by_id(report.session_id)
        if session is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

        if current_user.role != UserRole.ADMIN and session.slp_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

        return report

    def _find_segment_for_section(
        self, report_id: uuid.UUID, target_section: str
    ) -> ReportSegment | None:
        segments = self._report_repo.list_segments(report_id)
        segment_type = _SECTION_TYPE_MAP.get(target_section.upper())
        if segment_type is None:
            return None
        for seg in segments:
            if seg.segment_type == segment_type:
                return seg
        return None

    def _call_ai_service(self, payload: dict) -> dict:
        url = f"{settings.ai_service_base_url}/ai/report-chat"
        try:
            with httpx.Client(timeout=60.0) as client:
                resp = client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"AI service error: {exc.response.status_code}",
            ) from exc
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI service is unreachable.",
            ) from exc