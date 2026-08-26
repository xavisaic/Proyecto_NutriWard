import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import (
    CurrentSession,
    DatabaseSession,
    require_roles,
    require_roles_with_csrf,
)
from app.schemas.treatment import (
    MedicationCatalogList,
    MedicationCatalogMatchRequest,
    MedicationCatalogMatchResponse,
    TreatmentBulkCreate,
    TreatmentBulkRead,
    TreatmentContextRead,
    TreatmentCreate,
    TreatmentImpactSummary,
    TreatmentRead,
    TreatmentReviewCreate,
    TreatmentReviewRead,
    TreatmentUpdate,
)
from app.services.medication_catalog_service import (
    list_medication_catalog,
    match_medication_lines,
)
from app.services.treatment_service import (
    create_treatment,
    create_treatment_review,
    create_treatments_bulk,
    get_treatment,
    read_treatment_context,
    treatment_impact_summary,
    update_treatment,
)

router = APIRouter(tags=["active treatments"])
CLINICAL_ROLES = ("nutricionista", "jefatura")
ClinicalReader = Annotated[CurrentSession, Depends(require_roles(*CLINICAL_ROLES))]
ClinicalEditor = Annotated[
    CurrentSession, Depends(require_roles_with_csrf(*CLINICAL_ROLES))
]


@router.get("/medication-catalog", response_model=MedicationCatalogList)
def get_medication_catalog(
    _: ClinicalReader,
    session: DatabaseSession,
    q: str | None = None,
    availability: Literal["all", "inpatient", "outpatient", "both"] = "all",
    limit: int = Query(default=25, ge=1, le=100),
) -> MedicationCatalogList:
    return list_medication_catalog(
        session,
        query=q,
        availability=availability,
        limit=limit,
    )


@router.post("/medication-catalog/match", response_model=MedicationCatalogMatchResponse)
def post_medication_catalog_match(
    payload: MedicationCatalogMatchRequest,
    _: ClinicalReader,
    session: DatabaseSession,
) -> MedicationCatalogMatchResponse:
    return match_medication_lines(session, payload.lines)


@router.get("/admissions/{admission_id}/treatments", response_model=TreatmentContextRead)
def get_treatments(
    admission_id: uuid.UUID, _: ClinicalReader, session: DatabaseSession
) -> TreatmentContextRead:
    return read_treatment_context(session, admission_id)


@router.post(
    "/admissions/{admission_id}/treatments",
    response_model=TreatmentRead,
    status_code=status.HTTP_201_CREATED,
)
def post_treatment(
    admission_id: uuid.UUID,
    payload: TreatmentCreate,
    current: ClinicalEditor,
    session: DatabaseSession,
) -> TreatmentRead:
    return create_treatment(session, admission_id, payload, current.user.id)


@router.post(
    "/admissions/{admission_id}/treatments/bulk",
    response_model=TreatmentBulkRead,
    status_code=status.HTTP_201_CREATED,
)
def post_treatments_bulk(
    admission_id: uuid.UUID,
    payload: TreatmentBulkCreate,
    current: ClinicalEditor,
    session: DatabaseSession,
) -> TreatmentBulkRead:
    return create_treatments_bulk(session, admission_id, payload, current.user.id)


@router.post(
    "/admissions/{admission_id}/treatments/review",
    response_model=TreatmentReviewRead,
    status_code=status.HTTP_201_CREATED,
)
def post_treatment_review(
    admission_id: uuid.UUID,
    payload: TreatmentReviewCreate,
    current: ClinicalEditor,
    session: DatabaseSession,
) -> TreatmentReviewRead:
    return create_treatment_review(session, admission_id, payload, current.user.id)


@router.get(
    "/admissions/{admission_id}/treatment-impact-summary",
    response_model=TreatmentImpactSummary,
)
def get_treatment_impact(
    admission_id: uuid.UUID, _: ClinicalReader, session: DatabaseSession
) -> TreatmentImpactSummary:
    return treatment_impact_summary(session, admission_id)


@router.get("/admission-treatments/{treatment_id}", response_model=TreatmentRead)
def read_treatment(
    treatment_id: uuid.UUID, _: ClinicalReader, session: DatabaseSession
) -> TreatmentRead:
    return get_treatment(session, treatment_id)


@router.patch("/admission-treatments/{treatment_id}", response_model=TreatmentRead)
def patch_treatment(
    treatment_id: uuid.UUID,
    payload: TreatmentUpdate,
    current: ClinicalEditor,
    session: DatabaseSession,
) -> TreatmentRead:
    return update_treatment(session, treatment_id, payload, current.user.id)
