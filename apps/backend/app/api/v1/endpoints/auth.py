from fastapi import APIRouter, HTTPException, Response, status

from app.api.dependencies import AuthenticatedSession, CsrfProtectedSession, DatabaseSession
from app.core.config import settings
from app.core.security import (
    DUMMY_PASSWORD_HASH,
    create_access_token,
    verify_password,
)
from app.schemas.auth import LoginRequest, SessionResponse
from app.services.audit_service import record_audit
from app.services.user_service import get_user_by_email, normalize_email, to_user_read

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=SessionResponse)
def login(payload: LoginRequest, response: Response, session: DatabaseSession) -> SessionResponse:
    email = normalize_email(str(payload.email))
    user = get_user_by_email(session, email)
    password_matches = verify_password(
        payload.password,
        user.password_hash if user is not None else DUMMY_PASSWORD_HASH,
    )

    if user is None or not password_matches or not user.is_active:
        record_audit(
            session,
            action="login_failure",
            actor_user_id=user.id if user is not None else None,
            entity_type="auth_session",
            entity_id=user.id if user is not None else None,
            after_state={"email": email, "result": "failure"},
        )
        session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos.",
        )

    token, csrf_token = create_access_token(user.id)
    record_audit(
        session,
        action="login_success",
        actor_user_id=user.id,
        entity_type="auth_session",
        entity_id=user.id,
        after_state={"result": "success"},
    )
    session.commit()
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=token,
        max_age=settings.access_token_expire_minutes * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/api/v1",
    )
    response.headers["Cache-Control"] = "no-store"
    return SessionResponse(user=to_user_read(session, user), csrf_token=csrf_token)


@router.get("/me", response_model=SessionResponse)
def read_session(current: AuthenticatedSession, session: DatabaseSession) -> SessionResponse:
    return SessionResponse(
        user=to_user_read(session, current.user),
        csrf_token=current.csrf_token,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    current: CsrfProtectedSession,
    session: DatabaseSession,
) -> Response:
    record_audit(
        session,
        action="logout",
        actor_user_id=current.user.id,
        entity_type="auth_session",
        entity_id=current.user.id,
        before_state={"authenticated": True},
        after_state={"authenticated": False},
    )
    session.commit()
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(
        key=settings.auth_cookie_name,
        path="/api/v1",
        secure=settings.cookie_secure,
        httponly=True,
        samesite="lax",
    )
    response.headers["Cache-Control"] = "no-store"
    return response
