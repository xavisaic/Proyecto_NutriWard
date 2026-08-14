import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies import CurrentSession, DatabaseSession, require_roles, require_roles_with_csrf
from app.schemas.clinical_context import (
    AdmissionDiagnosisBulkCreate,
    AdmissionDiagnosisRead,
    ClinicalContextRead,
    ConditionStatusUpdate,
    DiagnosisStatusUpdate,
    PatientConditionBulkCreate,
    PatientConditionRead,
)
from app.services.clinical_context_service import (
    create_conditions,
    create_diagnoses,
    read_clinical_context,
    update_condition_status,
    update_diagnosis_status,
)

router = APIRouter(tags=["clinical diagnoses and history"])
CLINICAL_ROLES = ("nutricionista", "jefatura")
ClinicalReader = Annotated[CurrentSession, Depends(require_roles(*CLINICAL_ROLES))]
ClinicalEditor = Annotated[CurrentSession, Depends(require_roles_with_csrf(*CLINICAL_ROLES))]


@router.get("/admissions/{admission_id}/clinical-context", response_model=ClinicalContextRead)
def get_context(admission_id: uuid.UUID, _: ClinicalReader, session: DatabaseSession) -> ClinicalContextRead:
    return read_clinical_context(session, admission_id)


@router.post(
    "/patients/{patient_id}/conditions",
    response_model=list[PatientConditionRead],
    status_code=status.HTTP_201_CREATED,
)
def add_conditions(
    patient_id: uuid.UUID,
    payload: PatientConditionBulkCreate,
    current: ClinicalEditor,
    session: DatabaseSession,
) -> list[PatientConditionRead]:
    return create_conditions(session, patient_id, payload, current.user.id)


@router.post(
    "/admissions/{admission_id}/diagnoses",
    response_model=list[AdmissionDiagnosisRead],
    status_code=status.HTTP_201_CREATED,
)
def add_diagnoses(
    admission_id: uuid.UUID,
    payload: AdmissionDiagnosisBulkCreate,
    current: ClinicalEditor,
    session: DatabaseSession,
) -> list[AdmissionDiagnosisRead]:
    return create_diagnoses(session, admission_id, payload, current.user.id)


@router.patch("/patient-conditions/{condition_id}/status", response_model=PatientConditionRead)
def patch_condition(
    condition_id: uuid.UUID,
    payload: ConditionStatusUpdate,
    current: ClinicalEditor,
    session: DatabaseSession,
) -> PatientConditionRead:
    return update_condition_status(session, condition_id, payload, current.user.id)


@router.patch("/admission-diagnoses/{diagnosis_id}/status", response_model=AdmissionDiagnosisRead)
def patch_diagnosis(
    diagnosis_id: uuid.UUID,
    payload: DiagnosisStatusUpdate,
    current: ClinicalEditor,
    session: DatabaseSession,
) -> AdmissionDiagnosisRead:
    return update_diagnosis_status(session, diagnosis_id, payload, current.user.id)
