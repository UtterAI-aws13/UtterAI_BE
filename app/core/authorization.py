"""Object-level authorization helpers shared across services.

Report/session/patient ownership checks were previously duplicated ad-hoc in
each service (e.g. ``ReportService._get_accessible_session``,
``PatientService._get_accessible``). This module centralizes the same
ADMIN-bypass / SLP-owns-resource rule so new endpoints — starting with the
insight map's Graph API — don't reimplement it, and IDOR checks stay
consistent even when a resource is reached through a different path
(report_draft_id, patient_ref_id, case_index_id).
"""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session as DbSession

from app.core.enums import SessionStatus, UserRole
from app.models.entities import PatientRef, Report, Session as SessionEntity, SoapCaseIndex
from app.schemas.auth import UserRead


def ensure_session_access(db: DbSession, session_id: uuid.UUID, current_user: UserRead) -> SessionEntity:
    session = db.get(SessionEntity, session_id)
    if session is None or session.status == SessionStatus.DELETED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
    if current_user.role == UserRole.ADMIN:
        return session
    if current_user.role == UserRole.SLP and session.slp_id == current_user.id:
        return session
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")


def ensure_report_access(db: DbSession, report_id: uuid.UUID, current_user: UserRead) -> Report:
    report = db.get(Report, report_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")
    ensure_session_access(db, report.session_id, current_user)
    return report


def ensure_patient_ref_access(db: DbSession, patient_ref_id: uuid.UUID, current_user: UserRead) -> PatientRef:
    ref = db.get(PatientRef, patient_ref_id)
    if ref is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found.")
    if current_user.role == UserRole.ADMIN:
        return ref
    if ref.current_slp_id == current_user.id:
        return ref
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")


def ensure_case_index_access(db: DbSession, case_index_id: uuid.UUID, current_user: UserRead) -> SoapCaseIndex:
    case_index = db.get(SoapCaseIndex, case_index_id)
    if case_index is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case index not found.")
    if current_user.role == UserRole.ADMIN:
        return case_index
    if case_index.therapist_id == current_user.id:
        return case_index
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")