import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import (
    CurrentSession,
    DatabaseSession,
    require_roles,
    require_roles_with_csrf,
)
from app.schemas.patient import (
    ActiveAdmissionReconciliation,
    AdmissionCreate,
    AdmissionListResponse,
    AdmissionRead,
    AdmissionStatusUpdate,
    IdentityStatus,
    LocationAssignment,
    LocationRead,
    PatientCreate,
    PatientDetail,
    PatientIdentityUpdate,
    PatientListResponse,
    PatientReconcile,
    PotentialPatientMatchesResponse,
    UnidentifiedPatientCreate,
)
from app.services.patient_service import (
    assign_location,
    create_admission,
    create_patient,
    create_unidentified_patient,
    get_admission_detail,
    get_current_location,
    get_location_history,
    get_patient_detail,
    identify_patient,
    find_potential_patient_matches,
    list_active_admissions,
    list_patient_admissions,
    list_patients,
    reconcile_patient,
    resolve_active_admission_reconciliation,
    update_admission_status,
)

router = APIRouter(tags=["patients", "admissions"])
PATIENT_ROLES = ("administrador", "jefatura", "nutricionista")
PATIENT_MUTATION_ROLES = ("jefatura", "nutricionista")
PatientReader = Annotated[CurrentSession, Depends(require_roles(*PATIENT_ROLES))]
PatientEditor = Annotated[
    CurrentSession,
    Depends(require_roles_with_csrf(*PATIENT_MUTATION_ROLES)),
]
ReconciliationManager = Annotated[
    CurrentSession,
    Depends(require_roles_with_csrf("jefatura")),
]


@router.post("/patients", response_model=PatientDetail, status_code=status.HTTP_201_CREATED)
def add_patient(
    payload: PatientCreate,
    current: PatientEditor,
    session: DatabaseSession,
) -> PatientDetail:
    return create_patient(session, payload, current.user.id)


@router.post(
    "/patients/unidentified",
    response_model=PatientDetail,
    status_code=status.HTTP_201_CREATED,
)
def add_unidentified_patient(
    payload: UnidentifiedPatientCreate,
    current: PatientEditor,
    session: DatabaseSession,
) -> PatientDetail:
    return create_unidentified_patient(session, payload, current.user.id)


@router.get("/patients", response_model=PatientListResponse)
def read_patients(
    _: PatientReader,
    session: DatabaseSession,
    q: str | None = Query(default=None, max_length=160),
    identity_status: IdentityStatus | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PatientListResponse:
    return list_patients(
        session,
        query=q,
        identity_status=identity_status,
        page=page,
        page_size=page_size,
    )


@router.get("/patients/potential-matches", response_model=PotentialPatientMatchesResponse)
def read_potential_patient_matches(
    _: PatientReader,
    session: DatabaseSession,
    rut: str | None = Query(default=None, max_length=20),
    hospital_identifier: str | None = Query(default=None, max_length=80),
    given_names: str | None = Query(default=None, max_length=160),
    first_surname: str | None = Query(default=None, max_length=100),
) -> PotentialPatientMatchesResponse:
    return find_potential_patient_matches(
        session,
        rut=rut,
        hospital_identifier=hospital_identifier,
        given_names=given_names,
        first_surname=first_surname,
    )


@router.get("/patients/{patient_id}", response_model=PatientDetail)
def read_patient(
    patient_id: uuid.UUID,
    _: PatientReader,
    session: DatabaseSession,
) -> PatientDetail:
    return get_patient_detail(session, patient_id)


@router.patch("/patients/{patient_id}/identity", response_model=PatientDetail)
def update_patient_identity(
    patient_id: uuid.UUID,
    payload: PatientIdentityUpdate,
    current: PatientEditor,
    session: DatabaseSession,
) -> PatientDetail:
    return identify_patient(session, patient_id, payload, current.user.id)


@router.post("/patients/{patient_id}/reconcile", response_model=PatientDetail)
def reconcile_patient_record(
    patient_id: uuid.UUID,
    payload: PatientReconcile,
    current: PatientEditor,
    session: DatabaseSession,
) -> PatientDetail:
    return reconcile_patient(session, patient_id, payload, current.user.id)


@router.post(
    "/patients/{patient_id}/reconcile-active-conflict",
    response_model=PatientDetail,
)
def resolve_patient_active_admission_conflict(
    patient_id: uuid.UUID,
    payload: ActiveAdmissionReconciliation,
    current: ReconciliationManager,
    session: DatabaseSession,
) -> PatientDetail:
    return resolve_active_admission_reconciliation(
        session,
        patient_id,
        payload,
        current.user.id,
    )


@router.get("/patients/{patient_id}/admissions", response_model=AdmissionListResponse)
def read_patient_admissions(
    patient_id: uuid.UUID,
    _: PatientReader,
    session: DatabaseSession,
) -> AdmissionListResponse:
    return list_patient_admissions(session, patient_id)


@router.post("/admissions", response_model=AdmissionRead, status_code=status.HTTP_201_CREATED)
def add_admission(
    payload: AdmissionCreate,
    current: PatientEditor,
    session: DatabaseSession,
) -> AdmissionRead:
    return create_admission(session, payload, current.user.id)


@router.get("/admissions/active", response_model=AdmissionListResponse)
def read_active_admissions(
    _: PatientReader,
    session: DatabaseSession,
) -> AdmissionListResponse:
    return list_active_admissions(session)


@router.get("/admissions/{admission_id}", response_model=AdmissionRead)
def read_admission(
    admission_id: uuid.UUID,
    _: PatientReader,
    session: DatabaseSession,
) -> AdmissionRead:
    return get_admission_detail(session, admission_id)


@router.patch("/admissions/{admission_id}/status", response_model=AdmissionRead)
def change_admission_status(
    admission_id: uuid.UUID,
    payload: AdmissionStatusUpdate,
    current: PatientEditor,
    session: DatabaseSession,
) -> AdmissionRead:
    return update_admission_status(session, admission_id, payload, current.user.id)


@router.post(
    "/admissions/{admission_id}/location",
    response_model=LocationRead,
    status_code=status.HTTP_201_CREATED,
)
def change_admission_location(
    admission_id: uuid.UUID,
    payload: LocationAssignment,
    current: PatientEditor,
    session: DatabaseSession,
) -> LocationRead:
    return assign_location(session, admission_id, payload, current.user.id)


@router.get("/admissions/{admission_id}/location", response_model=LocationRead)
def read_current_location(
    admission_id: uuid.UUID,
    _: PatientReader,
    session: DatabaseSession,
) -> LocationRead:
    return get_current_location(session, admission_id)


@router.get("/admissions/{admission_id}/location-history", response_model=list[LocationRead])
def read_location_history(
    admission_id: uuid.UUID,
    _: PatientReader,
    session: DatabaseSession,
) -> list[LocationRead]:
    return get_location_history(session, admission_id)
