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
    NutritionistServiceAssignmentListResponse,
    RoleListResponse,
    UserCreate,
    UserListResponse,
    UserRead,
    UserRoleAssign,
    UserRoleRead,
    UserUpdate,
)
from app.services.administration_service import (
    assign_role,
    create_user,
    inactivate_user,
    list_assignments,
    list_user_roles,
    read_user,
    remove_role,
    update_user,
)
from app.services.user_service import list_users

router = APIRouter(prefix="/users", tags=["users"])
UsersReader = Annotated[
    CurrentSession,
    Depends(require_roles("jefatura", "administrador")),
]
UsersAdministrator = Annotated[
    CurrentSession,
    Depends(require_roles_with_csrf("administrador")),
]


@router.get("", response_model=UserListResponse)
def read_users(
    _: UsersReader,
    session: DatabaseSession,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> UserListResponse:
    return list_users(session, offset, limit)


@router.get("/{user_id}", response_model=UserRead)
def read_user_detail(
    user_id: uuid.UUID,
    _: UsersReader,
    session: DatabaseSession,
) -> UserRead:
    return read_user(session, user_id)


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def add_user(
    payload: UserCreate,
    current: UsersAdministrator,
    session: DatabaseSession,
) -> UserRead:
    return create_user(session, payload, current.user.id)


@router.patch("/{user_id}", response_model=UserRead)
def edit_user(
    user_id: uuid.UUID,
    payload: UserUpdate,
    current: UsersAdministrator,
    session: DatabaseSession,
) -> UserRead:
    return update_user(session, user_id, payload, current.user.id)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_user(
    user_id: uuid.UUID,
    current: UsersAdministrator,
    session: DatabaseSession,
) -> None:
    inactivate_user(session, user_id, current.user.id)


@router.get("/{user_id}/roles", response_model=RoleListResponse)
def read_roles_for_user(
    user_id: uuid.UUID,
    _: UsersReader,
    session: DatabaseSession,
) -> RoleListResponse:
    return list_user_roles(session, user_id)


@router.post(
    "/{user_id}/roles",
    response_model=UserRoleRead,
    status_code=status.HTTP_201_CREATED,
)
def add_role_to_user(
    user_id: uuid.UUID,
    payload: UserRoleAssign,
    current: UsersAdministrator,
    session: DatabaseSession,
) -> UserRoleRead:
    return assign_role(session, user_id, payload.role_id, current.user.id)


@router.delete(
    "/{user_id}/roles/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_role_from_user(
    user_id: uuid.UUID,
    role_id: uuid.UUID,
    current: UsersAdministrator,
    session: DatabaseSession,
) -> None:
    remove_role(session, user_id, role_id, current.user.id)


@router.get(
    "/{user_id}/service-assignments",
    response_model=NutritionistServiceAssignmentListResponse,
)
def read_service_assignments_for_user(
    user_id: uuid.UUID,
    _: UsersReader,
    session: DatabaseSession,
    include_inactive: bool = Query(default=False),
) -> NutritionistServiceAssignmentListResponse:
    return list_assignments(
        session,
        nutritionist_user_id=user_id,
        include_inactive=include_inactive,
    )
