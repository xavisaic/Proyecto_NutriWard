import uuid
from datetime import datetime, timezone

from sqlmodel import func, select

from app.core.config import settings
from app.models.admission import Admission
from app.models.admission_status_history import AdmissionStatusHistory
from app.models.audit_log import AuditLog
from app.models.care_unit import CareUnit
from app.models.patient import Patient
from app.models.patient_location_history import PatientLocationHistory


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


def create_identified(client, auth, rut: str = "12.345.678-5") -> dict:
    response = client.post(
        "/api/v1/patients",
        headers=headers(auth),
        json={
            "rut": rut,
            "given_names": "Persona",
            "first_surname": "Prueba",
            "second_surname": "Clínica",
            "date_of_birth": "1985-03-10",
            "sex": "female",
            "hospital_identifier": "TEST-HOSP-001",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_nn(client, auth, description: str = "Paciente NN de prueba") -> dict:
    response = client.post(
        "/api/v1/patients/unidentified",
        headers=headers(auth),
        json={"provisional_description": description, "sex": "unknown"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def available_beds(client) -> list[dict]:
    structure = client.get("/api/v1/hospital/structure").json()
    return [
        care_unit
        for service in structure["items"]
        for room in service["rooms"]
        for care_unit in room["care_units"]
        if care_unit["unit_type"] == "bed"
    ]


def test_create_identified_patient_normalizes_rut_and_rejects_duplicates(client) -> None:
    auth = authenticate(client)
    patient = create_identified(client, auth)
    assert patient["rut"] == "12345678-5"
    assert patient["identity_status"] == "identified"
    assert patient["temporary_identifier"] is None

    duplicate = client.post(
        "/api/v1/patients",
        headers=headers(auth),
        json={
            "rut": "12345678-5",
            "given_names": "Otra",
            "first_surname": "Persona",
        },
    )
    assert duplicate.status_code == 409

    invalid = client.post(
        "/api/v1/patients",
        headers=headers(auth),
        json={"rut": "12345678-9", "given_names": "RUT", "first_surname": "Inválido"},
    )
    assert invalid.status_code == 422


def test_two_nn_have_distinct_identifiers_and_are_searchable(client) -> None:
    auth = authenticate(client, "nutricionista")
    first = create_nn(client, auth, "Primer NN")
    second = create_nn(client, auth, "Segundo NN")
    assert first["temporary_identifier"].startswith("NN-")
    assert second["temporary_identifier"].startswith("NN-")
    assert first["temporary_identifier"] != second["temporary_identifier"]

    result = client.get(f"/api/v1/patients?q={first['temporary_identifier']}")
    assert result.status_code == 200
    assert [item["id"] for item in result.json()["items"]] == [first["id"]]


def test_nn_accepts_reported_name_and_estimated_age(client) -> None:
    auth = authenticate(client, "nutricionista")
    today = datetime.now(timezone.utc).date()
    response = client.post(
        "/api/v1/patients/unidentified",
        headers=headers(auth),
        json={
            "given_names": "  Nombre   informado ",
            "first_surname": "Apellido",
            "second_surname": "Provisorio",
            "age_years": 47,
            "hospital_identifier": "FICHA-NN-047",
        },
    )
    assert response.status_code == 201, response.text
    patient = response.json()
    assert patient["identity_status"] == "unidentified"
    assert patient["given_names"] == "Nombre informado"
    assert patient["first_surname"] == "Apellido"
    assert patient["second_surname"] == "Provisorio"
    assert patient["date_of_birth"] == today.replace(year=today.year - 47).isoformat()
    assert patient["date_of_birth_is_estimated"] is True
    assert "age_years" not in patient

    identified = client.patch(
        f"/api/v1/patients/{patient['id']}/identity",
        headers=headers(auth),
        json={
            "rut": "10.000.004-0",
            "given_names": "Nombre confirmado",
            "first_surname": "Apellido",
        },
    )
    assert identified.status_code == 200, identified.text
    assert identified.json()["hospital_identifier"] == "FICHA-NN-047"
    assert identified.json()["date_of_birth"] == patient["date_of_birth"]
    assert identified.json()["date_of_birth_is_estimated"] is True

    invalid_age = client.post(
        "/api/v1/patients/unidentified",
        headers=headers(auth),
        json={"age_years": 131},
    )
    assert invalid_age.status_code == 422


def test_hospital_identifier_is_unique_for_all_patient_creation_paths(client) -> None:
    auth = authenticate(client)
    identified = create_identified(client, auth, rut="10.000.001-6")
    assert identified["hospital_identifier"] == "TEST-HOSP-001"

    duplicate_nn = client.post(
        "/api/v1/patients/unidentified",
        headers=headers(auth),
        json={"hospital_identifier": "TEST-HOSP-001"},
    )
    assert duplicate_nn.status_code == 409
    assert duplicate_nn.json()["detail"] == "El número de ficha ya pertenece a otro paciente."

    duplicate_identified = client.post(
        "/api/v1/patients",
        headers=headers(auth),
        json={
            "rut": "10.000.002-4",
            "given_names": "Otra",
            "first_surname": "Persona",
            "hospital_identifier": "TEST-HOSP-001",
        },
    )
    assert duplicate_identified.status_code == 409

    second = create_nn(client, auth, "Paciente a identificar")
    duplicate_update = client.patch(
        f"/api/v1/patients/{second['id']}/identity",
        headers=headers(auth),
        json={
            "rut": "10.000.003-2",
            "given_names": "Identidad",
            "first_surname": "Duplicada",
            "hospital_identifier": "TEST-HOSP-001",
        },
    )
    assert duplicate_update.status_code == 409


def test_hospital_identifier_is_normalized_and_potential_matches_prevent_duplicates(client) -> None:
    auth = authenticate(client)
    created = client.post(
        "/api/v1/patients",
        headers=headers(auth),
        json={
            "rut": "12.345.678-5",
            "given_names": "María Elena",
            "first_surname": "Contreras",
            "hospital_identifier": "  ficha-ab-42 ",
        },
    )
    assert created.status_code == 201, created.text
    patient = created.json()
    assert patient["hospital_identifier"] == "FICHA-AB-42"

    by_identifier = client.get(
        "/api/v1/patients/potential-matches",
        params={"hospital_identifier": "ficha-ab-42"},
    )
    assert by_identifier.status_code == 200
    assert [item["id"] for item in by_identifier.json()["items"]] == [patient["id"]]

    by_name = client.get(
        "/api/v1/patients/potential-matches",
        params={"given_names": "María", "first_surname": "Contreras"},
    )
    assert by_name.status_code == 200
    assert patient["id"] in {item["id"] for item in by_name.json()["items"]}

    duplicate = client.post(
        "/api/v1/patients/unidentified",
        headers=headers(auth),
        json={"hospital_identifier": "ficha-ab-42"},
    )
    assert duplicate.status_code == 409

    client.cookies.clear()
    authenticate(client, "alimentacion")
    assert client.get(
        "/api/v1/patients/potential-matches",
        params={"hospital_identifier": "FICHA-AB-42"},
    ).status_code == 403


def test_admission_location_transfer_and_end_preserve_history(client, db_session) -> None:
    auth = authenticate(client)
    patient = create_nn(client, auth)
    occupied_ids = {
        str(value)
        for value in db_session.exec(
            select(PatientLocationHistory.care_unit_id).where(
                PatientLocationHistory.ended_at.is_(None)
            )
        ).all()
    }
    beds = [bed for bed in available_beds(client) if bed["id"] not in occupied_ids]
    first_bed, second_bed = beds[:2]

    created = client.post(
        "/api/v1/admissions",
        headers=headers(auth),
        json={"patient_id": patient["id"], "care_unit_id": first_bed["id"]},
    )
    assert created.status_code == 201, created.text
    admission = created.json()
    assert admission["status"] == "active"
    assert admission["current_location"]["care_unit_id"] == first_bed["id"]
    assert admission["status_history"][0]["to_status"] == "active"

    duplicate = client.post(
        "/api/v1/admissions",
        headers=headers(auth),
        json={"patient_id": patient["id"]},
    )
    assert duplicate.status_code == 409

    transferred = client.post(
        f"/api/v1/admissions/{admission['id']}/location",
        headers=headers(auth),
        json={"care_unit_id": second_bed["id"], "reason": "Cambio de sala clínico."},
    )
    assert transferred.status_code == 201, transferred.text
    history = client.get(
        f"/api/v1/admissions/{admission['id']}/location-history"
    ).json()
    assert len(history) == 2
    assert history[0]["ended_at"] is not None
    assert history[1]["ended_at"] is None

    ended = client.patch(
        f"/api/v1/admissions/{admission['id']}/status",
        headers=headers(auth),
        json={"status": "discharged", "reason": "Alta médica de prueba."},
    )
    assert ended.status_code == 200, ended.text
    assert ended.json()["current_location"] is None
    assert ended.json()["status_history"][-1]["to_status"] == "discharged"

    next_patient = create_nn(client, auth, "Paciente que usa cama liberada")
    reused = client.post(
        "/api/v1/admissions",
        headers=headers(auth),
        json={"patient_id": next_patient["id"], "care_unit_id": second_bed["id"]},
    )
    assert reused.status_code == 201
    actions = set(
        db_session.exec(
            select(AuditLog.action).where(
                AuditLog.admission_id == uuid.UUID(admission["id"])
            )
        ).all()
    )
    assert {
        "admission_created",
        "location_assigned",
        "location_closed_for_transfer",
        "location_transferred",
        "location_closed_on_admission_end",
        "admission_status_changed",
    }.issubset(actions)


def test_occupied_bed_and_non_bed_are_rejected(client, db_session) -> None:
    auth = authenticate(client)
    patient = create_nn(client, auth)
    occupied = db_session.exec(
        select(PatientLocationHistory).where(PatientLocationHistory.ended_at.is_(None))
    ).first()
    response = client.post(
        "/api/v1/admissions",
        headers=headers(auth),
        json={"patient_id": patient["id"], "care_unit_id": str(occupied.care_unit_id)},
    )
    assert response.status_code == 409
    assert db_session.exec(
        select(Admission).where(Admission.patient_id == uuid.UUID(patient["id"]))
    ).first() is None

    non_bed = db_session.exec(select(CareUnit).where(CareUnit.unit_type != "bed")).first()
    if non_bed is None:
        bed = db_session.exec(select(CareUnit)).first()
        non_bed = CareUnit(room_id=bed.room_id, code="TEST-ST", unit_type="stretcher")
        db_session.add(non_bed)
        db_session.commit()
        db_session.refresh(non_bed)
    response = client.post(
        "/api/v1/admissions",
        headers=headers(auth),
        json={"patient_id": patient["id"], "care_unit_id": str(non_bed.id)},
    )
    assert response.status_code == 400


def test_identification_preserves_active_admission_and_location(client) -> None:
    auth = authenticate(client)
    patient = create_nn(client, auth)
    admission = client.post(
        "/api/v1/admissions",
        headers=headers(auth),
        json={"patient_id": patient["id"]},
    ).json()
    identified = client.patch(
        f"/api/v1/patients/{patient['id']}/identity",
        headers=headers(auth),
        json={
            "rut": "10.000.000-8",
            "given_names": "Identidad",
            "first_surname": "Confirmada",
            "sex": "female",
        },
    )
    assert identified.status_code == 200, identified.text
    body = identified.json()
    assert body["identity_status"] == "identified"
    assert body["temporary_identifier"] == patient["temporary_identifier"]
    assert body["active_admission"]["id"] == admission["id"]


def test_existing_rut_requires_reconciliation_and_moves_history(client, db_session) -> None:
    auth = authenticate(client)
    canonical = create_identified(client, auth)
    previous_admission = client.post(
        "/api/v1/admissions",
        headers=headers(auth),
        json={"patient_id": canonical["id"]},
    ).json()
    ended = client.patch(
        f"/api/v1/admissions/{previous_admission['id']}/status",
        headers=headers(auth),
        json={"status": "discharged", "reason": "Alta previa verificada."},
    )
    assert ended.status_code == 200
    provisional = create_nn(client, auth)
    occupied_ids = set(
        db_session.exec(
            select(PatientLocationHistory.care_unit_id).where(
                PatientLocationHistory.ended_at.is_(None)
            )
        ).all()
    )
    bed = next(
        candidate
        for candidate in db_session.exec(
            select(CareUnit).where(CareUnit.unit_type == "bed", CareUnit.is_active.is_(True))
        ).all()
        if candidate.id not in occupied_ids
    )
    admission = client.post(
        "/api/v1/admissions",
        headers=headers(auth),
        json={"patient_id": provisional["id"], "care_unit_id": str(bed.id)},
    ).json()
    conflict = client.patch(
        f"/api/v1/patients/{provisional['id']}/identity",
        headers=headers(auth),
        json={
            "rut": canonical["rut"],
            "given_names": "Persona",
            "first_surname": "Prueba",
        },
    )
    assert conflict.status_code == 409

    reconciled = client.post(
        f"/api/v1/patients/{provisional['id']}/reconcile",
        headers=headers(auth),
        json={
            "rut": canonical["rut"],
            "reason": "Coincidencia confirmada mediante antecedentes institucionales.",
        },
    )
    assert reconciled.status_code == 200, reconciled.text
    body = reconciled.json()
    assert body["id"] == canonical["id"]
    assert body["active_admission"]["id"] == admission["id"]
    assert body["active_admission"]["current_location"]["care_unit_id"] == str(bed.id)
    assert {item["id"] for item in body["admissions"]} == {
        previous_admission["id"],
        admission["id"],
    }
    source = db_session.get(Patient, uuid.UUID(provisional["id"]))
    assert source.merged_into_patient_id == uuid.UUID(canonical["id"])
    assert source.is_active is False
    assert source.merge_reason == "Coincidencia confirmada mediante antecedentes institucionales."
    moved_admission = db_session.get(Admission, uuid.UUID(admission["id"]))
    assert moved_admission.patient_id == uuid.UUID(canonical["id"])
    audit = db_session.exec(
        select(AuditLog).where(
            AuditLog.action == "patient_reconciled",
            AuditLog.entity_id == source.id,
        )
    ).one()
    assert audit.after_state["canonical_patient_id"] == canonical["id"]
    assert audit.after_state["moved_admission_ids"] == [admission["id"]]


def test_incompatible_reconciliation_rolls_back(client, db_session) -> None:
    auth = authenticate(client)
    canonical = create_identified(client, auth)
    provisional = create_nn(client, auth)
    first_admission = client.post(
        "/api/v1/admissions",
        headers=headers(auth),
        json={"patient_id": canonical["id"]},
    )
    second_admission = client.post(
        "/api/v1/admissions",
        headers=headers(auth),
        json={"patient_id": provisional["id"]},
    )
    assert first_admission.status_code == second_admission.status_code == 201
    response = client.post(
        f"/api/v1/patients/{provisional['id']}/reconcile",
        headers=headers(auth),
        json={
            "rut": canonical["rut"],
            "reason": "Coincidencia confirmada mediante antecedentes institucionales.",
        },
    )
    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Ambas fichas tienen hospitalizaciones activas; la conciliación no puede continuar."
    )
    db_session.expire_all()
    source = db_session.get(Patient, uuid.UUID(provisional["id"]))
    assert source.is_active is True
    assert source.merged_into_patient_id is None
    assert db_session.exec(
        select(func.count())
        .select_from(Admission)
        .where(Admission.patient_id == source.id)
    ).one() == 1
    assert db_session.exec(
        select(AuditLog).where(
            AuditLog.action == "patient_reconciled",
            AuditLog.entity_id == source.id,
        )
    ).first() is None


def test_jefatura_resolves_two_active_admissions_as_administrative_duplicate(
    client,
    db_session,
) -> None:
    manager = authenticate(client, "jefatura")
    canonical = create_identified(client, manager)
    source = create_nn(client, manager)
    occupied_ids = set(
        db_session.exec(
            select(PatientLocationHistory.care_unit_id).where(
                PatientLocationHistory.ended_at.is_(None)
            )
        ).all()
    )
    beds = [
        bed
        for bed in db_session.exec(
            select(CareUnit).where(
                CareUnit.unit_type == "bed",
                CareUnit.is_active.is_(True),
            )
        ).all()
        if bed.id not in occupied_ids
    ]
    assert len(beds) >= 2
    canonical_admission = client.post(
        "/api/v1/admissions",
        headers=headers(manager),
        json={"patient_id": canonical["id"], "care_unit_id": str(beds[0].id)},
    ).json()
    source_admission = client.post(
        "/api/v1/admissions",
        headers=headers(manager),
        json={"patient_id": source["id"], "care_unit_id": str(beds[1].id)},
    ).json()

    client.cookies.clear()
    nutritionist = authenticate(client, "nutricionista")
    forbidden = client.post(
        f"/api/v1/patients/{source['id']}/reconcile-active-conflict",
        headers=headers(nutritionist),
        json={
            "rut": canonical["rut"],
            "reason": "Duplicidad confirmada por revisión institucional.",
            "admission_to_close_id": canonical_admission["id"],
        },
    )
    assert forbidden.status_code == 403

    client.cookies.clear()
    manager = authenticate(client, "jefatura")
    resolved = client.post(
        f"/api/v1/patients/{source['id']}/reconcile-active-conflict",
        headers=headers(manager),
        json={
            "rut": canonical["rut"],
            "reason": "Duplicidad confirmada por revisión institucional.",
            "admission_to_close_id": canonical_admission["id"],
        },
    )
    assert resolved.status_code == 200, resolved.text
    body = resolved.json()
    assert body["id"] == canonical["id"]
    assert body["active_admission"]["id"] == source_admission["id"]
    admissions = {item["id"]: item for item in body["admissions"]}
    closed = admissions[canonical_admission["id"]]
    assert closed["status"] == "closed"
    assert closed["end_reason"].startswith("Duplicidad administrativa:")
    assert closed["current_location"] is None
    assert closed["location_history"][0]["ended_at"] is not None

    db_session.expire_all()
    source_row = db_session.get(Patient, uuid.UUID(source["id"]))
    assert source_row.is_active is False
    assert source_row.merged_into_patient_id == uuid.UUID(canonical["id"])
    moved = db_session.get(Admission, uuid.UUID(source_admission["id"]))
    assert moved.patient_id == uuid.UUID(canonical["id"])
    assert moved.status == "active"
    administratively_closed = db_session.get(
        Admission,
        uuid.UUID(canonical_admission["id"]),
    )
    assert administratively_closed.status == "closed"
    history = db_session.exec(
        select(AdmissionStatusHistory).where(
            AdmissionStatusHistory.admission_id == administratively_closed.id,
            AdmissionStatusHistory.to_status == "closed",
        )
    ).one()
    assert history.reason.startswith("Duplicidad administrativa:")
    assert db_session.exec(
        select(AuditLog).where(
            AuditLog.action == "duplicate_admission_closed_for_reconciliation",
            AuditLog.entity_id == administratively_closed.id,
        )
    ).one()


def test_roles_csrf_audit_and_openapi(client, db_session) -> None:
    assert client.get("/api/v1/patients").status_code == 401
    food_auth = authenticate(client, "alimentacion")
    assert client.get("/api/v1/patients").status_code == 403
    client.cookies.clear()

    administrator = authenticate(client, "administrador")
    assert client.get("/api/v1/patients").status_code == 200
    assert client.post(
        "/api/v1/patients/unidentified",
        headers=headers(administrator),
        json={"provisional_description": "Intento administrativo"},
    ).status_code == 403
    client.cookies.clear()

    nutritionist = authenticate(client, "nutricionista")
    assert client.post(
        "/api/v1/patients/unidentified",
        json={"provisional_description": "Sin CSRF"},
    ).status_code == 403
    patient = create_nn(client, nutritionist, "Paciente auditado")
    audit = db_session.exec(
        select(AuditLog).where(
            AuditLog.entity_type == "patient",
            AuditLog.entity_id == uuid.UUID(patient["id"]),
        )
    ).first()
    assert audit is not None
    assert audit.actor_user_id == uuid.UUID(nutritionist["user"]["id"])
    assert audit.after_state["temporary_identifier"] == patient["temporary_identifier"]

    paths = client.get("/openapi.json").json()["paths"]
    expected = {
        "/api/v1/patients",
        "/api/v1/patients/unidentified",
        "/api/v1/patients/{patient_id}",
        "/api/v1/patients/{patient_id}/identity",
        "/api/v1/patients/{patient_id}/reconcile",
        "/api/v1/patients/{patient_id}/reconcile-active-conflict",
        "/api/v1/patients/potential-matches",
        "/api/v1/admissions",
        "/api/v1/admissions/active",
        "/api/v1/admissions/{admission_id}",
        "/api/v1/admissions/{admission_id}/status",
        "/api/v1/patients/{patient_id}/admissions",
        "/api/v1/admissions/{admission_id}/location",
        "/api/v1/admissions/{admission_id}/location-history",
    }
    assert expected.issubset(paths)
