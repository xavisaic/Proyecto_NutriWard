import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import CurrentSession, DatabaseSession, require_roles, require_roles_with_csrf
from app.schemas.nutrition import (
    CancellationCreate,
    CorrectionCreate,
    LabBulkImportCreate,
    LabBulkImportRead,
    LabClassificationUpdate,
    LabTrendResponse,
    LaboratoryTestCatalogRead,
    NutritionCatalogs,
    NutritionEncounterCreate,
    NutritionEncounterList,
    NutritionEncounterPatch,
    NutritionEncounterRead,
    NutritionLatest,
    NutritionProjectionList,
    VersionedAction,
)
from app.services.nutrition_service import (
    cancel_encounter,
    catalogs,
    correct_encounter,
    create_encounter,
    finalize_encounter,
    get_encounter_authorized,
    import_laboratory_results,
    classify_laboratory_observation,
    laboratory_test_catalog,
    laboratory_trends,
    latest_nutrition,
    list_encounters,
    projection,
    update_encounter,
)

router = APIRouter(tags=["nutritional clinical record"])
CLINICAL_ROLES = ("nutricionista", "jefatura")
ClinicalReader = Annotated[CurrentSession, Depends(require_roles(*CLINICAL_ROLES))]
ClinicalEditor = Annotated[CurrentSession, Depends(require_roles_with_csrf(*CLINICAL_ROLES))]


@router.get(
    "/admissions/{admission_id}/nutrition-care-encounters",
    response_model=NutritionEncounterList,
    summary="List nutritional care encounters for one hospitalization",
)
def read_encounters(
    admission_id: uuid.UUID,
    current: ClinicalReader,
    session: DatabaseSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> NutritionEncounterList:
    return list_encounters(
        session, admission_id, page, page_size, current.user.id, current.roles
    )


@router.post(
    "/admissions/{admission_id}/nutrition-care-encounters",
    response_model=NutritionEncounterRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create an explicit nutritional care draft",
)
def add_encounter(
    admission_id: uuid.UUID,
    payload: NutritionEncounterCreate,
    current: ClinicalEditor,
    session: DatabaseSession,
) -> NutritionEncounterRead:
    return create_encounter(session, admission_id, payload, current.user.id)


@router.get(
    "/nutrition-care-encounters/{encounter_id}",
    response_model=NutritionEncounterRead,
    summary="Read one structured nutritional care encounter",
)
def read_encounter(
    encounter_id: uuid.UUID,
    current: ClinicalReader,
    session: DatabaseSession,
) -> NutritionEncounterRead:
    return get_encounter_authorized(
        session, encounter_id, current.user.id, current.roles
    )


@router.patch(
    "/nutrition-care-encounters/{encounter_id}",
    response_model=NutritionEncounterRead,
    summary="Update an editable draft using optimistic concurrency",
)
def patch_encounter(
    encounter_id: uuid.UUID,
    payload: NutritionEncounterPatch,
    current: ClinicalEditor,
    session: DatabaseSession,
) -> NutritionEncounterRead:
    return update_encounter(session, encounter_id, payload, current.user.id, current.roles)


@router.post(
    "/nutrition-care-encounters/{encounter_id}/finalize",
    response_model=NutritionEncounterRead,
    summary="Validate and finalize an immutable nutritional encounter",
)
def finalize(
    encounter_id: uuid.UUID,
    payload: VersionedAction,
    current: ClinicalEditor,
    session: DatabaseSession,
) -> NutritionEncounterRead:
    return finalize_encounter(session, encounter_id, payload, current.user.id, current.roles)


@router.post(
    "/nutrition-care-encounters/{encounter_id}/correct",
    response_model=NutritionEncounterRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a linked corrective draft without overwriting the original",
)
def correct(
    encounter_id: uuid.UUID,
    payload: CorrectionCreate,
    current: ClinicalEditor,
    session: DatabaseSession,
) -> NutritionEncounterRead:
    return correct_encounter(session, encounter_id, payload, current.user.id)


@router.post(
    "/nutrition-care-encounters/{encounter_id}/cancel",
    response_model=NutritionEncounterRead,
    summary="Cancel a draft while preserving its traceability",
)
def cancel(
    encounter_id: uuid.UUID,
    payload: CancellationCreate,
    current: ClinicalEditor,
    session: DatabaseSession,
) -> NutritionEncounterRead:
    return cancel_encounter(session, encounter_id, payload, current.user.id, current.roles)


@router.get(
    "/admissions/{admission_id}/nutrition-latest",
    response_model=NutritionLatest,
    summary="Read the latest finalized clinical nutrition projection",
)
def read_latest(
    admission_id: uuid.UUID,
    _: ClinicalReader,
    session: DatabaseSession,
) -> NutritionLatest:
    return latest_nutrition(session, admission_id)


def _projection(
    kind: str,
    admission_id: uuid.UUID,
    session: DatabaseSession,
    page: int,
    page_size: int,
) -> NutritionProjectionList:
    return projection(session, admission_id, kind, page, page_size)


@router.get("/admissions/{admission_id}/nutrition-assessments", response_model=NutritionProjectionList)
def read_assessments(admission_id: uuid.UUID, _: ClinicalReader, session: DatabaseSession, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)) -> NutritionProjectionList:
    return _projection("assessments", admission_id, session, page, page_size)


@router.get("/admissions/{admission_id}/nutrition-anthropometry", response_model=NutritionProjectionList)
def read_anthropometry(admission_id: uuid.UUID, _: ClinicalReader, session: DatabaseSession, page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=100)) -> NutritionProjectionList:
    return _projection("anthropometry", admission_id, session, page, page_size)


@router.get("/admissions/{admission_id}/nutrition-screenings", response_model=NutritionProjectionList)
def read_screenings(admission_id: uuid.UUID, _: ClinicalReader, session: DatabaseSession, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)) -> NutritionProjectionList:
    return _projection("screenings", admission_id, session, page, page_size)


@router.get("/admissions/{admission_id}/nutrition-prescriptions", response_model=NutritionProjectionList)
def read_prescriptions(admission_id: uuid.UUID, _: ClinicalReader, session: DatabaseSession, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)) -> NutritionProjectionList:
    return _projection("prescriptions", admission_id, session, page, page_size)


@router.get("/admissions/{admission_id}/nutrition-intake", response_model=NutritionProjectionList)
def read_intake(admission_id: uuid.UUID, _: ClinicalReader, session: DatabaseSession, page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=100)) -> NutritionProjectionList:
    return _projection("intake", admission_id, session, page, page_size)


@router.get("/admissions/{admission_id}/nutrition-labs", response_model=NutritionProjectionList)
def read_labs(admission_id: uuid.UUID, _: ClinicalReader, session: DatabaseSession, page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=100)) -> NutritionProjectionList:
    return _projection("labs", admission_id, session, page, page_size)


@router.get(
    "/nutrition-lab-catalog",
    response_model=list[LaboratoryTestCatalogRead],
    summary="List canonical laboratory tests and learned aliases",
)
def read_lab_catalog(_: ClinicalReader, session: DatabaseSession) -> list[LaboratoryTestCatalogRead]:
    return laboratory_test_catalog(session)


@router.post(
    "/admissions/{admission_id}/nutrition-lab-imports",
    response_model=LabBulkImportRead,
    status_code=status.HTTP_201_CREATED,
    summary="Import and finalize a reviewed batch of laboratory results",
)
def add_lab_import(
    admission_id: uuid.UUID,
    payload: LabBulkImportCreate,
    current: ClinicalEditor,
    session: DatabaseSession,
) -> LabBulkImportRead:
    return import_laboratory_results(session, admission_id, payload, current.user.id)


@router.get(
    "/admissions/{admission_id}/nutrition-lab-trends",
    response_model=LabTrendResponse,
    summary="Read numeric laboratory series for charts",
)
def read_lab_trends(
    admission_id: uuid.UUID,
    _: ClinicalReader,
    session: DatabaseSession,
) -> LabTrendResponse:
    return laboratory_trends(session, admission_id)


@router.patch(
    "/nutrition-lab-observations/{observation_id}/classification",
    response_model=dict,
    summary="Classify a pending laboratory result without changing its source data",
)
def classify_lab_result(
    observation_id: uuid.UUID,
    payload: LabClassificationUpdate,
    current: ClinicalEditor,
    session: DatabaseSession,
) -> dict:
    return classify_laboratory_observation(
        session, observation_id, payload, current.user.id
    )


@router.get("/nutrition-catalogs", response_model=NutritionCatalogs)
def read_catalogs(_: ClinicalReader) -> NutritionCatalogs:
    return catalogs()
