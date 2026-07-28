import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import CurrentSession, DatabaseSession, require_roles
from app.schemas.user import RoleListResponse, UserListResponse
from app.services.administration_service import list_role_users, list_roles

router = APIRouter(prefix="/roles", tags=["roles"])
RolesReader = Annotated[
    CurrentSession,
    Depends(require_roles("jefatura", "administrador")),
]


@router.get("", response_model=RoleListResponse)
def read_roles(
    _: RolesReader,
    session: DatabaseSession,
) -> RoleListResponse:
    return list_roles(session)


@router.get("/{role_id}/users", response_model=UserListResponse)
def read_users_for_role(
    role_id: uuid.UUID,
    _: RolesReader,
    session: DatabaseSession,
) -> UserListResponse:
    return list_role_users(session, role_id)
