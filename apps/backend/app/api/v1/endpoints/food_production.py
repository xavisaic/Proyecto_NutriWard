import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.dependencies import CurrentSession, DatabaseSession, require_roles, require_roles_with_csrf
from app.schemas.food_production import (
    FoodCatalogItemCreate,
    FoodCatalogItemRead,
    FoodCatalogItemUpdate,
    MealPlanCreate,
    MealPlanFinalize,
    MealPlanRead,
    MealPlanUpdate,
    ProductionConsolidatedRead,
)
from app.services.food_production_service import (
    cancel_meal_plan,
    create_catalog_item,
    create_meal_plan,
    current_meal_plan,
    finalize_meal_plan,
    list_catalog,
    production_consolidated,
    production_xlsx,
    read_meal_plan,
    update_catalog_item,
    update_meal_plan,
)


router = APIRouter(tags=["meal plans and food production"])
ClinicalReader = Annotated[
    CurrentSession, Depends(require_roles("nutricionista", "jefatura"))
]
ClinicalEditor = Annotated[
    CurrentSession, Depends(require_roles_with_csrf("nutricionista", "jefatura"))
]
CatalogReader = Annotated[
    CurrentSession, Depends(require_roles("nutricionista", "jefatura", "alimentacion"))
]
CatalogManager = Annotated[
    CurrentSession, Depends(require_roles_with_csrf("jefatura"))
]
ProductionReader = Annotated[
    CurrentSession, Depends(require_roles("jefatura", "alimentacion"))
]


@router.get("/food-regimen-catalog", response_model=list[FoodCatalogItemRead])
def get_catalog(
    _: CatalogReader,
    session: DatabaseSession,
    search: str | None = Query(default=None, max_length=100),
    include_inactive: bool = False,
) -> list[FoodCatalogItemRead]:
    return list_catalog(session, search=search, include_inactive=include_inactive)


@router.post(
    "/food-regimen-catalog",
    response_model=FoodCatalogItemRead,
    status_code=status.HTTP_201_CREATED,
)
def post_catalog_item(
    payload: FoodCatalogItemCreate,
    current: CatalogManager,
    session: DatabaseSession,
) -> FoodCatalogItemRead:
    return create_catalog_item(session, payload, current.user.id)


@router.patch("/food-regimen-catalog/{item_id}", response_model=FoodCatalogItemRead)
def patch_catalog_item(
    item_id: uuid.UUID,
    payload: FoodCatalogItemUpdate,
    current: CatalogManager,
    session: DatabaseSession,
) -> FoodCatalogItemRead:
    return update_catalog_item(session, item_id, payload, current.user.id)


@router.get("/admissions/{admission_id}/meal-plans/current", response_model=MealPlanRead | None)
def get_current_plan(
    admission_id: uuid.UUID,
    _: ClinicalReader,
    session: DatabaseSession,
    service_date: date | None = None,
) -> MealPlanRead | None:
    return current_meal_plan(session, admission_id, service_date=service_date)


@router.get("/meal-plans/{plan_id}", response_model=MealPlanRead)
def get_plan(plan_id: uuid.UUID, _: ClinicalReader, session: DatabaseSession) -> MealPlanRead:
    return read_meal_plan(session, plan_id)


@router.post(
    "/admissions/{admission_id}/meal-plans",
    response_model=MealPlanRead,
    status_code=status.HTTP_201_CREATED,
)
def post_plan(
    admission_id: uuid.UUID,
    payload: MealPlanCreate,
    current: ClinicalEditor,
    session: DatabaseSession,
) -> MealPlanRead:
    return create_meal_plan(session, admission_id, payload, current.user.id)


@router.put("/meal-plans/{plan_id}", response_model=MealPlanRead)
def put_plan(
    plan_id: uuid.UUID,
    payload: MealPlanUpdate,
    current: ClinicalEditor,
    session: DatabaseSession,
) -> MealPlanRead:
    return update_meal_plan(session, plan_id, payload, current.user.id)


@router.post("/meal-plans/{plan_id}/finalize", response_model=MealPlanRead)
def finalize_plan(
    plan_id: uuid.UUID,
    payload: MealPlanFinalize,
    current: ClinicalEditor,
    session: DatabaseSession,
) -> MealPlanRead:
    return finalize_meal_plan(session, plan_id, payload.version, current.user.id)


@router.post("/meal-plans/{plan_id}/cancel", response_model=MealPlanRead)
def cancel_plan(
    plan_id: uuid.UUID,
    payload: MealPlanFinalize,
    current: ClinicalEditor,
    session: DatabaseSession,
) -> MealPlanRead:
    return cancel_meal_plan(session, plan_id, payload.version, current.user.id)


@router.get("/food-production/consolidated", response_model=ProductionConsolidatedRead)
def get_consolidated(
    _: ProductionReader,
    session: DatabaseSession,
    service_date: date,
    meal_time: str | None = None,
) -> ProductionConsolidatedRead:
    return production_consolidated(session, service_date=service_date, meal_time=meal_time)


@router.get("/food-production/consolidated.xlsx")
def download_consolidated(
    _: ProductionReader,
    session: DatabaseSession,
    service_date: date,
    meal_time: str | None = None,
) -> Response:
    data = production_consolidated(session, service_date=service_date, meal_time=meal_time)
    content = production_xlsx(data)
    suffix = f"-{meal_time}" if meal_time else ""
    filename = f"consolidado-raciones-{service_date.isoformat()}{suffix}.xlsx"
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
