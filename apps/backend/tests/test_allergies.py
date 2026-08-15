import uuid
from datetime import datetime, timezone

from sqlmodel import select

from app.core.config import settings
from app.models.admission import Admission
from app.models.audit_log import AuditLog


def authenticate(client, role: str = "nutricionista") -> dict:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": f"{role}@nutriward.local", "password": settings.demo_user_password},
    )
    assert response.status_code == 200
    return response.json()


def active_admission(db_session) -> Admission:
    row = db_session.exec(select(Admission).where(Admission.status == "active")).first()
    assert row is not None
    return row


def headers(auth: dict) -> dict:
    return {"X-CSRF-Token": auth["csrf_token"]}


def allergy_payload() -> dict:
    return {
        "items": [
            {
                "substance_name": "Maní",
                "allergy_type": "allergy",
                "category": "food",
                "clinical_status": "active",
                "verification_status": "confirmed",
                "criticality": "high",
                "source": "patient",
                "note": "Dato clínico reservado",
                "reactions": [{"manifestation": "Anafilaxia", "severity": "severe", "note": "Reservado"}],
            },
            {
                "substance_name": "Penicilina",
                "allergy_type": "allergy",
                "category": "medication",
                "clinical_status": "active",
                "verification_status": "presumed",
                "criticality": "unable_to_assess",
                "source": "clinical_record",
                "reactions": [],
            },
        ]
    }


def test_permissions_openapi_and_minimal_food_projection(client, db_session) -> None:
    admission = active_admission(db_session)
    full_url = f"/api/v1/admissions/{admission.id}/allergy-intolerances"
    food_url = f"/api/v1/admissions/{admission.id}/food-safety-allergies"
    assert client.get(full_url).status_code == 401
    assert client.get(food_url).status_code == 401

    authenticate(client, "administrador")
    assert client.get(full_url).status_code == 403
    assert client.get(food_url).status_code == 403
    client.cookies.clear()

    authenticate(client, "alimentacion")
    assert client.get(full_url).status_code == 403
    projection = client.get(food_url)
    assert projection.status_code == 200
    assert projection.json() == {
        "admission_id": str(admission.id), "review_status": "not_reviewed", "items": []
    }
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/v1/admissions/{admission_id}/allergy-intolerances" in paths
    assert "/api/v1/admissions/{admission_id}/food-safety-allergies" in paths

    client.cookies.clear()
    authenticate(client, "jefatura")
    assert client.get(full_url).status_code == 200
    assert client.get(food_url).status_code == 200


def test_bulk_create_longitudinal_reactions_and_food_privacy(client, db_session) -> None:
    admission = active_admission(db_session)
    auth = authenticate(client)
    created = client.post(
        f"/api/v1/admissions/{admission.id}/allergy-intolerances",
        headers=headers(auth),
        json=allergy_payload(),
    )
    assert created.status_code == 201, created.text
    assert len(created.json()) == 2
    assert created.json()[0]["history"][0]["reason"] == "Registro inicial de alergia o intolerancia."
    assert created.json()[0]["reactions"][0]["manifestation"] == "Anafilaxia"

    duplicate = client.post(
        f"/api/v1/admissions/{admission.id}/allergy-intolerances",
        headers=headers(auth),
        json={"items": [{
            "substance_name": "  maní ", "category": "food", "source": "patient"
        }]},
    )
    assert duplicate.status_code == 409

    old = Admission(
        patient_id=admission.patient_id,
        admission_identifier=f"ADM-HIST-{uuid.uuid4().hex[:6]}",
        status="discharged",
        admitted_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        ended_at=datetime(2025, 1, 2, tzinfo=timezone.utc),
    )
    db_session.add(old)
    db_session.commit()
    historical = client.get(f"/api/v1/admissions/{old.id}/allergy-intolerances")
    assert {item["substance_name"] for item in historical.json()["items"]} == {"Maní", "Penicilina"}

    client.cookies.clear()
    authenticate(client, "alimentacion")
    food = client.get(f"/api/v1/admissions/{admission.id}/food-safety-allergies")
    assert food.status_code == 200
    body = food.json()
    assert body["review_status"] == "active_food_risks"
    assert [item["substance_name"] for item in body["items"]] == ["Maní"]
    serialized = food.text
    for forbidden in ("Penicilina", "Dato clínico reservado", "Reservado", "source", "created_by"):
        assert forbidden not in serialized


def test_status_history_versioning_reactions_and_no_delete(client, db_session) -> None:
    admission = active_admission(db_session)
    auth = authenticate(client)
    csrf = headers(auth)
    item = client.post(
        f"/api/v1/admissions/{admission.id}/allergy-intolerances",
        headers=csrf,
        json={"items": [{"substance_name": "Lactosa", "allergy_type": "intolerance", "category": "food", "source": "patient"}]},
    ).json()[0]
    updated = client.patch(
        f"/api/v1/allergy-intolerances/{item['id']}/status",
        headers=csrf,
        json={"version": 1, "clinical_status": "resolved", "verification_status": "confirmed", "criticality": "low", "source": "care_team", "reason": "Tolerancia documentada en evolución."},
    )
    assert updated.status_code == 200
    assert updated.json()["version"] == 2
    assert len(updated.json()["history"]) == 2
    stale = client.patch(
        f"/api/v1/allergy-intolerances/{item['id']}/status",
        headers=csrf,
        json={"version": 1, "clinical_status": "active", "verification_status": "confirmed", "criticality": "low", "source": "care_team", "reason": "Versión obsoleta."},
    )
    assert stale.status_code == 409
    reaction = client.post(
        f"/api/v1/allergy-intolerances/{item['id']}/reactions",
        headers=csrf,
        json={"manifestation": "Distensión abdominal", "severity": "moderate"},
    )
    assert reaction.status_code == 200
    assert len(reaction.json()["reactions"]) == 1
    entered_error = client.patch(
        f"/api/v1/allergy-intolerances/{item['id']}/status",
        headers=csrf,
        json={"version": 2, "clinical_status": None, "verification_status": "entered_in_error", "criticality": "low", "source": "clinical_record", "reason": "Paciente equivocado; se conserva trazabilidad."},
    )
    assert entered_error.status_code == 200
    assert entered_error.json()["clinical_status"] is None
    assert client.delete(f"/api/v1/allergy-intolerances/{item['id']}", headers=csrf).status_code in (404, 405)
    audits = db_session.exec(select(AuditLog).where(AuditLog.entity_id == uuid.UUID(item["id"]))).all()
    assert all("substance_name" not in (event.after_state or {}) for event in audits)
    assert all("manifestation" not in (event.after_state or {}) for event in audits)


def test_review_assertions_csrf_conflict_and_historical_read_only(client, db_session) -> None:
    admission = active_admission(db_session)
    auth = authenticate(client)
    endpoint = f"/api/v1/admissions/{admission.id}/allergy-review-assertions"
    assertion = {"category": "food", "assertion": "no_known", "source": "patient"}
    assert client.post(endpoint, json=assertion).status_code == 403
    result = client.post(endpoint, headers=headers(auth), json=assertion)
    assert result.status_code == 201
    projection = client.get(f"/api/v1/admissions/{admission.id}/food-safety-allergies")
    assert projection.json()["review_status"] == "no_known"

    client.post(
        f"/api/v1/admissions/{admission.id}/allergy-intolerances",
        headers=headers(auth),
        json={"items": [{"substance_name": "Nuez", "category": "food", "source": "patient"}]},
    )
    assert client.post(endpoint, headers=headers(auth), json=assertion).status_code == 409

    old = Admission(
        patient_id=admission.patient_id,
        admission_identifier=f"ADM-HIST-{uuid.uuid4().hex[:6]}",
        status="discharged",
        admitted_at=datetime(2025, 2, 1, tzinfo=timezone.utc),
        ended_at=datetime(2025, 2, 2, tzinfo=timezone.utc),
    )
    db_session.add(old)
    db_session.commit()
    historical_endpoint = f"/api/v1/admissions/{old.id}/allergy-review-assertions"
    assert client.post(historical_endpoint, headers=headers(auth), json={
        "category": "all", "assertion": "information_unavailable", "source": "other"
    }).status_code == 409
