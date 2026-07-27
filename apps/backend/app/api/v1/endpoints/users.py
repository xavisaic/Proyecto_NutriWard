from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import CurrentSession, DatabaseSession, require_roles
from app.schemas.user import UserListResponse
from app.services.user_service import list_users

router = APIRouter(prefix="/users", tags=["users"])
UsersReader = Annotated[
    CurrentSession,
    Depends(require_roles("jefatura", "administrador")),
]


@router.get("", response_model=UserListResponse)
def read_users(
    _: UsersReader,
    session: DatabaseSession,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> UserListResponse:
    return list_users(session, offset, limit)
