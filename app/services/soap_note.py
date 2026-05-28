"""Service-layer logic for generating and reading SOAP notes."""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status

from app.core.enums import SessionStatus, UserRole
from app.models.entities import SoapNote
from app.repositories.analysis_result import AnalysisResultRepository
from app.repositories.session import SessionRepository
from app.repositories.soap_note import SoapNoteRepository
from app.schemas.auth import UserRead
from app.schemas.soap_note import SoapNoteGenerateRequest, SoapNoteRead


class SoapNoteService:
    """Generate draft SOAP notes from confirmed transcript and analysis data."""

    def __init__(self, db) -> None:
        self.analysis_result_repository = AnalysisResultRepository(db)
        self.session_repository = SessionRepository(db)
        self.soap_note_repository = SoapNoteRepository(db)

    def generate(self, request: SoapNoteGenerateRequest, current_user: UserRead) -> SoapNoteRead:
        """Generate and persist a first-pass SOAP draft."""

        session = self._get_accessible_session(request.session_id, current_user)
        result = self.analysis_result_repository.get_result_by_id(request.transcript_id)
        if result is None or result.session_id != session.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transcript/analysis result not found for this session.",
            )

        utterances = self.analysis_result_repository.list_utterances_by_session(session.id)
        if not utterances:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Transcript segments do not exist for this session.",
            )
        if not all(item.is_confirmed for item in utterances):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Transcript must be confirmed before generating a SOAP draft.",
            )

        transcript_text = " ".join(
            [item.edited_text or item.original_text or "" for item in utterances]
        ).strip()
        summary = result.summary_json or {}
        metrics = result.metrics_json or {}

        subjective = (
            "Transcript-based summary:\n"
            f"{transcript_text[:1200] if transcript_text else 'No transcript content available.'}"
        )
        objective = (
            "Observed session metrics:\n"
            f"- Total utterances: {summary.get('totalUtterances', 'N/A')}\n"
            f"- Child utterances: {summary.get('childUtterances', 'N/A')}\n"
            f"- Duration seconds: {summary.get('durationSeconds', 'N/A')}"
        )
        assessment = (
            "Preliminary assessment draft:\n"
            f"- Available metric keys: {', '.join(metrics.keys()) if metrics else 'No structured metrics available.'}"
        )
        plan = (
            "Draft plan:\n"
            "- Review transcript edits and analysis metrics.\n"
            "- Finalize clinician interpretation before sharing."
        )

        note = SoapNote(
            session_id=session.id,
            result_id=result.id,
            job_id=request.clinical_analysis_job_id,
            generated_by=current_user.id,
            subjective=subjective,
            objective=objective,
            assessment=assessment,
            plan=plan,
        )
        stored_note = self.soap_note_repository.create(note)
        return SoapNoteRead.model_validate(stored_note)

    def list(
        self,
        current_user: UserRead,
        session_id: uuid.UUID | None = None,
        child_id: uuid.UUID | None = None,
    ) -> list[SoapNoteRead]:
        """List visible SOAP notes for therapist/admin users."""

        if session_id is not None:
            self._get_accessible_session(session_id, current_user)

        notes = self.soap_note_repository.list_visible(current_user, session_id, child_id)
        return [SoapNoteRead.model_validate(note) for note in notes]

    def get(self, note_id: uuid.UUID, current_user: UserRead) -> SoapNoteRead:
        """Return one SOAP note after access checks."""

        note = self.soap_note_repository.get_by_id(note_id)
        if note is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="SOAP note not found.",
            )
        self._get_accessible_session(note.session_id, current_user)
        return SoapNoteRead.model_validate(note)

    def _get_accessible_session(self, session_id: uuid.UUID, current_user: UserRead):
        """Load a session and enforce therapist ownership or admin override."""

        session = self.session_repository.get_by_id(session_id)
        if session is None or session.status == SessionStatus.DELETED:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found.",
            )
        if current_user.role == UserRole.ADMIN:
            return session
        if current_user.role == UserRole.THERAPIST and session.therapist_id == current_user.id:
            return session
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this SOAP note.",
        )
