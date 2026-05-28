"""Service-layer logic for report generation, reads, and downloads."""

from __future__ import annotations

import re
import uuid

from fastapi import HTTPException, status

from app.core.enums import ReportStatus, SessionStatus, SoapNoteStatus, UserRole
from app.models.entities import Report, Session, SoapNote
from app.repositories.analysis_result import AnalysisResultRepository
from app.repositories.report import ReportRepository
from app.repositories.session import SessionRepository
from app.repositories.soap_note import SoapNoteRepository
from app.schemas.auth import UserRead
from app.schemas.report import ReportCreateRequest, ReportRead, ReportUpdateRequest


class ReportService:
    """Generate report content from finalized SOAP notes and analysis output."""

    def __init__(self, db) -> None:
        self.analysis_result_repository = AnalysisResultRepository(db)
        self.report_repository = ReportRepository(db)
        self.session_repository = SessionRepository(db)
        self.soap_note_repository = SoapNoteRepository(db)

    def generate(self, request: ReportCreateRequest, current_user: UserRead) -> ReportRead:
        """Generate a report after the transcript and SOAP workflow is complete.

        Reports are generated from the latest finalized SOAP note for the session
        plus the selected analysis result. That keeps the report aligned with the
        clinician-reviewed narrative instead of the raw STT output alone.
        """

        session = self._get_accessible_session(request.session_id, current_user)
        result = self.analysis_result_repository.get_result_by_id(request.result_id)
        if result is None or result.session_id != session.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis result not found for this session.",
            )

        soap_note = self._get_latest_finalized_soap_note(session.id)
        content = self._build_report_content(session, result.summary_json or {}, result.metrics_json or {}, soap_note)
        title = f"{session.session_date.isoformat()} {session.session_type or 'Session'} Report"

        report = Report(
            session_id=session.id,
            result_id=result.id,
            soap_note_id=soap_note.id,
            generated_by=current_user.id,
            title=title,
            template_type=request.template_type,
            content=content,
            memo="Generated from finalized SOAP note and the selected analysis result.",
        )
        stored_report = self.report_repository.create(report)

        if session.status != SessionStatus.REPORT_READY:
            session.status = SessionStatus.REPORT_READY
            self.session_repository.update(session)

        return ReportRead.model_validate(stored_report)

    def list(
        self,
        current_user: UserRead,
        session_id: uuid.UUID | None = None,
        child_id: uuid.UUID | None = None,
    ) -> list[ReportRead]:
        """List visible reports filtered by child when requested."""

        if session_id is not None:
            self._get_accessible_session(session_id, current_user)

        reports = self.report_repository.list_visible(current_user, session_id, child_id)
        return [ReportRead.model_validate(report) for report in reports]

    def get(self, report_id: uuid.UUID, current_user: UserRead) -> ReportRead:
        """Return one accessible report."""

        report = self._get_accessible_report(report_id, current_user)
        return ReportRead.model_validate(report)

    def update(
        self,
        report_id: uuid.UUID,
        request: ReportUpdateRequest,
        current_user: UserRead,
    ) -> ReportRead:
        """Apply manual edits to an accessible report.

        Manual editing lets the clinician refine generated language before the
        report is downloaded or shared. Deleted reports remain immutable.
        """

        report = self._get_accessible_report(report_id, current_user)
        update_data = request.model_dump(exclude_unset=True)
        for field_name, value in update_data.items():
            setattr(report, field_name, value)
        stored_report = self.report_repository.update(report)
        return ReportRead.model_validate(stored_report)

    def get_download_payload(self, report_id: uuid.UUID, current_user: UserRead) -> tuple[str, str]:
        """Return a filename and text payload for download responses.

        The MVP serves a text attachment directly from the database. This keeps
        the workflow complete before a dedicated PDF rendering pipeline exists.
        """

        report = self._get_accessible_report(report_id, current_user)
        return self._build_download_filename(report), report.content

    def _get_accessible_session(self, session_id: uuid.UUID, current_user: UserRead) -> Session:
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
            detail="You do not have access to this report.",
        )

    def _get_accessible_report(self, report_id: uuid.UUID, current_user: UserRead) -> Report:
        """Load one report and enforce the same session-based access rules."""

        report = self.report_repository.get_by_id(report_id)
        if report is None or report.status == ReportStatus.DELETED:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report not found.",
            )
        self._get_accessible_session(report.session_id, current_user)
        return report

    def _get_latest_finalized_soap_note(self, session_id: uuid.UUID) -> SoapNote:
        """Select the most recent finalized SOAP note as the report source."""

        note = self.soap_note_repository.get_latest_finalized_by_session(session_id)
        if note is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A finalized SOAP note is required before generating a report.",
            )
        return note

    def _build_report_content(
        self,
        session: Session,
        summary: dict,
        metrics: dict,
        soap_note: SoapNote,
    ) -> str:
        """Assemble a deterministic report body from reviewed source artifacts."""

        metric_keys = ", ".join(metrics.keys()) if metrics else "No structured metrics available."
        return "\n\n".join(
            [
                f"Title: {session.session_date.isoformat()} {session.session_type or 'Session'} Report",
                "Overview:\n"
                f"- Session date: {session.session_date.isoformat()}\n"
                f"- Session type: {session.session_type or 'Unspecified'}\n"
                f"- Summary utterances: {summary.get('totalUtterances', 'N/A')}\n"
                f"- Summary duration seconds: {summary.get('durationSeconds', 'N/A')}",
                f"Subjective:\n{soap_note.subjective or 'No subjective content provided.'}",
                f"Objective:\n{soap_note.objective or 'No objective content provided.'}",
                f"Assessment:\n{soap_note.assessment or 'No assessment content provided.'}",
                f"Plan:\n{soap_note.plan or 'No plan content provided.'}",
                f"Structured Metrics:\nAvailable keys: {metric_keys}",
            ]
        )

    def _build_download_filename(self, report: Report) -> str:
        """Create a filesystem-safe attachment name for the report download."""

        safe_title = re.sub(r"[^A-Za-z0-9._-]+", "_", report.title).strip("_")
        return f"{safe_title or 'report'}-{report.id}.txt"
