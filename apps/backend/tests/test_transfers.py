import uuid

from sqlmodel import select

from app.core.config import settings
from app.models.admission import Admission
from app.models.audit_log import AuditLog
from app.models.care_unit import CareUnit
from app.models.hospital_service import HospitalService
from app.models.patient_location_history import PatientLocationHistory
from app.models.patient_transfer_request import PatientTransferRequest
from app.models.patient_transfer_request_status_history import (
    PatientTransferRequestStatusHistory,
)
from app.models.room import Room


def authenticate(client, role: str = "jefatura") -> dict:
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": f"{role}@nutriward.local",
            "password": settings.demo_user_password,
        },
    )
    assert response.status_code == 200
    return response.json()


def headers(auth: dict) -> dict[str, str]:
    return {"X-CSRF-Token": auth["csrf_token"]}


def service(db_session, code: str) -> HospitalService:
    return db_session.exec(
        select(HospitalService).where(HospitalService.code == code)
    ).one()


def available_beds(db_session, service_code: str) -> list[CareUnit]:
    occupied = set(
        db_session.exec(
            select(PatientLocationHistory.care_unit_id).where(
                PatientLocationHistory.ended_at.is_(None)
            )
        ).all()
    )
    return [
        bed
        for bed in db_session.exec(
            select(CareUnit)
            .join(Room, Room.id == CareUnit.room_id)
            .join(HospitalService, HospitalService.id == Room.service_id)
            .where(
                HospitalService.code == service_code,
                CareUnit.unit_type == "bed",
                CareUnit.is_active.is_(True),
                Room.is_active.is_(True),
            )
            .order_by(Room.code, CareUnit.code)
        ).all()
        if bed.id not in occupied
    ]


def create_admission_in(client, db_session, auth: dict, service_code: str) -> tuple[dict, CareUnit]:
    patient = client.post(
        "/api/v1/patients/unidentified",
        headers=headers(auth),
        json={"provisional_description": f"Paciente ficticio para traslado {uuid.uuid4()}"},
    )
    assert patient.status_code == 201, patient.text
    origin = available_beds(db_session, service_code)[0]
    admission = client.post(
        "/api/v1/admissions",
        headers=headers(auth),
        json={"patient_id": patient.json()["id"], "care_unit_id": str(origin.id)},
    )
    assert admission.status_code == 201, admission.text
    return admission.json(), origin


def create_tray(client, db_session, auth: dict, origin="MED", destination="UCI") -> tuple[dict, dict]:
    admission, _ = create_admission_in(client, db_session, auth, origin)
    response = client.post(
        "/api/v1/transfer-requests",
        headers=headers(auth),
        json={
            "admission_id": admission["id"],
            "destination_service_id": str(service(db_session, destination).id),
            "transfer_mode": "reception_tray",
            "destination_care_unit_id": None,
        },
    )
    assert response.status_code == 201, response.text
    return admission, response.json()


def test_auth_csrf_and_role_matrix(client, db_session) -> None:
    med = service(db_session, "MED")
    assert client.get(f"/api/v1/transfer-requests/reception-tray?service_id={med.id}").status_code == 401
    for role in ("administrador", "jefatura", "nutricionista", "alimentacion"):
        client.cookies.clear()
        auth = authenticate(client, role)
        assert client.get(
            f"/api/v1/transfer-requests/reception-tray?service_id={med.id}"
        ).status_code == 200
        demo_admission = db_session.exec(
            select(Admission).where(Admission.admission_identifier == "ADM-DEMO-ACT-003")
        ).one()
        mutation = client.post(
            "/api/v1/transfer-requests",
            headers=headers(auth),
            json={
                "admission_id": str(demo_admission.id),
                "destination_service_id": str(service(db_session, "UCI").id),
                "transfer_mode": "reception_tray",
                "reason": "Intento según rol.",
            },
        )
        if role in {"administrador", "alimentacion"}:
            assert mutation.status_code == 403
        else:
            # The selected admission intentionally has no bed, proving the role
            # passed auth/CSRF and reached the domain validation.
            assert mutation.status_code == 409
    client.cookies.clear()
    authenticate(client, "jefatura")
    assert client.post("/api/v1/transfer-requests", json={}).status_code == 403


def test_direct_transfer_is_atomic_historized_and_audited(client, db_session) -> None:
    auth = authenticate(client)
    admission, origin_bed = create_admission_in(client, db_session, auth, "MED")
    destination_bed = available_beds(db_session, "UCI")[0]
    response = client.post(
        "/api/v1/transfer-requests",
        headers=headers(auth),
        json={
            "admission_id": admission["id"],
            "destination_service_id": str(service(db_session, "UCI").id),
            "transfer_mode": "direct",
            "destination_care_unit_id": str(destination_bed.id),
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "assigned_to_bed"
    assert body["request_reason"] is None
    assert [item["to_status"] for item in body["status_history"]] == [
        "requested", "pending_reception", "accepted", "assigned_to_bed"
    ]
    assert [item["sequence_number"] for item in body["status_history"]] == [1, 2, 3, 4]
    assert body["status_history"][0]["reason"] is None
    locations = db_session.exec(
        select(PatientLocationHistory)
        .where(PatientLocationHistory.admission_id == uuid.UUID(admission["id"]))
        .order_by(PatientLocationHistory.started_at, PatientLocationHistory.id)
    ).all()
    assert len(locations) == 2
    assert locations[0].care_unit_id == origin_bed.id and locations[0].ended_at is not None
    assert locations[1].care_unit_id == destination_bed.id and locations[1].ended_at is None
    assert len([item for item in locations if item.ended_at is None]) == 1
    audits = db_session.exec(
        select(AuditLog).where(AuditLog.admission_id == uuid.UUID(admission["id"]))
    ).all()
    assert {"transfer_requested", "transfer_pending_reception", "transfer_accepted", "transfer_assigned_to_bed"} <= {
        item.action for item in audits
    }


def test_reception_tray_keeps_origin_then_accepts_and_assigns_current_origin_bed(
    client, db_session
) -> None:
    auth = authenticate(client)
    admission, transfer = create_tray(client, db_session, auth)
    assert transfer["status"] == "pending_reception"
    assert transfer["current_origin_location"]["service_code"] == "MED"
    med_map = client.get(
        f"/api/v1/bed-map?service_id={service(db_session, 'MED').id}"
    ).json()
    origin_occupancy = next(
        bed["occupancy"]
        for room in med_map["rooms"]
        for bed in room["beds"]
        if bed["occupancy"] and bed["occupancy"]["patient"]["id"] == admission["patient_id"]
    )
    assert origin_occupancy["pending_transfer"] == {
        "id": transfer["id"],
        "status": "pending_reception",
        "destination_service_id": str(service(db_session, "UCI").id),
        "destination_service_code": "UCI",
        "destination_service_name": "Unidad de Cuidados Intensivos",
        "requested_at": transfer["requested_at"],
    }
    uci_map = client.get(
        f"/api/v1/bed-map?service_id={service(db_session, 'UCI').id}"
    ).json()
    assert admission["patient_id"] not in {
        bed["occupancy"]["patient"]["id"]
        for room in uci_map["rooms"] for bed in room["beds"] if bed["occupancy"]
    }

    # A pending request follows a valid bed change inside its origin service.
    another_origin_bed = available_beds(db_session, "MED")[0]
    moved = client.post(
        f"/api/v1/admissions/{admission['id']}/location",
        headers=headers(auth),
        json={"care_unit_id": str(another_origin_bed.id), "reason": "Cambio interno de cama."},
    )
    assert moved.status_code == 201, moved.text
    refreshed = client.get(f"/api/v1/transfer-requests/{transfer['id']}").json()
    assert refreshed["origin_care_unit_id"] != refreshed["current_origin_location"]["care_unit_id"]
    assert refreshed["current_origin_location"]["care_unit_id"] == str(another_origin_bed.id)

    accepted = client.post(
        f"/api/v1/transfer-requests/{transfer['id']}/accept",
        headers=headers(auth),
        json={"destination_care_unit_id": None, "observation": "Recepción coordinada."},
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["status"] == "pending_bed"
    med_map = client.get(
        f"/api/v1/bed-map?service_id={service(db_session, 'MED').id}"
    ).json()
    assert next(
        bed["occupancy"]["pending_transfer"]["status"]
        for room in med_map["rooms"]
        for bed in room["beds"]
        if bed["occupancy"] and bed["occupancy"]["patient"]["id"] == admission["patient_id"]
    ) == "pending_bed"
    destination_bed = available_beds(db_session, "UCI")[0]
    assigned = client.post(
        f"/api/v1/transfer-requests/{transfer['id']}/assign-bed",
        headers=headers(auth),
        json={"destination_care_unit_id": str(destination_bed.id)},
    )
    assert assigned.status_code == 200, assigned.text
    assert assigned.json()["status"] == "assigned_to_bed"
    db_session.expire_all()
    current = db_session.exec(
        select(PatientLocationHistory).where(
            PatientLocationHistory.admission_id == uuid.UUID(admission["id"]),
            PatientLocationHistory.ended_at.is_(None),
        )
    ).one()
    assert current.care_unit_id == destination_bed.id
    destination_map = client.get(
        f"/api/v1/bed-map?service_id={service(db_session, 'UCI').id}"
    ).json()
    destination_occupancy = next(
        bed["occupancy"]
        for room in destination_map["rooms"]
        for bed in room["beds"]
        if bed["occupancy"] and bed["occupancy"]["patient"]["id"] == admission["patient_id"]
    )
    assert destination_occupancy["pending_transfer"] is None
    assert client.get(
        f"/api/v1/transfer-requests/reception-tray?service_id={service(db_session, 'UCI').id}"
    ).json()["items"] == []


def test_accept_with_bed_and_invalid_terminal_transitions(client, db_session) -> None:
    auth = authenticate(client)
    _, transfer = create_tray(client, db_session, auth)
    destination_bed = available_beds(db_session, "UCI")[0]
    accepted = client.post(
        f"/api/v1/transfer-requests/{transfer['id']}/accept",
        headers=headers(auth),
        json={"destination_care_unit_id": str(destination_bed.id)},
    )
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "assigned_to_bed"
    for action in ("reject", "return", "cancel", "accept", "assign-bed"):
        payload = (
            {"destination_care_unit_id": str(destination_bed.id)}
            if action == "assign-bed"
            else {"reason": "Intento terminal inválido."}
            if action in {"reject", "return", "cancel"}
            else {"destination_care_unit_id": None}
        )
        assert client.post(
            f"/api/v1/transfer-requests/{transfer['id']}/{action}",
            headers=headers(auth),
            json=payload,
        ).status_code == 409


def test_reject_return_cancel_require_reason_and_keep_location(client, db_session) -> None:
    auth = authenticate(client)
    actions = ("reject", "return", "cancel")
    for index, action in enumerate(actions):
        admission, transfer = create_tray(client, db_session, auth, origin="MED", destination="UCI")
        if action == "return" or (action == "cancel" and index % 2):
            accepted = client.post(
                f"/api/v1/transfer-requests/{transfer['id']}/accept",
                headers=headers(auth),
                json={"destination_care_unit_id": None},
            )
            assert accepted.status_code == 200
        missing = client.post(
            f"/api/v1/transfer-requests/{transfer['id']}/{action}",
            headers=headers(auth),
            json={"reason": " "},
        )
        assert missing.status_code == 422
        terminal = client.post(
            f"/api/v1/transfer-requests/{transfer['id']}/{action}",
            headers=headers(auth),
            json={"reason": f"Motivo ficticio para {action}."},
        )
        assert terminal.status_code == 200, terminal.text
        assert terminal.json()["status"] == (
            "returned" if action == "return" else "rejected" if action == "reject" else "cancelled"
        )
        assert client.get(f"/api/v1/admissions/{admission['id']}/location").status_code == 200


def test_manual_cross_service_bypass_and_duplicate_open_are_conflicts(client, db_session) -> None:
    auth = authenticate(client)
    admission, transfer = create_tray(client, db_session, auth)
    cross_bed = available_beds(db_session, "UCI")[0]
    bypass = client.post(
        f"/api/v1/admissions/{admission['id']}/location",
        headers=headers(auth),
        json={"care_unit_id": str(cross_bed.id)},
    )
    assert bypass.status_code == 409
    duplicate = client.post(
        "/api/v1/transfer-requests",
        headers=headers(auth),
        json={
            "admission_id": admission["id"],
            "destination_service_id": str(service(db_session, "UTI").id),
            "transfer_mode": "reception_tray",
            "reason": "Segundo traslado no permitido.",
        },
    )
    assert duplicate.status_code == 409
    assert db_session.exec(
        select(PatientTransferRequest).where(
            PatientTransferRequest.admission_id == uuid.UUID(admission["id"]),
            PatientTransferRequest.status.in_(("requested", "pending_reception", "accepted", "pending_bed")),
        )
    ).one().id == uuid.UUID(transfer["id"])


def test_admission_end_cancels_open_transfer_in_same_transaction(client, db_session) -> None:
    auth = authenticate(client)
    admission, transfer = create_tray(client, db_session, auth)
    ended = client.patch(
        f"/api/v1/admissions/{admission['id']}/status",
        headers=headers(auth),
        json={"status": "discharged", "reason": "Alta ficticia de prueba."},
    )
    assert ended.status_code == 200, ended.text
    detail = client.get(f"/api/v1/transfer-requests/{transfer['id']}").json()
    assert detail["status"] == "cancelled"
    assert detail["status_history"][-1]["reason"].startswith("Término de hospitalización:")
    assert ended.json()["current_location"] is None


def test_privacy_pagination_order_openapi_and_seed_states(client, db_session) -> None:
    authenticate(client, "alimentacion")
    med = service(db_session, "MED")
    response = client.get(
        f"/api/v1/transfer-requests/reception-tray?service_id={med.id}&page=1&page_size=1"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["page"] == body["page_size"] == 1 and body["total"] >= 2
    serialized = response.text.lower()
    for forbidden in (
        "rut", "phone", "date_of_birth", "hospital_identifier", "provisional_description",
        "clinical", "nutrition", "audit_logs",
    ):
        assert forbidden not in serialized
    statuses = set(db_session.exec(select(PatientTransferRequest.status)).all())
    assert {"pending_reception", "pending_bed", "assigned_to_bed", "rejected", "returned", "cancelled"} <= statuses
    operation_paths = client.get("/openapi.json").json()["paths"]
    assert {
        "/api/v1/transfer-requests",
        "/api/v1/transfer-requests/reception-tray",
        "/api/v1/transfer-requests/{transfer_request_id}/accept",
        "/api/v1/transfer-requests/{transfer_request_id}/assign-bed",
    } <= set(operation_paths)


def test_seed_is_idempotent_for_transfer_sequences(db_session) -> None:
    from app.db.seed import seed_database

    before = (
        len(db_session.exec(select(PatientTransferRequest)).all()),
        len(db_session.exec(select(PatientTransferRequestStatusHistory)).all()),
        len(db_session.exec(select(PatientLocationHistory)).all()),
    )
    seed_database(db_session)
    after = (
        len(db_session.exec(select(PatientTransferRequest)).all()),
        len(db_session.exec(select(PatientTransferRequestStatusHistory)).all()),
        len(db_session.exec(select(PatientLocationHistory)).all()),
    )
    assert before == after


def test_nutritionist_outside_assigned_services_is_allowed_and_marked_as_coverage(
    client, db_session
) -> None:
    auth = authenticate(client, "nutricionista")
    admission, _ = create_admission_in(client, db_session, auth, "UTI")
    created = client.post(
        "/api/v1/transfer-requests",
        headers=headers(auth),
        json={
            "admission_id": admission["id"],
            "destination_service_id": str(service(db_session, "MED").id),
            "transfer_mode": "reception_tray",
            "reason": "Cobertura ficticia fuera de asignación habitual.",
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["has_coverage_support"] is True
    assert all(item["is_coverage"] for item in created.json()["status_history"])


def test_two_requests_competing_for_same_destination_bed_leave_one_winner(
    client, db_session
) -> None:
    auth = authenticate(client)
    first_admission, first = create_tray(client, db_session, auth)
    second_admission, second = create_tray(client, db_session, auth)
    for transfer in (first, second):
        accepted = client.post(
            f"/api/v1/transfer-requests/{transfer['id']}/accept",
            headers=headers(auth),
            json={"destination_care_unit_id": None},
        )
        assert accepted.status_code == 200
    target = available_beds(db_session, "UCI")[0]
    winner = client.post(
        f"/api/v1/transfer-requests/{first['id']}/assign-bed",
        headers=headers(auth),
        json={"destination_care_unit_id": str(target.id)},
    )
    loser = client.post(
        f"/api/v1/transfer-requests/{second['id']}/assign-bed",
        headers=headers(auth),
        json={"destination_care_unit_id": str(target.id)},
    )
    assert winner.status_code == 200
    assert loser.status_code == 409
    assert client.get(f"/api/v1/transfer-requests/{second['id']}").json()["status"] == "pending_bed"
    current = db_session.exec(
        select(PatientLocationHistory).where(
            PatientLocationHistory.care_unit_id == target.id,
            PatientLocationHistory.ended_at.is_(None),
        )
    ).one()
    assert current.admission_id == uuid.UUID(first_admission["id"])
    assert current.admission_id != uuid.UUID(second_admission["id"])


def test_structure_soft_delete_and_purge_return_transfer_domain_conflicts(
    client, db_session
) -> None:
    auth = authenticate(client)
    admission, origin_bed = create_admission_in(client, db_session, auth, "MED")
    created = client.post(
        "/api/v1/transfer-requests",
        headers=headers(auth),
        json={
            "admission_id": admission["id"],
            "destination_service_id": str(service(db_session, "UCI").id),
            "transfer_mode": "reception_tray",
            "reason": "Solicitud para probar protecciones estructurales.",
        },
    ).json()
    blocked_service = client.patch(
        f"/api/v1/hospital/services/{service(db_session, 'UCI').id}",
        headers=headers(auth),
        json={"is_active": False},
    )
    assert blocked_service.status_code == 409
    assert "traslados abiertos" in blocked_service.json()["detail"]
    blocked_bed = client.patch(
        f"/api/v1/hospital/care-units/{origin_bed.id}",
        headers=headers(auth),
        json={"is_active": False},
    )
    assert blocked_bed.status_code == 409
    assert "ubicación vigente" in blocked_bed.json()["detail"]

    assert client.post(
        f"/api/v1/transfer-requests/{created['id']}/cancel",
        headers=headers(auth),
        json={"reason": "Cierre ficticio de la solicitud."},
    ).status_code == 200
    assert client.patch(
        f"/api/v1/admissions/{admission['id']}/status",
        headers=headers(auth),
        json={"status": "closed", "reason": "Cierre administrativo ficticio."},
    ).status_code == 200
    assert client.patch(
        f"/api/v1/hospital/care-units/{origin_bed.id}",
        headers=headers(auth),
        json={"is_active": False},
    ).status_code == 200

    client.cookies.clear()
    admin = authenticate(client, "administrador")
    purged = client.request(
        "DELETE",
        f"/api/v1/hospital/care-units/{origin_bed.id}",
        headers=headers(admin),
        json={"reason": "Intento de purga ficticio."},
    )
    assert purged.status_code == 409
    assert "historial de traslados" in purged.json()["detail"]
