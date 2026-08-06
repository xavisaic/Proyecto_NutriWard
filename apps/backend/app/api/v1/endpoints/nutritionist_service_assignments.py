import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import (
    CurrentSession,
    DatabaseSession,
    require_roles,
    require_roles_with_csrf,
)
from app.schemas.user import (
    NutritionistServiceAssignmentCreate,
    NutritionistServiceAssignmentListResponse,
    NutritionistServiceAssignmentRead,
    NutritionistServiceAssignmentUpdate,
)
from app.services.administration_service import (
    create_assignment,
    inactivate_assignment,
    list_assignments,
    update_assignment,
)

router = APIRouter(
    prefix="/nutritionist-service-assignments",
    tags=["nutritionist-service-assignments"],
)
AssignmentsReader = Annotated[
    CurrentSession,
    Depends(require_roles("jefatura", "administrador")),
]
CurrentNutritionist = Annotated[
    CurrentSession,
    Depends(require_roles("nutricionista")),
]
AssignmentsAdministrator = Annotated[
    CurrentSession,
    Depends(require_roles_with_csrf("administrador")),
]


@router.get(
    "/me",
    response_model=NutritionistServiceAssignmentListResponse,
)
def read_current_nutritionist_assignments(
    current: CurrentNutritionist,
    session: DatabaseSession,
) -> NutritionistServiceAssignmentListResponse:
    """Return only active service assignments belonging to the current user."""
    return list_assignments(
        session,
        nutritionist_user_id=current.user.id,
        include_inactive=False,
    )


@router.get("", response_model=NutritionistServiceAssignmentListResponse)
def read_assignments(
    _: AssignmentsReader,
    session: DatabaseSession,
    nutritionist_user_id: uuid.UUID | None = Query(default=None),
    include_inactive: bool = Query(default=False),
) -> NutritionistServiceAssignmentListResponse:
    return list_assignments(
        session,
        nutritionist_user_id=nutritionist_user_id,
        include_inactive=include_inactive,
    )


@router.post(
    "",
    response_model=NutritionistServiceAssignmentRead,
    status_code=status.HTTP_201_CREATED,
)
def add_assignment(
    payload: NutritionistServiceAssignmentCreate,
    current: AssignmentsAdministrator,
    session: DatabaseSession,
) -> NutritionistServiceAssignmentRead:
    return create_assignment(session, payload, current.user.id)


@router.patch(
    "/{assignment_id}",
    response_model=NutritionistServiceAssignmentRead,
)
def edit_assignment(
    assignment_id: uuid.UUID,
    payload: NutritionistServiceAssignmentUpdate,
    current: AssignmentsAdministrator,
    session: DatabaseSession,
) -> NutritionistServiceAssignmentRead:
    return update_assignment(session, assignment_id, payload, current.user.id)


@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_assignment(
    assignment_id: uuid.UUID,
    current: AssignmentsAdministrator,
    session: DatabaseSession,
) -> None:
    inactivate_assignment(session, assignment_id, current.user.id)
