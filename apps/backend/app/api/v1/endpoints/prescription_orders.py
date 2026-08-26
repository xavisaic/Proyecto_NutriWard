import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies import CurrentSession, DatabaseSession, require_roles, require_roles_with_csrf
from app.schemas.prescription_order import (
    FormulaCatalogCreate,
    FormulaCatalogRead,
    PrescriptionAction,
    PrescriptionClone,
    PrescriptionOrderCreate,
    PrescriptionOrderRead,
    PrescriptionOrderUpdate,
    PrescriptionSettingsRead,
    PrescriptionSettingsUpdate,
    PrescriptionSuspension,
    PrescriptionWorkspaceRead,
)
from app.services.prescription_order_service import (
    activate_order,
    clone_order,
    create_formula,
    create_order,
    suspend_order,
    update_order,
    update_settings,
    validate_order,
    workspace,
)


router = APIRouter(tags=["nutrition prescription orders"])
CLINICAL_ROLES = ("nutricionista", "jefatura")
ClinicalReader = Annotated[CurrentSession, Depends(require_roles(*CLINICAL_ROLES))]
ClinicalEditor = Annotated[CurrentSession, Depends(require_roles_with_csrf(*CLINICAL_ROLES))]
CatalogEditor = Annotated[CurrentSession, Depends(require_roles_with_csrf("administrador", "jefatura"))]


@router.get("/admissions/{admission_id}/nutrition-prescription-workspace", response_model=PrescriptionWorkspaceRead)
def get_workspace(admission_id: uuid.UUID, current: ClinicalReader, session: DatabaseSession) -> PrescriptionWorkspaceRead:
    return workspace(session, admission_id, current.user.id, current.roles)


@router.post("/admissions/{admission_id}/nutrition-prescription-orders", response_model=PrescriptionOrderRead, status_code=status.HTTP_201_CREATED)
def post_order(admission_id: uuid.UUID, payload: PrescriptionOrderCreate, current: ClinicalEditor, session: DatabaseSession) -> PrescriptionOrderRead:
    return create_order(session, admission_id, payload, current.user.id)


@router.patch("/nutrition-prescription-orders/{order_id}", response_model=PrescriptionOrderRead)
def patch_order(order_id: uuid.UUID, payload: PrescriptionOrderUpdate, current: ClinicalEditor, session: DatabaseSession) -> PrescriptionOrderRead:
    return update_order(session, order_id, payload, current.user.id, current.roles)


@router.post("/nutrition-prescription-orders/{order_id}/validate", response_model=PrescriptionOrderRead)
def post_validate(order_id: uuid.UUID, payload: PrescriptionAction, current: ClinicalEditor, session: DatabaseSession) -> PrescriptionOrderRead:
    return validate_order(session, order_id, payload, current.user.id, current.roles)


@router.post("/nutrition-prescription-orders/{order_id}/activate", response_model=PrescriptionOrderRead)
def post_activate(order_id: uuid.UUID, payload: PrescriptionAction, current: ClinicalEditor, session: DatabaseSession) -> PrescriptionOrderRead:
    return activate_order(session, order_id, payload, current.user.id)


@router.post("/nutrition-prescription-orders/{order_id}/suspend", response_model=PrescriptionOrderRead)
def post_suspend(order_id: uuid.UUID, payload: PrescriptionSuspension, current: ClinicalEditor, session: DatabaseSession) -> PrescriptionOrderRead:
    return suspend_order(session, order_id, payload, current.user.id)


@router.post("/nutrition-prescription-orders/{order_id}/clone", response_model=PrescriptionOrderRead, status_code=status.HTTP_201_CREATED)
def post_clone(order_id: uuid.UUID, payload: PrescriptionClone, current: ClinicalEditor, session: DatabaseSession) -> PrescriptionOrderRead:
    return clone_order(session, order_id, payload, current.user.id)


@router.post("/enteral-formula-catalog", response_model=FormulaCatalogRead, status_code=status.HTTP_201_CREATED)
def post_formula(payload: FormulaCatalogCreate, current: CatalogEditor, session: DatabaseSession) -> FormulaCatalogRead:
    return create_formula(session, payload, current.user.id)


@router.put("/nutrition-prescription-settings", response_model=PrescriptionSettingsRead)
def put_settings(payload: PrescriptionSettingsUpdate, current: CatalogEditor, session: DatabaseSession) -> PrescriptionSettingsRead:
    return update_settings(session, payload, current.user.id)
