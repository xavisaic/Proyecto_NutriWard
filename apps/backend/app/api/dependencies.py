import secrets
from dataclasses import dataclass
from typing import Annotated, Callable

from fastapi import Depends, HTTPException, Request, status
from sqlmodel import Session

from app.core.config import settings
from app.core.security import decode_access_token
from app.db.session import get_session
from app.models.user import User
from app.services.user_service import get_role_names, get_user_by_id

DatabaseSession = Annotated[Session, Depends(get_session)]


@dataclass(frozen=True)
class CurrentSession:
    user: User
    roles: frozenset[str]
    csrf_token: str


def get_current_session(request: Request, session: DatabaseSession) -> CurrentSession:
    token = request.cookies.get(settings.auth_cookie_name)
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No fue posible validar la sesión.",
    )
    if not token:
        raise credentials_error
    try:
        claims = decode_access_token(token)
    except ValueError as exc:
        raise credentials_error from exc

    user = get_user_by_id(session, claims.user_id)
    if user is None or not user.is_active:
        raise credentials_error
    return CurrentSession(
        user=user,
        roles=frozenset(get_role_names(session, user.id)),
        csrf_token=claims.csrf_token,
    )


AuthenticatedSession = Annotated[CurrentSession, Depends(get_current_session)]


def require_csrf(request: Request, current: AuthenticatedSession) -> CurrentSession:
    supplied_token = request.headers.get("X-CSRF-Token", "")
    if not supplied_token or not secrets.compare_digest(supplied_token, current.csrf_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token CSRF inválido.",
        )
    return current


CsrfProtectedSession = Annotated[CurrentSession, Depends(require_csrf)]


def require_roles(*allowed_roles: str) -> Callable:
    def role_dependency(current: AuthenticatedSession) -> CurrentSession:
        if current.roles.isdisjoint(allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permisos para realizar esta acción.",
            )
        return current

    return role_dependency
