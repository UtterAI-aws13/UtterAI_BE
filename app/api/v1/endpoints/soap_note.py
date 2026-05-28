"""SOAP note draft generation and basic read endpoints."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.db import get_db_session
from app.schemas.auth import UserRead
from app.schemas.soap_note import SoapNoteGenerateRequest, SoapNoteRead
from app.services.soap_note import SoapNoteService

router = APIRouter()


@router.post("/generate", response_model=SoapNoteRead, status_code=201)
def generate_soap_note(
    request: SoapNoteGenerateRequest,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> SoapNoteRead:
    """Generate and persist a SOAP draft for a confirmed transcript."""

    service = SoapNoteService(db)
    return service.generate(request, current_user)


@router.get("", response_model=list[SoapNoteRead])
def list_soap_notes(
    session_id: uuid.UUID | None = Query(default=None, alias="sessionId"),
    child_id: uuid.UUID | None = Query(default=None, alias="childId"),
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> list[SoapNoteRead]:
    """List visible SOAP notes with optional session/child filters."""

    service = SoapNoteService(db)
    return service.list(current_user, session_id, child_id)


@router.get("/{note_id}", response_model=SoapNoteRead)
def get_soap_note(
    note_id: uuid.UUID,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> SoapNoteRead:
    """Return one stored SOAP note."""

    service = SoapNoteService(db)
    return service.get(note_id, current_user)
