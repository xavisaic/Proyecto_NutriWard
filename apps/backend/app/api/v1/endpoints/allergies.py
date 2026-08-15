import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies import CurrentSession, DatabaseSession, require_roles, require_roles_with_csrf
from app.schemas.allergy import (
    AllergyContextRead,
    AllergyIntoleranceBulkCreate,
    AllergyIntoleranceRead,
    AllergyReactionCreate,
    AllergyReviewAssertionCreate,
    AllergyReviewAssertionRead,
    AllergyStatusUpdate,
    FoodSafetyAllergyProjection,
)
from app.services.allergy_service import (
    add_reaction,
    create_allergies,
    create_review_assertion,
    food_safety_projection,
    read_allergy_context,
    update_allergy_status,
)

router = APIRouter(tags=["allergies and intolerances"])
CLINICAL_ROLES = ("nutricionista", "jefatura")
ClinicalReader = Annotated[CurrentSession, Depends(require_roles(*CLINICAL_ROLES))]
ClinicalEditor = Annotated[CurrentSession, Depends(require_roles_with_csrf(*CLINICAL_ROLES))]
FoodSafetyReader = Annotated[
    CurrentSession,
    Depends(require_roles("nutricionista", "jefatura", "alimentacion")),
]


@router.get("/admissions/{admission_id}/allergy-intolerances", response_model=AllergyContextRead)
def get_allergies(
    admission_id: uuid.UUID, _: ClinicalReader, session: DatabaseSession
) -> AllergyContextRead:
    return read_allergy_context(session, admission_id)


@router.post(
    "/admissions/{admission_id}/allergy-intolerances",
    response_model=list[AllergyIntoleranceRead],
    status_code=status.HTTP_201_CREATED,
)
def add_allergies(
    admission_id: uuid.UUID,
    payload: AllergyIntoleranceBulkCreate,
    current: ClinicalEditor,
    session: DatabaseSession,
) -> list[AllergyIntoleranceRead]:
    return create_allergies(session, admission_id, payload, current.user.id)


@router.patch("/allergy-intolerances/{allergy_id}/status", response_model=AllergyIntoleranceRead)
def patch_allergy(
    allergy_id: uuid.UUID,
    payload: AllergyStatusUpdate,
    current: ClinicalEditor,
    session: DatabaseSession,
) -> AllergyIntoleranceRead:
    return update_allergy_status(session, allergy_id, payload, current.user.id)


@router.post("/allergy-intolerances/{allergy_id}/reactions", response_model=AllergyIntoleranceRead)
def post_reaction(
    allergy_id: uuid.UUID,
    payload: AllergyReactionCreate,
    current: ClinicalEditor,
    session: DatabaseSession,
) -> AllergyIntoleranceRead:
    return add_reaction(session, allergy_id, payload, current.user.id)


@router.post(
    "/admissions/{admission_id}/allergy-review-assertions",
    response_model=AllergyReviewAssertionRead,
    status_code=status.HTTP_201_CREATED,
)
def post_review_assertion(
    admission_id: uuid.UUID,
    payload: AllergyReviewAssertionCreate,
    current: ClinicalEditor,
    session: DatabaseSession,
) -> AllergyReviewAssertionRead:
    return create_review_assertion(session, admission_id, payload, current.user.id)


@router.get(
    "/admissions/{admission_id}/food-safety-allergies",
    response_model=FoodSafetyAllergyProjection,
)
def get_food_safety(
    admission_id: uuid.UUID, _: FoodSafetyReader, session: DatabaseSession
) -> FoodSafetyAllergyProjection:
    return food_safety_projection(session, admission_id)
