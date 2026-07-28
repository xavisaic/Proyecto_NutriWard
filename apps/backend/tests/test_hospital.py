import uuid

from sqlmodel import select

from app.core.config import settings
from app.models.audit_log import AuditLog


def authenticate(client, role: str = "administrador") -> dict:
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": f"{role}@nutriward.local",
            "password": settings.demo_user_password,
        },
    )
    assert response.status_code == 200
    return response.json()


def csrf_headers(session_payload: dict) -> dict[str, str]:
    return {"X-CSRF-Token": session_payload["csrf_token"]}


def test_all_authenticated_roles_can_read_active_structure(client) -> None:
    for role in ("administrador", "jefatura", "nutricionista", "alimentacion"):
        authenticate(client, role)
        response = client.get("/api/v1/hospital/structure")
        assert response.status_code == 200
        structure = response.json()
        assert structure["total"] == 4
        assert {service["code"] for service in structure["items"]} == {
            "MED",
            "UCI",
            "UTI",
            "CIR",
        }
        assert sum(len(service["rooms"]) for service in structure["items"]) == 5
        assert (
            sum(
                len(room["care_units"])
                for service in structure["items"]
                for room in service["rooms"]
            )
            == 10
        )
        client.cookies.clear()


def test_structure_requires_authentication(client) -> None:
    assert client.get("/api/v1/hospital/structure").status_code == 401


def test_operational_roles_cannot_mutate_structure(client) -> None:
    for role in ("nutricionista", "alimentacion"):
        auth = authenticate(client, role)
        response = client.post(
            "/api/v1/hospital/services",
            headers=csrf_headers(auth),
            json={"code": "PED", "name": "Pediatría"},
        )
        assert response.status_code == 403
        client.cookies.clear()


def test_mutations_require_csrf(client) -> None:
    authenticate(client)
    response = client.post(
        "/api/v1/hospital/services",
        json={"code": "PED", "name": "Pediatría"},
    )
    assert response.status_code == 403


def test_editor_can_build_and_place_hospital_structure(client, db_session) -> None:
    auth = authenticate(client, "jefatura")
    headers = csrf_headers(auth)

    service_response = client.post(
        "/api/v1/hospital/services",
        headers=headers,
        json={
            "code": " ped ",
            "name": "Pediatría",
            "description": "Hospitalización infantil",
        },
    )
    assert service_response.status_code == 201
    service = service_response.json()
    assert service["code"] == "PED"

    room_response = client.post(
        "/api/v1/hospital/rooms",
        headers=headers,
        json={
            "service_id": service["id"],
            "code": "p-201",
            "name": "Sala Pediátrica 201",
            "floor": "Piso 2",
            "notes": "Sector pediátrico",
        },
    )
    assert room_response.status_code == 201
    room = room_response.json()
    assert room["code"] == "P-201"
    assert room["notes"] == "Sector pediátrico"

    care_unit_response = client.post(
        "/api/v1/hospital/care-units",
        headers=headers,
        json={
            "room_id": room["id"],
            "code": "1",
            "label": "Camilla ventana",
            "unit_type": "stretcher",
        },
    )
    assert care_unit_response.status_code == 201
    care_unit = care_unit_response.json()
    assert care_unit["unit_type"] == "stretcher"

    layout_response = client.put(
        f"/api/v1/hospital/care-units/{care_unit['id']}/layout",
        headers=headers,
        json={"grid_x": 2, "grid_y": 3, "width": 2, "height": 1},
    )
    assert layout_response.status_code == 200
    assert layout_response.json()["layout"]["grid_x"] == 2

    structure = client.get("/api/v1/hospital/structure").json()
    pediatrics = next(item for item in structure["items"] if item["code"] == "PED")
    assert pediatrics["rooms"][0]["care_units"][0]["label"] == "Camilla ventana"
    assert pediatrics["rooms"][0]["care_units"][0]["unit_type"] == "stretcher"

    events = db_session.exec(
        select(AuditLog).where(
            AuditLog.actor_user_id == uuid.UUID(auth["user"]["id"]),
            AuditLog.entity_type.in_(
                ["service", "room", "care_unit", "care_unit_layout_position"]
            ),
        ).order_by(AuditLog.occurred_at)
    ).all()
    assert [(event.entity_type, event.action) for event in events] == [
        ("service", "create"),
        ("room", "create"),
        ("care_unit", "create"),
        ("care_unit_layout_position", "create"),
    ]


def test_care_unit_code_is_suggested_and_never_reuses_inactive_codes(client) -> None:
    auth = authenticate(client)
    headers = csrf_headers(auth)
    structure = client.get("/api/v1/hospital/structure").json()
    room = next(item for item in structure["items"] if item["code"] == "MED")["rooms"][0]

    created = client.post(
        "/api/v1/hospital/care-units",
        headers=headers,
        json={"room_id": room["id"], "label": "Código automático"},
    )
    assert created.status_code == 201
    assert created.json()["code"] == "03"

    inactivated = client.patch(
        f"/api/v1/hospital/care-units/{created.json()['id']}",
        headers=headers,
        json={"is_active": False},
    )
    assert inactivated.status_code == 200

    next_care_unit = client.post(
        "/api/v1/hospital/care-units",
        headers=headers,
        json={"room_id": room["id"]},
    )
    assert next_care_unit.status_code == 201
    assert next_care_unit.json()["code"] == "04"
    assert next_care_unit.json()["unit_type"] == "bed"


def test_care_unit_type_accepts_catalog_and_rejects_unknown_values(client) -> None:
    auth = authenticate(client)
    headers = csrf_headers(auth)
    structure = client.get("/api/v1/hospital/structure").json()
    room = next(item for item in structure["items"] if item["code"] == "MED")["rooms"][0]

    for index, unit_type in enumerate(("stretcher", "station", "box"), start=20):
        response = client.post(
            "/api/v1/hospital/care-units",
            headers=headers,
            json={
                "room_id": room["id"],
                "code": str(index),
                "unit_type": unit_type,
            },
        )
        assert response.status_code == 201
        assert response.json()["unit_type"] == unit_type

    invalid = client.post(
        "/api/v1/hospital/care-units",
        headers=headers,
        json={
            "room_id": room["id"],
            "code": "99",
            "unit_type": "chair",
        },
    )
    assert invalid.status_code == 422


def test_duplicate_codes_are_rejected_within_parent(client) -> None:
    auth = authenticate(client)
    headers = csrf_headers(auth)
    structure = client.get("/api/v1/hospital/structure").json()
    medicine = next(item for item in structure["items"] if item["code"] == "MED")
    room = medicine["rooms"][0]

    duplicate_service = client.post(
        "/api/v1/hospital/services",
        headers=headers,
        json={"code": "med", "name": "Otro servicio"},
    )
    assert duplicate_service.status_code == 409

    duplicate_room = client.post(
        "/api/v1/hospital/rooms",
        headers=headers,
        json={
            "service_id": medicine["id"],
            "code": room["code"].lower(),
            "name": "Otra sala",
        },
    )
    assert duplicate_room.status_code == 409

    duplicate_care_unit = client.post(
        "/api/v1/hospital/care-units",
        headers=headers,
        json={
            "room_id": room["id"],
            "code": room["care_units"][0]["code"],
        },
    )
    assert duplicate_care_unit.status_code == 409


def test_required_update_fields_reject_explicit_null(client) -> None:
    auth = authenticate(client)
    headers = csrf_headers(auth)
    structure = client.get("/api/v1/hospital/structure").json()
    medicine = next(item for item in structure["items"] if item["code"] == "MED")
    room = medicine["rooms"][0]
    care_unit = room["care_units"][0]

    assert client.patch(
        f"/api/v1/hospital/services/{medicine['id']}",
        headers=headers,
        json={"code": None},
    ).status_code == 422
    assert client.patch(
        f"/api/v1/hospital/rooms/{room['id']}",
        headers=headers,
        json={"service_id": None},
    ).status_code == 422
    assert client.patch(
        f"/api/v1/hospital/care-units/{care_unit['id']}",
        headers=headers,
        json={"room_id": None},
    ).status_code == 422


def test_soft_delete_respects_active_dependencies_and_filter(client) -> None:
    auth = authenticate(client)
    headers = csrf_headers(auth)
    structure = client.get("/api/v1/hospital/structure").json()
    intensive_care = next(item for item in structure["items"] if item["code"] == "UCI")
    room = intensive_care["rooms"][0]

    blocked_service = client.patch(
        f"/api/v1/hospital/services/{intensive_care['id']}",
        headers=headers,
        json={"is_active": False},
    )
    assert blocked_service.status_code == 409

    for care_unit in room["care_units"]:
        response = client.patch(
            f"/api/v1/hospital/care-units/{care_unit['id']}",
            headers=headers,
            json={"is_active": False},
        )
        assert response.status_code == 200

    room_response = client.patch(
        f"/api/v1/hospital/rooms/{room['id']}",
        headers=headers,
        json={"is_active": False},
    )
    assert room_response.status_code == 200

    service_response = client.patch(
        f"/api/v1/hospital/services/{intensive_care['id']}",
        headers=headers,
        json={"is_active": False},
    )
    assert service_response.status_code == 200

    active_codes = {
        item["code"] for item in client.get("/api/v1/hospital/structure").json()["items"]
    }
    assert "UCI" not in active_codes
    all_codes = {
        item["code"]
        for item in client.get(
            "/api/v1/hospital/structure?include_inactive=true"
        ).json()["items"]
    }
    assert "UCI" in all_codes


def test_only_administrator_can_purge_inactive_structure(client, db_session) -> None:
    manager_auth = authenticate(client, "jefatura")
    manager_headers = csrf_headers(manager_auth)
    structure = client.get("/api/v1/hospital/structure").json()
    care_unit = next(item for item in structure["items"] if item["code"] == "MED")["rooms"][0]["care_units"][0]
    assert client.patch(
        f"/api/v1/hospital/care-units/{care_unit['id']}",
        headers=manager_headers,
        json={"is_active": False},
    ).status_code == 200
    assert client.request(
        "DELETE",
        f"/api/v1/hospital/care-units/{care_unit['id']}",
        headers=manager_headers,
        json={"reason": "Registro creado por error."},
    ).status_code == 403

    client.cookies.clear()
    admin_auth = authenticate(client)
    admin_headers = csrf_headers(admin_auth)
    deleted = client.request(
        "DELETE",
        f"/api/v1/hospital/care-units/{care_unit['id']}",
        headers=admin_headers,
        json={"reason": "Registro creado por error."},
    )
    assert deleted.status_code == 204

    structure_with_inactive = client.get(
        "/api/v1/hospital/structure?include_inactive=true"
    ).json()
    assert all(
        candidate["id"] != care_unit["id"]
        for service in structure_with_inactive["items"]
        for room in service["rooms"]
        for candidate in room["care_units"]
    )
    audit = db_session.exec(
        select(AuditLog).where(
            AuditLog.entity_type == "care_unit",
            AuditLog.entity_id == uuid.UUID(care_unit["id"]),
            AuditLog.action == "delete",
        )
    ).first()
    assert audit is not None
    assert audit.after_state["reason"] == "Registro creado por error."


def test_purge_requires_inactive_entities_without_dependencies(client) -> None:
    auth = authenticate(client)
    headers = csrf_headers(auth)
    structure = client.get("/api/v1/hospital/structure").json()
    medicine = next(item for item in structure["items"] if item["code"] == "MED")
    room = medicine["rooms"][0]

    assert client.request(
        "DELETE",
        f"/api/v1/hospital/care-units/{room['care_units'][0]['id']}",
        headers=headers,
        json={"reason": "Registro creado por error."},
    ).status_code == 409

    for care_unit in room["care_units"]:
        assert client.patch(
            f"/api/v1/hospital/care-units/{care_unit['id']}",
            headers=headers,
            json={"is_active": False},
        ).status_code == 200
    assert client.patch(
        f"/api/v1/hospital/rooms/{room['id']}",
        headers=headers,
        json={"is_active": False},
    ).status_code == 200
    assert client.request(
        "DELETE",
        f"/api/v1/hospital/rooms/{room['id']}",
        headers=headers,
        json={"reason": "Registro creado por error."},
    ).status_code == 409
