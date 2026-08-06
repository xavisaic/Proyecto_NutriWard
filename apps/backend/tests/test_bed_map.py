import uuid
from datetime import date, datetime, timezone

from sqlalchemy import event
from sqlmodel import Session, select

from app.core.config import settings
from app.models.admission import Admission
from app.models.audit_log import AuditLog
from app.models.care_unit import CareUnit
from app.models.care_unit_layout_position import CareUnitLayoutPosition
from app.models.hospital_service import HospitalService
from app.models.patient import Patient
from app.models.patient_location_history import PatientLocationHistory
from app.models.room import Room
from app.services.bed_map_service import get_bed_map


def authenticate(client, role: str) -> dict:
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": f"{role}@nutriward.local",
            "password": settings.demo_user_password,
        },
    )
    assert response.status_code == 200
    return response.json()


def service_id(db_session, code: str = "MED") -> uuid.UUID:
    return db_session.exec(
        select(HospitalService.id).where(HospitalService.code == code)
    ).one()


def endpoint(client, db_session, code: str = "MED"):
    return client.get(f"/api/v1/bed-map?service_id={service_id(db_session, code)}")


def create_occupied_bed(
    db_session,
    *,
    room: Room,
    bed_code: str,
    patient: Patient,
    admission_identifier: str,
    layout: tuple[int, int, int, int] | None = None,
    admission_status: str = "active",
    location_ended_at: datetime | None = None,
) -> CareUnit:
    bed = CareUnit(room_id=room.id, code=bed_code, label=f"Cama {bed_code}", unit_type="bed")
    db_session.add(bed)
    db_session.flush()
    if layout:
        db_session.add(
            CareUnitLayoutPosition(
                care_unit_id=bed.id,
                grid_x=layout[0],
                grid_y=layout[1],
                width=layout[2],
                height=layout[3],
            )
        )
    admission = Admission(
        patient_id=patient.id,
        admission_identifier=admission_identifier,
        status=admission_status,
        admitted_at=datetime(2026, 8, 1, 10, 0, tzinfo=timezone.utc),
        ended_at=(
            datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)
            if admission_status != "active"
            else None
        ),
    )
    db_session.add(admission)
    db_session.flush()
    db_session.add(
        PatientLocationHistory(
            admission_id=admission.id,
            care_unit_id=bed.id,
            ended_at=location_ended_at,
        )
    )
    db_session.commit()
    return bed


def test_requires_authentication_and_allows_all_operational_roles(client, db_session) -> None:
    target = service_id(db_session)
    assert client.get(f"/api/v1/bed-map?service_id={target}").status_code == 401

    for role in ("administrador", "jefatura", "nutricionista", "alimentacion"):
        client.cookies.clear()
        authenticate(client, role)
        response = client.get(f"/api/v1/bed-map?service_id={target}")
        assert response.status_code == 200, (role, response.text)
        assert "X-CSRF-Token" not in response.request.headers


def test_food_role_keeps_general_patient_and_admission_endpoints_forbidden(
    client, db_session
) -> None:
    authenticate(client, "alimentacion")
    assert endpoint(client, db_session).status_code == 200
    patient = db_session.exec(select(Patient)).first()
    admission = db_session.exec(select(Admission)).first()
    for path in (
        "/api/v1/patients",
        f"/api/v1/patients/{patient.id}",
        "/api/v1/admissions/active",
        f"/api/v1/admissions/{admission.id}",
    ):
        assert client.get(path).status_code == 403, path


def test_service_parameter_validation_and_active_service_requirement(client, db_session) -> None:
    authenticate(client, "jefatura")
    assert client.get("/api/v1/bed-map").status_code == 422
    assert client.get("/api/v1/bed-map?service_id=not-a-uuid").status_code == 422
    assert client.get(f"/api/v1/bed-map?service_id={uuid.uuid4()}").status_code == 404

    inactive = db_session.exec(
        select(HospitalService).where(HospitalService.code == "CIR")
    ).one()
    inactive.is_active = False
    db_session.add(inactive)
    db_session.commit()
    assert client.get(f"/api/v1/bed-map?service_id={inactive.id}").status_code == 404


def test_filters_inactive_rooms_and_non_active_non_bed_units(client, db_session) -> None:
    authenticate(client, "administrador")
    service = db_session.exec(
        select(HospitalService).where(HospitalService.code == "MED")
    ).one()
    active_empty = Room(
        service_id=service.id,
        code="EMPTY",
        name="Sala sin camas",
        floor="3",
    )
    inactive_room = Room(
        service_id=service.id,
        code="INACTIVE",
        name="Sala inactiva",
        is_active=False,
    )
    db_session.add(active_empty)
    db_session.add(inactive_room)
    db_session.flush()
    db_session.add(CareUnit(room_id=active_empty.id, code="BOX", unit_type="box"))
    db_session.add(CareUnit(room_id=active_empty.id, code="ST", unit_type="stretcher"))
    db_session.add(CareUnit(room_id=active_empty.id, code="POST", unit_type="station"))
    db_session.add(CareUnit(room_id=active_empty.id, code="OFF", unit_type="bed", is_active=False))
    db_session.add(CareUnit(room_id=inactive_room.id, code="01", unit_type="bed"))
    db_session.commit()

    body = endpoint(client, db_session).json()
    assert "EMPTY" in [room["code"] for room in body["rooms"]]
    assert "INACTIVE" not in [room["code"] for room in body["rooms"]]
    empty = next(room for room in body["rooms"] if room["code"] == "EMPTY")
    assert empty["beds"] == []


def test_free_occupied_historical_and_ended_admission_rules(client, db_session) -> None:
    authenticate(client, "nutricionista")
    room = db_session.exec(select(Room).where(Room.code == "A102")).one()
    identified = Patient(
        identity_status="identified",
        rut="33333333-3",
        given_names="Ana María",
        first_surname="Pérez",
        second_surname="Soto",
        date_of_birth=date(2000, 8, 2),
    )
    historical_patient = Patient(
        identity_status="provisional",
        temporary_identifier="PROV-HIST",
        given_names="Nombre Provisorio",
    )
    ended_patient = Patient(
        identity_status="unidentified",
        temporary_identifier="NN-ENDED",
    )
    db_session.add(identified)
    db_session.add(historical_patient)
    db_session.add(ended_patient)
    db_session.flush()
    occupied = create_occupied_bed(
        db_session,
        room=room,
        bed_code="20",
        patient=identified,
        admission_identifier="ADM-MAP-OCCUPIED",
        layout=(4, 2, 2, 1),
    )
    historical = create_occupied_bed(
        db_session,
        room=room,
        bed_code="21",
        patient=historical_patient,
        admission_identifier="ADM-MAP-HISTORICAL",
        location_ended_at=datetime(2026, 8, 1, 11, 0, tzinfo=timezone.utc),
    )
    ended = create_occupied_bed(
        db_session,
        room=room,
        bed_code="22",
        patient=ended_patient,
        admission_identifier="ADM-MAP-ENDED",
        admission_status="discharged",
    )

    body = endpoint(client, db_session).json()
    beds = {bed["id"]: bed for room_item in body["rooms"] for bed in room_item["beds"]}
    occupied_body = beds[str(occupied.id)]
    assert occupied_body["status"] == "occupied"
    assert occupied_body["layout"] == {"grid_x": 4, "grid_y": 2, "width": 2, "height": 1}
    assert occupied_body["occupancy"]["patient"] == {
        "id": str(identified.id),
        "display_name": "Ana María Pérez Soto",
        "identity_status": "identified",
        "age_years": date.today().year - 2000 - (date.today() < date(date.today().year, 8, 2)),
        "age_is_estimated": False,
    }
    assert beds[str(historical.id)]["status"] == "free"
    assert beds[str(historical.id)]["occupancy"] is None
    assert beds[str(ended.id)]["status"] == "free"
    assert beds[str(ended.id)]["occupancy"] is None


def test_identity_names_age_variants_missing_layout_and_privacy(client, db_session) -> None:
    authenticate(client, "alimentacion")
    room = db_session.exec(select(Room).where(Room.code == "A102")).one()
    people = [
        Patient(
            identity_status="provisional",
            temporary_identifier="PROV-NAMED",
            given_names="Nombre",
            first_surname="Disponible",
            date_of_birth=date(1990, 1, 1),
            date_of_birth_is_estimated=True,
            phone="+56 9 0000 0000",
        ),
        Patient(identity_status="provisional", temporary_identifier="PROV-NONAME"),
        Patient(identity_status="unidentified", temporary_identifier="NN-MAP"),
        Patient(
            identity_status="unidentified",
            temporary_identifier="NN-NAMED",
            given_names="Nombre",
            first_surname="Informado",
        ),
    ]
    db_session.add_all(people)
    db_session.flush()
    beds = [
        create_occupied_bed(
            db_session,
            room=room,
            bed_code=str(30 + index),
            patient=patient,
            admission_identifier=f"ADM-MAP-IDENTITY-{index}",
        )
        for index, patient in enumerate(people)
    ]

    response = endpoint(client, db_session)
    payload = response.json()
    by_id = {
        bed["id"]: bed
        for room_item in payload["rooms"]
        for bed in room_item["beds"]
    }
    assert by_id[str(beds[0].id)]["occupancy"]["patient"]["display_name"] == "Nombre Disponible"
    assert by_id[str(beds[0].id)]["occupancy"]["patient"]["age_is_estimated"] is True
    assert by_id[str(beds[1].id)]["occupancy"]["patient"]["display_name"] == (
        "Paciente provisorio · PROV-NONAME"
    )
    nn = by_id[str(beds[2].id)]["occupancy"]["patient"]
    assert nn["display_name"] == "Paciente NN · NN-MAP"
    assert nn["age_years"] is None
    named_nn = by_id[str(beds[3].id)]["occupancy"]["patient"]
    assert named_nn["display_name"] == "Nombre Informado · NN-NAMED"
    assert all(by_id[str(bed.id)]["layout"] is None for bed in beds)
    serialized = response.text.lower()
    for forbidden in (
        "rut",
        "phone",
        "date_of_birth",
        "hospital_identifier",
        "location_history",
        "status_history",
        "provisional_description",
        "audit",
    ):
        assert forbidden not in serialized


def test_deterministic_room_and_bed_order(client, db_session) -> None:
    authenticate(client, "jefatura")
    service = db_session.exec(select(HospitalService).where(HospitalService.code == "UTI")).one()
    first_room = db_session.exec(select(Room).where(Room.service_id == service.id)).one()
    second_room = Room(service_id=service.id, code="AAA", name="Última por código")
    db_session.add(second_room)
    db_session.flush()
    definitions = [
        ("Z-NOPOS", None),
        ("B", (3, 1, 1, 1)),
        ("A", (5, 0, 1, 1)),
        ("C", (1, 1, 1, 1)),
        ("A-NOPOS", None),
    ]
    for code, layout in definitions:
        bed = CareUnit(room_id=first_room.id, code=code, unit_type="bed")
        db_session.add(bed)
        db_session.flush()
        if layout:
            db_session.add(
                CareUnitLayoutPosition(
                    care_unit_id=bed.id,
                    grid_x=layout[0],
                    grid_y=layout[1],
                    width=layout[2],
                    height=layout[3],
                )
            )
    db_session.commit()

    body = endpoint(client, db_session, "UTI").json()
    assert [room["code"] for room in body["rooms"]] == ["AAA", "UTI-A"]
    target = next(room for room in body["rooms"] if room["code"] == "UTI-A")
    codes = [bed["code"] for bed in target["beds"]]
    assert codes.index("A") < codes.index("C") < codes.index("B")
    assert codes[-2:] == ["A-NOPOS", "Z-NOPOS"]
    assert body["generated_at"]


def test_openapi_and_fixed_query_plan(client, db_session, database_engine) -> None:
    authenticate(client, "administrador")
    operation = client.get("/openapi.json").json()["paths"]["/api/v1/bed-map"]["get"]
    assert operation["responses"]["200"]["content"]["application/json"]["schema"]
    assert any(parameter["name"] == "service_id" and parameter["required"] for parameter in operation["parameters"])

    statements: list[str] = []
    audit_count = len(db_session.exec(select(AuditLog)).all())

    def count_queries(*args):
        statements.append(args[2])

    event.listen(database_engine, "before_cursor_execute", count_queries)
    try:
        with Session(database_engine) as session:
            result = get_bed_map(session, service_id(session, "MED"))
        assert result.rooms
    finally:
        event.remove(database_engine, "before_cursor_execute", count_queries)
    assert len(statements) == 4  # service-id lookup plus the service's fixed three-query plan
    assert all(statement.lstrip().upper().startswith("SELECT") for statement in statements)
    db_session.expire_all()
    assert len(db_session.exec(select(AuditLog)).all()) == audit_count
