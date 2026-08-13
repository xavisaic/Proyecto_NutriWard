import uuid
from datetime import date, datetime, timezone

from sqlmodel import select

from app.core.config import settings
from app.models.admission import Admission
from app.models.patient import Patient


def authenticate(client, role: str = "nutricionista") -> dict:
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": f"{role}@nutriward.local",
            "password": settings.demo_user_password,
        },
    )
    assert response.status_code == 200
    return response.json()


def test_patient_chart_auth_roles_and_openapi(client) -> None:
    admission_id = uuid.uuid4()
    assert client.get(f"/api/v1/patients/{uuid.uuid4()}/chart-summary").status_code == 401
    assert client.get(
        f"/api/v1/admissions/{admission_id}/operational-timeline"
    ).status_code == 401

    for role in ("administrador", "jefatura", "nutricionista"):
        client.cookies.clear()
        authenticate(client, role)
        assert client.get(f"/api/v1/patients/{uuid.uuid4()}/chart-summary").status_code == 404

    client.cookies.clear()
    authenticate(client, "alimentacion")
    assert client.get(f"/api/v1/patients/{uuid.uuid4()}/chart-summary").status_code == 403
    assert client.get(
        f"/api/v1/admissions/{uuid.uuid4()}/operational-timeline"
    ).status_code == 403

    schema = client.get("/openapi.json").json()
    assert "/api/v1/patients/{patient_id}/chart-summary" in schema["paths"]
    assert "/api/v1/admissions/{admission_id}/operational-timeline" in schema["paths"]


def test_chart_selects_active_or_most_recent_and_rejects_foreign_episode(
    client, db_session
) -> None:
    authenticate(client)
    active = db_session.exec(select(Admission).where(Admission.status == "active")).first()
    assert active is not None
    response = client.get(f"/api/v1/patients/{active.patient_id}/chart-summary")
    assert response.status_code == 200
    assert response.json()["selected_admission"]["id"] == str(active.id)
    assert response.json()["selected_admission"]["is_historical"] is False

    patient = db_session.get(Patient, active.patient_id)
    assert patient is not None
    patient.date_of_birth = date.today()
    db_session.add(patient)
    db_session.commit()
    neonatal = client.get(f"/api/v1/patients/{patient.id}/chart-summary").json()
    assert neonatal["patient"]["current_age"]["unit"] == "days"

    foreign = db_session.exec(
        select(Admission).where(Admission.patient_id != active.patient_id)
    ).first()
    assert foreign is not None
    invalid = client.get(
        f"/api/v1/patients/{active.patient_id}/chart-summary",
        params={"admission_id": str(foreign.id)},
    )
    assert invalid.status_code == 404


def test_chart_supports_patient_without_admissions_and_historical_last_location(
    client, db_session
) -> None:
    authenticate(client)
    patient = Patient(
        identity_status="unidentified",
        temporary_identifier=f"NN-TEST-{uuid.uuid4().hex[:6].upper()}",
        date_of_birth_is_estimated=True,
    )
    db_session.add(patient)
    db_session.commit()
    empty = client.get(f"/api/v1/patients/{patient.id}/chart-summary")
    assert empty.status_code == 200
    assert empty.json()["selected_admission"] is None
    assert empty.json()["admissions"] == []

    historical = db_session.exec(
        select(Admission)
        .where(Admission.status != "active")
        .order_by(Admission.admitted_at.desc())
    ).first()
    assert historical is not None
    result = client.get(f"/api/v1/patients/{historical.patient_id}/chart-summary").json()
    selected = result["selected_admission"]
    assert selected["is_historical"] is True
    if selected["location"]:
        assert selected["location"]["is_current"] is False
        assert selected["bed_status"] == "released"


def test_timeline_is_deterministic_paginated_and_episode_isolated(client, db_session) -> None:
    authenticate(client)
    admission = db_session.exec(select(Admission).order_by(Admission.admitted_at)).first()
    assert admission is not None
    url = f"/api/v1/admissions/{admission.id}/operational-timeline"
    first = client.get(url, params={"page": 1, "page_size": 2})
    second = client.get(url, params={"page": 1, "page_size": 2})
    assert first.status_code == 200
    assert first.json() == second.json()
    body = first.json()
    assert body["admission_id"] == str(admission.id)
    assert body["page"] == 1 and body["page_size"] == 2
    assert len(body["items"]) <= 2
    assert all("changed_by_user_id" not in item for item in body["items"])
    assert all("snapshot" not in str(item).lower() for item in body["items"])
    dates = [datetime.fromisoformat(item["occurred_at"]) for item in body["items"]]
    assert dates == sorted(dates, reverse=True)


def test_chart_does_not_expose_clinical_placeholders(client, db_session) -> None:
    authenticate(client)
    patient = db_session.exec(select(Patient)).first()
    assert patient is not None
    body = client.get(f"/api/v1/patients/{patient.id}/chart-summary").json()
    serialized = str(body).lower()
    assert "no disponible en nutriward" not in serialized
    assert "audit_log" not in serialized
    assert "prescription" not in serialized
