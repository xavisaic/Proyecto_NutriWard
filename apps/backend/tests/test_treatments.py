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


def treatment_payload(name: str = "Propofol 2%") -> dict:
    return {
        "kind": "medication",
        "name": name,
        "category": "sedative_analgesic",
        "prescription_text": "Infusión continua según receta médica",
        "concentration_value": 20,
        "concentration_unit": "mg/mL",
        "diluent_volume_ml": None,
        "dose_value": None,
        "dose_unit": None,
        "route": "EV",
        "modality": "Infusión continua",
        "frequency": "Continua",
        "rate_value": 8,
        "rate_unit": "mL/h",
        "prescribed_energy_kcal_day": 211.2,
        "starts_at": "2026-08-19T08:00:00Z",
        "planned_ends_at": None,
        "indication": "Sedación",
        "order_status": "active",
        "source_type": "medical_order",
        "source_reference": "Receta de las 08:00",
        "observed_at": "2026-08-19T08:30:00Z",
        "verification_status": "verified",
        "nutritional_note": "Dato clínico reservado",
    }


def test_permissions_empty_review_and_openapi(client, db_session) -> None:
    admission = active_admission(db_session)
    url = f"/api/v1/admissions/{admission.id}/treatments"
    assert client.get(url).status_code == 401

    authenticate(client, "administrador")
    assert client.get(url).status_code == 403
    client.cookies.clear()
    authenticate(client, "alimentacion")
    assert client.get(url).status_code == 403

    client.cookies.clear()
    auth = authenticate(client, "nutricionista")
    empty = client.get(url)
    assert empty.status_code == 200
    assert empty.json()["review_status"] == "not_reviewed"
    assert empty.json()["items"] == []
    assert empty.json()["counts"] == {
        "active": 0,
        "on_hold": 0,
        "pending_verification": 0,
        "historical": 0,
    }

    review_url = f"{url}/review"
    assert client.post(
        review_url,
        json={"assertion": "no_known", "source_type": "clinical_record"},
    ).status_code == 403
    reviewed = client.post(
        review_url,
        headers=headers(auth),
        json={"assertion": "no_known", "source_type": "clinical_record"},
    )
    assert reviewed.status_code == 201
    assert client.get(url).json()["review_status"] == "no_known"

    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/v1/admissions/{admission_id}/treatments" in paths
    assert "/api/v1/admissions/{admission_id}/treatment-impact-summary" in paths
    assert "/api/v1/admission-treatments/{treatment_id}" in paths


def test_create_context_impact_and_audit_privacy(client, db_session) -> None:
    admission = active_admission(db_session)
    auth = authenticate(client)
    url = f"/api/v1/admissions/{admission.id}/treatments"
    created = client.post(url, headers=headers(auth), json=treatment_payload())
    assert created.status_code == 201, created.text
    item = created.json()
    assert item["kind"] == "medication"
    assert item["current"]["version"] == 1
    assert item["current"]["verifier_name"]
    assert item["history"][0]["change_reason"] == "Registro inicial del tratamiento."

    context = client.get(url).json()
    assert context["review_status"] == "reviewed_with_findings"
    assert context["counts"]["active"] == 1
    assert context["items"][0]["current"]["name"] == "Propofol 2%"

    impact = client.get(
        f"/api/v1/admissions/{admission.id}/treatment-impact-summary"
    )
    assert impact.status_code == 200
    assert float(impact.json()["potential_energy_kcal_day"]) == 211.2
    assert impact.json()["energy_source_count"] == 1
    assert {row["rule_code"] for row in impact.json()["items"]} == {
        "potential_prescribed_energy",
        "motility_context",
    }
    assert "administración efectiva" in impact.json()["disclaimer"]

    audits = db_session.exec(
        select(AuditLog).where(AuditLog.entity_id == uuid.UUID(item["id"]))
    ).all()
    assert audits
    assert all("name" not in (event.after_state or {}) for event in audits)
    assert all("nutritional_note" not in (event.after_state or {}) for event in audits)


def test_versioning_concurrency_duplicate_and_no_delete(client, db_session) -> None:
    admission = active_admission(db_session)
    auth = authenticate(client)
    csrf = headers(auth)
    base_url = f"/api/v1/admissions/{admission.id}/treatments"
    item = client.post(base_url, headers=csrf, json=treatment_payload()).json()

    duplicate = client.post(base_url, headers=csrf, json=treatment_payload("  PROPOFOL 2% "))
    assert duplicate.status_code == 409

    update = treatment_payload()
    update.pop("kind")
    update.update(
        expected_version=1,
        change_reason="Se actualiza velocidad según receta vigente.",
        rate_value=6,
        prescribed_energy_kcal_day=158.4,
    )
    updated = client.patch(
        f"/api/v1/admission-treatments/{item['id']}", headers=csrf, json=update
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["current"]["version"] == 2
    assert len(updated.json()["history"]) == 2
    assert updated.json()["history"][1]["rate_value"] == "8.0000"

    stale = client.patch(
        f"/api/v1/admission-treatments/{item['id']}", headers=csrf, json=update
    )
    assert stale.status_code == 409

    no_known = client.post(
        f"{base_url}/review",
        headers=csrf,
        json={"assertion": "no_known", "source_type": "clinical_record"},
    )
    assert no_known.status_code == 409

    entered_error = {**update, "expected_version": 2, "order_status": "entered_in_error"}
    invalidated = client.patch(
        f"/api/v1/admission-treatments/{item['id']}", headers=csrf, json=entered_error
    )
    assert invalidated.status_code == 200
    assert invalidated.json()["current"]["version"] == 3
    resume = {**update, "expected_version": 3, "order_status": "active"}
    assert client.patch(
        f"/api/v1/admission-treatments/{item['id']}", headers=csrf, json=resume
    ).status_code == 409
    assert client.delete(
        f"/api/v1/admission-treatments/{item['id']}", headers=csrf
    ).status_code in (404, 405)


def test_validation_historical_read_only_and_episode_isolation(client, db_session) -> None:
    admission = active_admission(db_session)
    auth = authenticate(client)
    csrf = headers(auth)
    base_url = f"/api/v1/admissions/{admission.id}/treatments"

    invalid = treatment_payload("Noradrenalina")
    invalid["concentration_unit"] = None
    assert client.post(base_url, headers=csrf, json=invalid).status_code == 422

    created = client.post(base_url, headers=csrf, json=treatment_payload()).json()
    historical = Admission(
        patient_id=admission.patient_id,
        admission_identifier=f"ADM-HIST-{uuid.uuid4().hex[:6]}",
        status="discharged",
        admitted_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
        ended_at=datetime(2025, 1, 2, tzinfo=timezone.utc),
    )
    db_session.add(historical)
    db_session.commit()

    history_context = client.get(f"/api/v1/admissions/{historical.id}/treatments")
    assert history_context.status_code == 200
    assert history_context.json()["items"] == []
    assert client.post(
        f"/api/v1/admissions/{historical.id}/treatments",
        headers=csrf,
        json=treatment_payload("Furosemida"),
    ).status_code == 409
    assert client.post(
        f"/api/v1/admissions/{historical.id}/treatments/review",
        headers=csrf,
        json={"assertion": "information_unavailable", "source_type": "other"},
    ).status_code == 409

    update = treatment_payload()
    update.pop("kind")
    update.update(expected_version=1, change_reason="Intento válido de actualización.")
    assert client.patch(
        f"/api/v1/admission-treatments/{created['id']}", headers=csrf, json=update
    ).status_code == 200

def test_catalog_search_matching_and_bulk_infusion_capture(client, db_session) -> None:
    from app.models.treatment import MedicationCatalogItem

    assert len(db_session.exec(select(MedicationCatalogItem)).all()) == 440
    admission = active_admission(db_session)
    auth = authenticate(client)
    csrf = headers(auth)

    catalog = client.get("/api/v1/medication-catalog?q=propofol&availability=inpatient")
    assert catalog.status_code == 200
    assert catalog.json()["total"] == 2
    assert {item["code"] for item in catalog.json()["items"]} == {
        "100001223",
        "100002090",
    }
    assert all(item["clinical_profile"] == "continuous_infusion" for item in catalog.json()["items"])
    assert client.get(
        "/api/v1/medication-catalog?q=propofol&availability=outpatient"
    ).json()["total"] == 0

    matched = client.post(
        "/api/v1/medication-catalog/match",
        json={
            "lines": [
                "PROPOFOL 1% AM 20 ML",
                "Propofol",
                "XYZ SIN COINCIDENCIA 999",
            ]
        },
    )
    assert matched.status_code == 200
    match_items = matched.json()["items"]
    assert match_items[0]["status"] == "matched"
    assert match_items[0]["match"]["code"] == "100001223"
    assert match_items[1]["status"] == "ambiguous"
    assert len(match_items[1]["suggestions"]) == 2
    assert match_items[2]["status"] == "unmatched"

    propofol = treatment_payload("Texto que no debe reemplazar el arsenal")
    propofol.update(
        medication_catalog_code="100001223",
        raw_medication_text="Propofol 1% a 8 mL/h por 12 horas",
        category="other",
        route=None,
        rate_value=8,
        rate_unit="mL/h",
        infusion_duration_hours=12,
        administered_volume_ml=90,
        prescribed_energy_kcal_day=None,
    )
    created = client.post(
        f"/api/v1/admissions/{admission.id}/treatments/bulk",
        headers=csrf,
        json={"items": [propofol]},
    )
    assert created.status_code == 201, created.text
    current = created.json()["items"][0]["current"]
    assert current["name"] == "PROPOFOL 1% AM 20 ML"
    assert current["category"] == "sedative_analgesic"
    assert current["medication_catalog_code"] == "100001223"
    assert current["medication_catalog"]["available_inpatient"] is True
    assert float(current["estimated_volume_ml"]) == 96
    assert float(current["administered_volume_ml"]) == 90
