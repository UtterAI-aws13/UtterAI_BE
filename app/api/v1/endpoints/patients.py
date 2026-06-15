"""Patient CRUD endpoints."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.db import get_db_session
from app.schemas.auth import UserRead
from app.schemas.patient import PatientCreateRequest, PatientRead, PatientUpdateRequest
from app.services.patient import PatientService

router = APIRouter()


@router.post("/", response_model=PatientRead, status_code=201)
def create_patient(
    request: PatientCreateRequest,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> PatientRead:
    return PatientService(db).create(request, current_user)


@router.get("/", response_model=list[PatientRead])
def list_patients(
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> list[PatientRead]:
    return PatientService(db).list(current_user)


@router.get("/by-ref/{patient_ref_id}", response_model=PatientRead)
def get_patient_by_ref_id(
    patient_ref_id: uuid.UUID,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> PatientRead:
    return PatientService(db).get_by_ref_id(patient_ref_id, current_user)


@router.get("/{patient_id}", response_model=PatientRead)
def get_patient(
    patient_id: uuid.UUID,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> PatientRead:
    return PatientService(db).get(patient_id, current_user)


@router.patch("/{patient_id}", response_model=PatientRead)
def update_patient(
    patient_id: uuid.UUID,
    request: PatientUpdateRequest,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> PatientRead:
    return PatientService(db).update(patient_id, request, current_user)


@router.delete("/{patient_id}", response_model=PatientRead)
def delete_patient(
    patient_id: uuid.UUID,
    current_user: UserRead = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> PatientRead:
    return PatientService(db).delete(patient_id, current_user)