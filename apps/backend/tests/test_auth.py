from sqlmodel import select

from app.core.config import settings
from app.core.security import hash_password
from app.models.audit_log import AuditLog
from app.models.user import User


def login(client, email: str = "administrador@nutriward.local"):
    return client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": settings.demo_user_password},
    )


def test_login_sets_secure_session_contract_and_restores_user(client) -> None:
    response = login(client)

    assert response.status_code == 200
    payload = response.json()
    assert payload["user"]["email"] == "administrador@nutriward.local"
    assert payload["user"]["roles"] == ["administrador"]
    assert payload["csrf_token"]
    assert "password_hash" not in payload["user"]

    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "samesite=lax" in cookie
    assert "path=/api/v1" in cookie

    restored = client.get("/api/v1/auth/me")
    assert restored.status_code == 200
    assert restored.json()["csrf_token"] == payload["csrf_token"]


def test_login_failure_is_generic_and_audited(client, db_session) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "desconocido@nutriward.local", "password": "incorrecta"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Correo o contraseña incorrectos."
    event = db_session.exec(
        select(AuditLog).where(AuditLog.action == "login_failure")
    ).one()
    assert event.actor_user_id is None
    assert event.after_state["result"] == "failure"


def test_inactive_user_cannot_login(client, db_session) -> None:
    db_session.add(
        User(
            email="inactivo@nutriward.local",
            full_name="Usuario Inactivo",
            password_hash=hash_password("clave-inactiva"),
            is_active=False,
        )
    )
    db_session.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "inactivo@nutriward.local", "password": "clave-inactiva"},
    )
    assert response.status_code == 401


def test_invalid_token_is_rejected(client) -> None:
    client.cookies.set(settings.auth_cookie_name, "token-alterado", path="/api/v1")
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_logout_requires_csrf_and_writes_audit(client, db_session) -> None:
    session_payload = login(client).json()

    missing_csrf = client.post("/api/v1/auth/logout")
    assert missing_csrf.status_code == 403

    response = client.post(
        "/api/v1/auth/logout",
        headers={"X-CSRF-Token": session_payload["csrf_token"]},
    )
    assert response.status_code == 204
    assert client.get("/api/v1/auth/me").status_code == 401

    events = db_session.exec(select(AuditLog).order_by(AuditLog.occurred_at)).all()
    assert [event.action for event in events][-2:] == ["login_success", "logout"]
