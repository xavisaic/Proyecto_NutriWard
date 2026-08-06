import uuid

from sqlmodel import select

from app.core.config import settings
from app.models.audit_log import AuditLog
from app.models.hospital_service import HospitalService
from app.models.nutritionist_service_assignment import NutritionistServiceAssignment
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole


def login(client, role: str = "administrador") -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": f"{role}@nutriward.local",
            "password": settings.demo_user_password,
        },
    )
    assert response.status_code == 200
    return response.json()["csrf_token"]


def csrf_header(token: str) -> dict[str, str]:
    return {"X-CSRF-Token": token}


def get_user_id(db_session, role: str) -> uuid.UUID:
    return db_session.exec(
        select(User.id).where(User.email == f"{role}@nutriward.local")
    ).one()


def get_role_id(db_session, role: str) -> uuid.UUID:
    return db_session.exec(select(Role.id).where(Role.name == role)).one()


def get_service_id(db_session, code: str) -> uuid.UUID:
    return db_session.exec(
        select(HospitalService.id).where(HospitalService.code == code)
    ).one()


def test_administration_read_permissions(client) -> None:
    for role in ("administrador", "jefatura"):
        login(client, role)
        assert client.get("/api/v1/users").status_code == 200
        assert client.get("/api/v1/roles").status_code == 200
        response = client.get("/api/v1/nutritionist-service-assignments")
        assert response.status_code == 200
        assert response.json()["total"] == 2
        client.cookies.clear()

    for role in ("nutricionista", "alimentacion"):
        login(client, role)
        assert client.get("/api/v1/users").status_code == 403
        assert client.get("/api/v1/roles").status_code == 403
        assert (
            client.get("/api/v1/nutritionist-service-assignments").status_code
            == 403
        )
        client.cookies.clear()


def test_nutritionist_can_read_only_own_active_service_assignments(client) -> None:
    assert client.get("/api/v1/nutritionist-service-assignments/me").status_code == 401

    login(client, "nutricionista")
    response = client.get("/api/v1/nutritionist-service-assignments/me")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert {item["service_code"] for item in body["items"]} == {"MED", "UCI"}
    assert all(item["is_active"] for item in body["items"])
    assert all(
        item["nutritionist_email"] == "nutricionista@nutriward.local"
        for item in body["items"]
    )

    client.cookies.clear()
    login(client, "alimentacion")
    assert client.get("/api/v1/nutritionist-service-assignments/me").status_code == 403


def test_only_administrator_can_mutate_and_csrf_is_required(
    client,
    db_session,
) -> None:
    payload = {
        "email": "nuevo@nutriward.local",
        "full_name": "Usuario Nuevo",
        "password": "clave-segura",
    }
    assert client.post("/api/v1/users", json=payload).status_code == 401

    manager_csrf = login(client, "jefatura")
    response = client.post(
        "/api/v1/users",
        json=payload,
        headers=csrf_header(manager_csrf),
    )
    assert response.status_code == 403
    client.cookies.clear()

    login(client)
    assert client.post("/api/v1/users", json=payload).status_code == 403
    assert db_session.exec(
        select(User).where(User.email == payload["email"])
    ).first() is None


def test_create_and_update_user_without_exposing_password(
    client,
    db_session,
) -> None:
    token = login(client)
    created = client.post(
        "/api/v1/users",
        json={
            "email": " Persona@Example.cl ",
            "full_name": "  Persona   de Prueba ",
            "password": "clave-segura",
        },
        headers=csrf_header(token),
    )
    assert created.status_code == 201
    payload = created.json()
    assert payload["email"] == "persona@example.cl"
    assert payload["full_name"] == "Persona de Prueba"
    assert "password_hash" not in payload

    updated = client.patch(
        f"/api/v1/users/{payload['id']}",
        json={"email": "persona.actualizada@example.cl", "full_name": "Persona Actualizada"},
        headers=csrf_header(token),
    )
    assert updated.status_code == 200
    assert updated.json()["email"] == "persona.actualizada@example.cl"
    assert updated.json()["full_name"] == "Persona Actualizada"

    events = db_session.exec(
        select(AuditLog).where(
            AuditLog.entity_type == "user",
            AuditLog.entity_id == uuid.UUID(payload["id"]),
        )
    ).all()
    assert [event.action for event in events] == ["create", "update"]
    assert all(event.actor_user_id is not None for event in events)


def test_multiple_roles_duplicate_rejection_and_logical_removal(
    client,
    db_session,
) -> None:
    token = login(client)
    created = client.post(
        "/api/v1/users",
        json={
            "email": "multirrol@nutriward.local",
            "full_name": "Usuario Multirrol",
            "password": "clave-segura",
        },
        headers=csrf_header(token),
    ).json()
    user_id = created["id"]
    nutritionist_role_id = get_role_id(db_session, "nutricionista")
    manager_role_id = get_role_id(db_session, "jefatura")

    for role_id in (nutritionist_role_id, manager_role_id):
        response = client.post(
            f"/api/v1/users/{user_id}/roles",
            json={"role_id": str(role_id)},
            headers=csrf_header(token),
        )
        assert response.status_code == 201

    duplicate = client.post(
        f"/api/v1/users/{user_id}/roles",
        json={"role_id": str(nutritionist_role_id)},
        headers=csrf_header(token),
    )
    assert duplicate.status_code == 409
    roles = client.get(f"/api/v1/users/{user_id}/roles")
    assert {item["name"] for item in roles.json()["items"]} == {
        "nutricionista",
        "jefatura",
    }

    removed = client.delete(
        f"/api/v1/users/{user_id}/roles/{manager_role_id}",
        headers=csrf_header(token),
    )
    assert removed.status_code == 204
    link = db_session.exec(
        select(UserRole).where(
            UserRole.user_id == uuid.UUID(user_id),
            UserRole.role_id == manager_role_id,
        )
    ).one()
    assert link.is_active is False
    assert db_session.exec(
        select(AuditLog).where(
            AuditLog.entity_type == "user_role",
            AuditLog.action == "remove_role",
            AuditLog.entity_id == link.id,
        )
    ).one()
    assert db_session.exec(
        select(AuditLog).where(
            AuditLog.entity_type == "user_role",
            AuditLog.action == "assign_role",
            AuditLog.entity_id == link.id,
        )
    ).one()


def test_inactive_user_cannot_receive_roles(client, db_session) -> None:
    token = login(client)
    user_id = get_user_id(db_session, "alimentacion")
    response = client.delete(
        f"/api/v1/users/{user_id}",
        headers=csrf_header(token),
    )
    assert response.status_code == 204

    role_id = get_role_id(db_session, "jefatura")
    rejected = client.post(
        f"/api/v1/users/{user_id}/roles",
        json={"role_id": str(role_id)},
        headers=csrf_header(token),
    )
    assert rejected.status_code == 409
    db_session.expire_all()
    assert db_session.get(User, user_id).is_active is False
    assert db_session.exec(
        select(AuditLog).where(
            AuditLog.entity_type == "user",
            AuditLog.entity_id == user_id,
            AuditLog.action == "inactivate",
        )
    ).one()


def test_multiple_service_assignments_and_duplicate_rejection(
    client,
    db_session,
) -> None:
    token = login(client)
    nutritionist_id = get_user_id(db_session, "nutricionista")
    for code in ("UTI", "CIR"):
        response = client.post(
            "/api/v1/nutritionist-service-assignments",
            json={
                "nutritionist_user_id": str(nutritionist_id),
                "service_id": str(get_service_id(db_session, code)),
            },
            headers=csrf_header(token),
        )
        assert response.status_code == 201

    duplicate = client.post(
        "/api/v1/nutritionist-service-assignments",
        json={
            "nutritionist_user_id": str(nutritionist_id),
            "service_id": str(get_service_id(db_session, "UTI")),
        },
        headers=csrf_header(token),
    )
    assert duplicate.status_code == 409
    response = client.get(
        f"/api/v1/users/{nutritionist_id}/service-assignments"
    )
    assert response.status_code == 200
    assert {item["service_code"] for item in response.json()["items"]} == {
        "MED",
        "UCI",
        "UTI",
        "CIR",
    }


def test_assignment_rejects_non_nutritionist_missing_and_inactive_services(
    client,
    db_session,
) -> None:
    token = login(client)
    manager_id = get_user_id(db_session, "jefatura")
    nutritionist_id = get_user_id(db_session, "nutricionista")
    medicine_id = get_service_id(db_session, "MED")

    non_nutritionist = client.post(
        "/api/v1/nutritionist-service-assignments",
        json={
            "nutritionist_user_id": str(manager_id),
            "service_id": str(medicine_id),
        },
        headers=csrf_header(token),
    )
    assert non_nutritionist.status_code == 409

    missing = client.post(
        "/api/v1/nutritionist-service-assignments",
        json={
            "nutritionist_user_id": str(nutritionist_id),
            "service_id": str(uuid.uuid4()),
        },
        headers=csrf_header(token),
    )
    assert missing.status_code == 404

    inactive_service = db_session.exec(
        select(HospitalService).where(HospitalService.code == "UTI")
    ).one()
    inactive_service.is_active = False
    db_session.add(inactive_service)
    db_session.commit()
    rejected = client.post(
        "/api/v1/nutritionist-service-assignments",
        json={
            "nutritionist_user_id": str(nutritionist_id),
            "service_id": str(inactive_service.id),
        },
        headers=csrf_header(token),
    )
    assert rejected.status_code == 409

    nutritionist = db_session.get(User, nutritionist_id)
    nutritionist.is_active = False
    db_session.add(nutritionist)
    db_session.commit()
    inactive_user = client.post(
        "/api/v1/nutritionist-service-assignments",
        json={
            "nutritionist_user_id": str(nutritionist_id),
            "service_id": str(medicine_id),
        },
        headers=csrf_header(token),
    )
    assert inactive_user.status_code == 409


def test_assignment_inactivation_is_logical_and_audited(
    client,
    db_session,
) -> None:
    token = login(client)
    assignment = db_session.exec(
        select(NutritionistServiceAssignment).where(
            NutritionistServiceAssignment.service_id
            == get_service_id(db_session, "MED")
        )
    ).one()
    response = client.delete(
        f"/api/v1/nutritionist-service-assignments/{assignment.id}",
        headers=csrf_header(token),
    )
    assert response.status_code == 204

    db_session.expire_all()
    persisted = db_session.get(NutritionistServiceAssignment, assignment.id)
    assert persisted is not None
    assert persisted.is_active is False
    event = db_session.exec(
        select(AuditLog).where(
            AuditLog.entity_type == "nutritionist_service_assignment",
            AuditLog.entity_id == assignment.id,
            AuditLog.action == "inactivate",
        )
    ).one()
    assert event.before_state["is_active"] is True
    assert event.after_state["is_active"] is False
    assert event.actor_user_id == get_user_id(db_session, "administrador")


def test_assignment_update_is_audited(client, db_session) -> None:
    token = login(client)
    assignment = db_session.exec(
        select(NutritionistServiceAssignment).where(
            NutritionistServiceAssignment.service_id
            == get_service_id(db_session, "MED")
        )
    ).one()
    surgery_id = get_service_id(db_session, "CIR")

    response = client.patch(
        f"/api/v1/nutritionist-service-assignments/{assignment.id}",
        json={"service_id": str(surgery_id)},
        headers=csrf_header(token),
    )
    assert response.status_code == 200
    assert response.json()["service_code"] == "CIR"

    event = db_session.exec(
        select(AuditLog).where(
            AuditLog.entity_type == "nutritionist_service_assignment",
            AuditLog.entity_id == assignment.id,
            AuditLog.action == "update",
        )
    ).one()
    assert event.before_state["service_id"] != event.after_state["service_id"]
