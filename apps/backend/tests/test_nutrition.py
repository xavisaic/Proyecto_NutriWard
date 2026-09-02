import uuid
from datetime import date, datetime, timezone

from sqlmodel import select

from app.core.config import settings
from app.core.security import hash_password
from app.models.admission import Admission
from app.models.audit_log import AuditLog
from app.models.patient import Patient
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole


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


def active_admission(db_session) -> Admission:
    admission = db_session.exec(
        select(Admission).where(Admission.status == "active").order_by(Admission.admitted_at)
    ).first()
    assert admission is not None
    return admission


def complete_payload(population: str = "adult") -> dict:
    screening = {
        "tool_code": "nrs_2002",
        "tool_version": "ESPEN 2002",
        "applied_at": "2026-08-13T10:00:00Z",
        "answers": [
            {"answer_code": "nutritional_status_score", "answer_value": "1"},
            {"answer_code": "disease_severity_score", "answer_value": "1"},
            {"answer_code": "age_70_or_more", "answer_value": "true"},
        ],
    }
    if population == "pediatric":
        screening = {
            "tool_code": "strongkids",
            "tool_version": "original",
            "applied_at": "2026-08-13T10:00:00Z",
            "answers": [
                {"answer_code": "subjective_clinical_assessment", "answer_value": "true"},
                {"answer_code": "high_risk_disease", "answer_value": "true"},
                {"answer_code": "nutritional_intake_or_losses", "answer_value": "false"},
                {"answer_code": "weight_loss_or_poor_gain", "answer_value": "true"},
            ],
        }
    if population in ("neonatal", "pregnancy"):
        screening = {
            "tool_code": "none",
            "tool_version": "institutional-policy-pending",
            "applied_at": "2026-08-13T10:00:00Z",
            "no_tool_reason": "Protocolo institucional aún no confirmado.",
            "answers": [],
        }
    return {
        "encounter_datetime": "2026-08-13T10:00:00Z",
        "encounter_type": "initial_assessment",
        "clinical_summary": "Evaluación nutricional inicial estructurada.",
        "reason_for_assessment": "Evaluación al ingreso hospitalario.",
        "information_source": "combined",
        "assessment": {
            "population_group": population,
            "nutritional_status": "Riesgo nutricional en evaluación.",
            "objectives": "Mantener cobertura de requerimientos.",
            "monitoring_plan": "Reevaluar ingesta y tolerancia.",
            "observed_at": "2026-08-13T09:55:00Z",
        },
        "screenings": [screening],
        "diagnoses": [
            {
                "problem": "Ingesta energética insuficiente",
                "etiology": "disminución del apetito",
                "signs_and_symptoms": "consumo estimado menor al plan",
                "priority": 1,
            }
        ],
    }


def test_clinical_permissions_authentication_openapi_and_catalogs(client, db_session) -> None:
    admission = active_admission(db_session)
    url = f"/api/v1/admissions/{admission.id}/nutrition-care-encounters"
    assert client.get(url).status_code == 401
    for role in ("administrador", "alimentacion"):
        client.cookies.clear()
        authenticate(client, role)
        assert client.get(url).status_code == 403
        assert client.post(url, json={}).status_code == 403

    client.cookies.clear()
    authenticate(client)
    catalog = client.get("/api/v1/nutrition-catalogs")
    assert catalog.status_code == 200
    assert catalog.json()["screening_defaults"] == {
        "adult": "nrs_2002",
        "pediatric": "strongkids",
        "neonatal": "none",
        "pregnancy": "none",
    }
    schema = client.get("/openapi.json").json()
    required_paths = {
        "/api/v1/admissions/{admission_id}/nutrition-care-encounters",
        "/api/v1/nutrition-care-encounters/{encounter_id}",
        "/api/v1/nutrition-care-encounters/{encounter_id}/finalize",
        "/api/v1/nutrition-care-encounters/{encounter_id}/correct",
        "/api/v1/nutrition-care-encounters/{encounter_id}/cancel",
        "/api/v1/admissions/{admission_id}/nutrition-latest",
    }
    assert required_paths <= set(schema["paths"])


def test_bulk_lab_import_learns_new_test_preserves_pending_and_builds_trend(client, db_session) -> None:
    admission = active_admission(db_session)
    auth = authenticate(client)
    headers = {"X-CSRF-Token": auth["csrf_token"]}
    endpoint = f"/api/v1/admissions/{admission.id}/nutrition-lab-imports"
    first = client.post(
        endpoint,
        headers=headers,
        json={
            "sampled_at": "2026-08-30T09:00:00Z",
            "source": "trakcare_manual",
            "rows": [
                {
                    "test_name": "Albúmina",
                    "value": "3,2",
                    "unit": "g/dL",
                    "reference_range": "3,5 - 5,2",
                    "resolution": "create",
                },
                {
                    "test_name": "Examen experimental X",
                    "value": "<5",
                    "unit": "mg/L",
                    "resolution": "pending",
                },
            ],
        },
    )
    assert first.status_code == 201, first.text
    assert first.json()["created_catalog_count"] == 1
    assert first.json()["pending_count"] == 1
    assert first.json()["items"][0]["numeric_value"] == "3.200000"
    assert first.json()["items"][0]["reference_low"] == "3.500000"
    assert first.json()["items"][1]["comparator"] == "<"

    catalog = client.get("/api/v1/nutrition-lab-catalog")
    assert catalog.status_code == 200
    assert [item["canonical_name"] for item in catalog.json()] == ["Albúmina"]

    second = client.post(
        endpoint,
        headers=headers,
        json={
            "sampled_at": "2026-08-31T09:00:00Z",
            "rows": [
                {
                    "test_name": "Albumina",
                    "value": "3.8",
                    "unit": "g/dL",
                    "reference_range": "3.5-5.2",
                    "resolution": "match",
                }
            ],
        },
    )
    assert second.status_code == 201, second.text
    assert second.json()["created_catalog_count"] == 0
    assert second.json()["pending_count"] == 0

    trends = client.get(f"/api/v1/admissions/{admission.id}/nutrition-lab-trends")
    assert trends.status_code == 200, trends.text
    series = trends.json()["series"]
    albumin = next(item for item in series if item["display_name"] == "Albúmina")
    assert [point["value"] for point in albumin["points"]] == ["3,2", "3.8"]
    pending = next(item for item in series if item["display_name"] == "Examen experimental X")
    assert pending["pending_classification"] is True

    classified = client.patch(
        f"/api/v1/nutrition-lab-observations/{pending['points'][0]['id']}/classification",
        headers=headers,
        json={"create_new": True},
    )
    assert classified.status_code == 200, classified.text
    assert classified.json()["canonical_name"] == "Examen experimental X"
    assert classified.json()["pending_classification"] is False

    projection = client.get(f"/api/v1/admissions/{admission.id}/nutrition-labs?page_size=100")
    assert projection.status_code == 200
    assert projection.json()["total"] == 3
    assert not any(item["pending_classification"] for item in projection.json()["items"])


def test_draft_version_finalization_immutability_latest_and_correction(client, db_session) -> None:
    admission = active_admission(db_session)
    auth = authenticate(client)
    headers = {"X-CSRF-Token": auth["csrf_token"]}
    created = client.post(
        f"/api/v1/admissions/{admission.id}/nutrition-care-encounters",
        json=complete_payload(),
        headers=headers,
    )
    assert created.status_code == 201, created.text
    body = created.json()
    encounter_id = body["encounter"]["id"]
    assert body["encounter"]["status"] == "draft"
    assert body["screenings"][0]["total_score"] == "3.00"
    assert body["screenings"][0]["classification"] == "nutritional_risk"
    assert "relacionado con" in body["diagnoses"][0]["generated_statement"]
    assert "evidenciado por" in body["diagnoses"][0]["generated_statement"]

    patched = client.patch(
        f"/api/v1/nutrition-care-encounters/{encounter_id}",
        json={"version": 1, "clinical_summary": "Síntesis actualizada."},
        headers=headers,
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["encounter"]["version"] == 2
    stale = client.patch(
        f"/api/v1/nutrition-care-encounters/{encounter_id}",
        json={"version": 1, "clinical_summary": "Escritura obsoleta."},
        headers=headers,
    )
    assert stale.status_code == 409

    finalized = client.post(
        f"/api/v1/nutrition-care-encounters/{encounter_id}/finalize",
        json={"version": 2},
        headers=headers,
    )
    assert finalized.status_code == 200, finalized.text
    assert finalized.json()["encounter"]["status"] == "finalized"
    assert client.patch(
        f"/api/v1/nutrition-care-encounters/{encounter_id}",
        json={"version": 3, "clinical_summary": "No permitido."},
        headers=headers,
    ).status_code == 409

    latest = client.get(f"/api/v1/admissions/{admission.id}/nutrition-latest")
    assert latest.status_code == 200
    latest_body = latest.json()
    assert latest_body["latest_encounter"]["id"] == encounter_id
    assert latest_body["active_diagnoses"][0]["problem"] == "Ingesta energética insuficiente"
    assert "audit_logs" not in str(latest_body)

    correction = client.post(
        f"/api/v1/nutrition-care-encounters/{encounter_id}/correct",
        json={"version": 3, "reason": "Corrección justificada de la evaluación original."},
        headers=headers,
    )
    assert correction.status_code == 201, correction.text
    corrected_body = correction.json()
    assert corrected_body["encounter"]["status"] == "draft"
    assert corrected_body["encounter"]["corrected_encounter_id"] == encounter_id
    assert corrected_body["diagnoses"][0]["problem"] == "Ingesta energética insuficiente"
    original = client.get(f"/api/v1/nutrition-care-encounters/{encounter_id}").json()
    assert original["encounter"]["status"] == "finalized"


def test_cancel_author_rules_historical_and_not_found(client, db_session) -> None:
    admission = active_admission(db_session)
    auth = authenticate(client)
    headers = {"X-CSRF-Token": auth["csrf_token"]}
    created = client.post(
        f"/api/v1/admissions/{admission.id}/nutrition-care-encounters",
        json={"encounter_type": "follow_up"},
        headers=headers,
    )
    encounter_id = created.json()["encounter"]["id"]
    incomplete = client.post(
        f"/api/v1/nutrition-care-encounters/{encounter_id}/finalize",
        json={"version": 1},
        headers=headers,
    )
    assert incomplete.status_code == 422
    assert "section_errors" in str(incomplete.json())

    role = db_session.exec(select(Role).where(Role.name == "nutricionista")).one()
    other = User(
        email="otro.nutricionista@nutriward.local",
        full_name="Otro Nutricionista",
        password_hash=hash_password(settings.demo_user_password),
    )
    db_session.add(other)
    db_session.flush()
    db_session.add(UserRole(user_id=other.id, role_id=role.id))
    db_session.commit()
    client.cookies.clear()
    assert client.post(
        "/api/v1/auth/login",
        json={"email": other.email, "password": settings.demo_user_password},
    ).status_code == 200
    assert client.get(f"/api/v1/nutrition-care-encounters/{encounter_id}").status_code == 403
    listed = client.get(
        f"/api/v1/admissions/{admission.id}/nutrition-care-encounters"
    ).json()
    assert encounter_id not in {item["id"] for item in listed["items"]}

    client.cookies.clear()
    boss = authenticate(client, "jefatura")
    cancelled = client.post(
        f"/api/v1/nutrition-care-encounters/{encounter_id}/cancel",
        json={"version": 1, "reason": "Borrador duplicado, se conserva trazabilidad."},
        headers={"X-CSRF-Token": boss["csrf_token"]},
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["encounter"]["status"] == "cancelled"
    assert cancelled.json()["encounter"]["cancellation_reason"]

    historical = db_session.exec(select(Admission).where(Admission.status != "active")).first()
    assert historical is not None
    assert client.post(
        f"/api/v1/admissions/{historical.id}/nutrition-care-encounters",
        json={},
        headers={"X-CSRF-Token": boss["csrf_token"]},
    ).status_code == 409
    assert client.get(
        f"/api/v1/admissions/{uuid.uuid4()}/nutrition-care-encounters"
    ).status_code == 404
    assert client.get(f"/api/v1/nutrition-care-encounters/{uuid.uuid4()}").status_code == 404


def test_modular_follow_up_preserves_previous_clinical_projections(client, db_session) -> None:
    admission = active_admission(db_session)
    auth = authenticate(client)
    headers = {"X-CSRF-Token": auth["csrf_token"]}
    initial_payload = complete_payload()
    initial_payload["prescription"] = {
        "effective_from": "2026-08-13T12:00:00Z",
        "primary_route": "oral",
        "regimen_type": "Régimen liviano",
        "energy_target": 1800,
    }
    initial = client.post(
        f"/api/v1/admissions/{admission.id}/nutrition-care-encounters",
        json=initial_payload,
        headers=headers,
    )
    assert initial.status_code == 201, initial.text
    initial_id = initial.json()["encounter"]["id"]
    assert client.post(
        f"/api/v1/nutrition-care-encounters/{initial_id}/finalize",
        json={"version": 1},
        headers=headers,
    ).status_code == 200

    follow_up = client.post(
        f"/api/v1/admissions/{admission.id}/nutrition-care-encounters",
        json={
            "encounter_type": "follow_up",
            "reason_for_assessment": "Control diario de ingesta.",
            "information_source": "patient_interview",
            "clinical_summary": "Menor ingesta durante el almuerzo; reevaluar mañana.",
            "intake": [{
                "intake_date": "2026-08-14",
                "meal_time": "lunch",
                "consumed_percentage": 40,
                "incomplete_reason": "Náuseas",
                "source": "patient_interview",
            }],
        },
        headers=headers,
    )
    assert follow_up.status_code == 201, follow_up.text
    follow_up_id = follow_up.json()["encounter"]["id"]
    finalized = client.post(
        f"/api/v1/nutrition-care-encounters/{follow_up_id}/finalize",
        json={"version": 1},
        headers=headers,
    )
    assert finalized.status_code == 200, finalized.text

    latest = client.get(f"/api/v1/admissions/{admission.id}/nutrition-latest").json()
    assert latest["latest_encounter"]["id"] == follow_up_id
    assert latest["nutritional_status"] == "Riesgo nutricional en evaluación."
    assert latest["latest_screening"]["tool_code"] == "nrs_2002"
    assert latest["active_diagnoses"][0]["problem"] == "Ingesta energética insuficiente"
    assert latest["current_prescription"]["regimen_type"] == "Régimen liviano"

    listed = client.get(
        f"/api/v1/admissions/{admission.id}/nutrition-care-encounters"
    ).json()["items"]
    follow_up_summary = next(row for row in listed if row["id"] == follow_up_id)
    assert follow_up_summary["documented_sections"] == ["context", "intake"]

    resolution = client.post(
        f"/api/v1/admissions/{admission.id}/nutrition-care-encounters",
        json={
            "encounter_type": "follow_up",
            "reason_for_assessment": "Cierre de objetivos nutricionales.",
            "information_source": "combined",
            "clinical_summary": "PES resuelto y prescripción discontinuada.",
            "diagnoses": [{
                "problem": "Ingesta energética insuficiente",
                "etiology": "disminución del apetito",
                "signs_and_symptoms": "cobertura recuperada",
                "priority": 1,
                "status": "resolved",
                "resolved_at": "2026-08-15T10:00:00Z",
            }],
            "prescription": {
                "effective_from": "2026-08-15T10:00:00Z",
                "effective_until": "2026-08-15T10:00:00Z",
                "status": "discontinued",
                "primary_route": "oral",
                "regimen_type": "Prescripción finalizada",
            },
        },
        headers=headers,
    )
    assert resolution.status_code == 201, resolution.text
    resolution_id = resolution.json()["encounter"]["id"]
    assert client.post(
        f"/api/v1/nutrition-care-encounters/{resolution_id}/finalize",
        json={"version": 1},
        headers=headers,
    ).status_code == 200

    resolved_latest = client.get(
        f"/api/v1/admissions/{admission.id}/nutrition-latest"
    ).json()
    assert resolved_latest["active_diagnoses"] == []
    assert resolved_latest["current_prescription"] is None
    assert resolved_latest["nutritional_status"] == "Riesgo nutricional en evaluación."
    assert resolved_latest["latest_screening"]["tool_code"] == "nrs_2002"


def test_advanced_measurements_calculate_protocol_results_and_preserve_device_data(
    client, db_session
) -> None:
    admission = active_admission(db_session)
    auth = authenticate(client)
    clinical_headers = {"X-CSRF-Token": auth["csrf_token"]}
    handgrip_values = [
        {
            "measurement_code": "handgrip_strength",
            "laterality": side,
            "attempt_number": attempt,
            "value": value,
            "unit": "kgf",
        }
        for side, readings in (("left", (20, 22, 21)), ("right", (24, 23, 25)))
        for attempt, value in enumerate(readings, start=1)
    ]
    skinfold_values = [
        {
            "measurement_code": code,
            "laterality": "right",
            "attempt_number": attempt,
            "value": value,
            "unit": "mm",
        }
        for code, readings in (
            ("skinfold_biceps", (4, 5, 6)),
            ("skinfold_triceps", (10, 11, 12)),
            ("skinfold_subscapular", (15, 16, 17)),
            ("skinfold_suprailiac", (20, 21, 22)),
        )
        for attempt, value in enumerate(readings, start=1)
    ]
    payload = {
        "encounter_type": "follow_up",
        "reason_for_assessment": "Medición corporal avanzada.",
        "information_source": "care_team_observation",
        "clinical_summary": "Se registran composición y función muscular.",
        "advanced_measurements": [
            {
                "session_type": "circumference",
                "measured_at": "2026-08-17T10:00:00Z",
                "protocol_code": "institutional-circumferences",
                "protocol_version": "v1",
                "position": "standing",
                "values": [
                    {"measurement_code": "calf_circumference", "laterality": "left", "value": 31.2, "unit": "cm"},
                    {"measurement_code": "calf_circumference", "laterality": "right", "value": 31.5, "unit": "cm"},
                    {"measurement_code": "mid_upper_arm_circumference", "laterality": "right", "value": 25.4, "unit": "cm"},
                    {"measurement_code": "waist_circumference", "value": 89.0, "unit": "cm"},
                ],
            },
            {
                "session_type": "handgrip",
                "measured_at": "2026-08-17T10:05:00Z",
                "protocol_code": "hospital-handgrip",
                "protocol_version": "v1",
                "device_manufacturer": "Jamar",
                "device_model": "Hydraulic",
                "position": "seated",
                "values": handgrip_values,
            },
            {
                "session_type": "skinfold_4",
                "measured_at": "2026-08-17T10:10:00Z",
                "protocol_code": "durnin-womersley-4",
                "protocol_version": "v1",
                "device_manufacturer": "Harpenden",
                "device_model": "Clinical caliper",
                "position": "standing",
                "values": skinfold_values,
            },
            {
                "session_type": "bioimpedance",
                "measured_at": "2026-08-17T10:20:00Z",
                "protocol_code": "device-reported-bia",
                "protocol_version": "v1",
                "device_manufacturer": "InBody",
                "device_model": "Clinical demo",
                "technology": "multifrequency_segmental",
                "frequencies_khz": "5, 50, 250",
                "position": "standing",
                "preparation_status": "standard",
                "fasting_hours": 4,
                "recent_exercise": False,
                "bladder_emptied": True,
                "hydration_status": "usual",
                "edema_present": False,
                "values": [
                    {"measurement_code": "resistance", "value": 510, "unit": "ohm"},
                    {"measurement_code": "reactance", "value": 47, "unit": "ohm"},
                    {"measurement_code": "phase_angle", "value": 5.3, "unit": "degree"},
                    {"measurement_code": "fat_free_mass", "value": 48.2, "unit": "kg"},
                ],
            },
        ],
    }
    created = client.post(
        f"/api/v1/admissions/{admission.id}/nutrition-care-encounters",
        json=payload,
        headers=clinical_headers,
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert len(body["advanced_measurements"]) == 4
    handgrip = next(
        row for row in body["advanced_measurements"] if row["session_type"] == "handgrip"
    )
    assert handgrip["algorithm_version"] == "maximum-of-three-bilateral-v1"
    grip_results = {row["measurement_code"]: row["value"] for row in handgrip["values"]}
    assert grip_results["handgrip_max_left"] == "22.0000"
    assert grip_results["handgrip_max_right"] == "25.0000"
    assert grip_results["handgrip_max"] == "25.0000"
    skinfold = next(
        row for row in body["advanced_measurements"] if row["session_type"] == "skinfold_4"
    )
    skinfold_results = {row["measurement_code"]: row["value"] for row in skinfold["values"]}
    assert skinfold_results["skinfold_sum_4"] == "53.0000"
    bia = next(
        row for row in body["advanced_measurements"] if row["session_type"] == "bioimpedance"
    )
    assert bia["technology"] == "multifrequency_segmental"
    assert all(row["value_nature"] == "device_reported" for row in bia["values"])

    encounter_id = body["encounter"]["id"]
    assert client.post(
        f"/api/v1/nutrition-care-encounters/{encounter_id}/finalize",
        json={"version": 1},
        headers=clinical_headers,
    ).status_code == 200
    anthropometry_projection = client.get(
        f"/api/v1/admissions/{admission.id}/nutrition-anthropometry"
    ).json()
    projected_handgrip = next(
        row
        for row in anthropometry_projection["items"]
        if row["record_type"] == "advanced_session"
        and row["session_type"] == "handgrip"
    )
    assert len(projected_handgrip["values"]) == 9
    assert any(
        row["measurement_code"] == "handgrip_max"
        and row["value_nature"] == "calculated"
        for row in projected_handgrip["values"]
    )
    summaries = client.get(
        f"/api/v1/admissions/{admission.id}/nutrition-care-encounters"
    ).json()["items"]
    summary = next(row for row in summaries if row["id"] == encounter_id)
    assert summary["documented_sections"] == ["context", "anthropometry"]

    invalid = {**payload, "advanced_measurements": [payload["advanced_measurements"][1]]}
    invalid["advanced_measurements"][0] = {
        **invalid["advanced_measurements"][0],
        "values": handgrip_values[:-1],
    }
    rejected = client.post(
        f"/api/v1/admissions/{admission.id}/nutrition-care-encounters",
        json=invalid,
        headers=clinical_headers,
    )
    assert rejected.status_code == 422


def test_anthropometry_requirements_prescription_intake_labs_and_alerts(client, db_session) -> None:
    admission = active_admission(db_session)
    auth = authenticate(client)
    headers = {"X-CSRF-Token": auth["csrf_token"]}
    payload = complete_payload()
    payload.update({
        "anthropometry": [
            {"measurement_type": "current_weight_measured", "value": 80, "unit": "kg", "measured_at": "2026-08-13T08:00:00Z", "reliability": "high", "value_nature": "measured"},
            {"measurement_type": "usual_weight", "value": 100, "unit": "kg", "measured_at": "2026-07-13T08:00:00Z", "reliability": "medium", "value_nature": "reported"},
            {"measurement_type": "standing_height", "value": 200, "unit": "cm", "measured_at": "2026-08-13T08:00:00Z", "reliability": "high", "value_nature": "measured"},
        ],
        "prescription": {
            "effective_from": "2026-08-13T12:00:00Z", "primary_route": "oral",
            "energy_target": 2200, "protein_target": 95, "fluid_target": 2000,
            "regimen_type": "Régimen individualizado",
            "meal_times": [{"meal_time": "lunch", "regimen": "Régimen liviano", "texture": "normal"}],
        },
        "intake": [{"intake_date": "2026-08-13", "meal_time": "lunch", "consumed_percentage": 75, "incomplete_reason": "Saciedad precoz", "source": "patient_interview"}],
        "labs": [{"test_name": "Glicemia", "value": "110", "unit": "mg/dL", "sampled_at": "2026-08-13T07:00:00Z", "source": "trakcare_manual"}],
        "alerts": [{"alert_type": "food_allergy", "description": "Alergia a maní informada", "source": "trakcare_manual", "verification_status": "unverified"}],
    })
    created = client.post(
        f"/api/v1/admissions/{admission.id}/nutrition-care-encounters",
        json=payload,
        headers=headers,
    )
    assert created.status_code == 201, created.text
    body = created.json()
    bmi = next(item for item in body["anthropometry"] if item["measurement_type"] == "body_mass_index")
    assert bmi["value"] == "20.0000"
    weight_change = next(item for item in body["anthropometry"] if item["measurement_type"] == "weight_change_percentage")
    assert weight_change["value"] == "20.0000"
    assert weight_change["calculated_value"] == "-20.0000"
    weight = next(item for item in body["anthropometry"] if item["measurement_type"] == "current_weight_measured")

    patched = client.patch(
        f"/api/v1/nutrition-care-encounters/{body['encounter']['id']}",
        json={
            "version": 1,
            "requirements": [
                {
                    "nutrient_code": "energy", "method": "factorial", "unit": "kcal/day",
                    "weight_measurement_id": weight["id"], "weight_selection_reason": "Peso actual medido confiable.",
                    "inputs": {"basal_result": 1500, "activity_factor": 1.2, "stress_factor": 1.1, "thermal_factor": 1},
                }
            ],
        },
        headers=headers,
    )
    assert patched.status_code == 200, patched.text
    requirement = patched.json()["requirements"][0]
    assert requirement["automatic_result"] == "1980.00"
    assert requirement["weight_measurement_id"] == weight["id"]

    finalized = client.post(
        f"/api/v1/nutrition-care-encounters/{body['encounter']['id']}/finalize",
        json={"version": 2}, headers=headers,
    )
    assert finalized.status_code == 200
    anthropometry_projection = client.get(
        f"/api/v1/admissions/{admission.id}/nutrition-anthropometry"
    ).json()
    assert anthropometry_projection["total"] >= 5
    assert anthropometry_projection["items"][0]["record_type"] == "measurement"
    screening_projection = client.get(
        f"/api/v1/admissions/{admission.id}/nutrition-screenings"
    ).json()
    assert screening_projection["total"] >= 1
    assert screening_projection["items"][0]["answers"]
    assert client.get(f"/api/v1/admissions/{admission.id}/nutrition-prescriptions").json()["total"] >= 1
    assert client.get(f"/api/v1/admissions/{admission.id}/nutrition-intake").json()["items"][0]["consumed_percentage"] == "75.00"
    lab = client.get(f"/api/v1/admissions/{admission.id}/nutrition-labs").json()["items"][0]
    assert lab["source"] == "trakcare_manual"

    audit_rows = db_session.exec(
        select(AuditLog).where(AuditLog.entity_type == "nutritional_care_encounter")
    ).all()
    assert audit_rows
    assert all("clinical_summary" not in str(row.after_state) for row in audit_rows)


def test_strongkids_and_no_automatic_neonatal_or_pregnancy_tool(client, db_session) -> None:
    admission = active_admission(db_session)
    auth = authenticate(client)
    headers = {"X-CSRF-Token": auth["csrf_token"]}
    pediatric = client.post(
        f"/api/v1/admissions/{admission.id}/nutrition-care-encounters",
        json=complete_payload("pediatric"), headers=headers,
    )
    assert pediatric.status_code == 201
    screening = pediatric.json()["screenings"][0]
    assert screening["total_score"] == "4.00"
    assert screening["classification"] == "high"
    rejected_factorial = client.patch(
        f"/api/v1/nutrition-care-encounters/{pediatric.json()['encounter']['id']}",
        json={
            "version": 1,
            "requirements": [{
                "nutrient_code": "energy", "method": "factorial", "unit": "kcal/day",
                "inputs": {"basal_result": 1000, "activity_factor": 1, "stress_factor": 1},
            }],
        },
        headers=headers,
    )
    assert rejected_factorial.status_code == 422
    for population in ("neonatal", "pregnancy"):
        response = client.post(
            f"/api/v1/admissions/{admission.id}/nutrition-care-encounters",
            json=complete_payload(population), headers=headers,
        )
        assert response.status_code == 201
        screening = response.json()["screenings"][0]
        assert screening["tool_code"] == "none"
        assert screening["total_score"] is None


def test_nrs_initial_screen_negative_does_not_require_final_components(client, db_session) -> None:
    admission = active_admission(db_session)
    auth = authenticate(client)
    headers = {"X-CSRF-Token": auth["csrf_token"]}
    payload = complete_payload()
    payload["screenings"] = [{
        "tool_code": "nrs_2002",
        "tool_version": "ESPEN 2002",
        "applied_at": "2026-08-13T10:00:00Z",
        "answers": [
            {"answer_code": "initial_bmi_below_20_5", "answer_value": "false"},
            {"answer_code": "initial_weight_loss_3_months", "answer_value": "false"},
            {"answer_code": "initial_reduced_intake_last_week", "answer_value": "false"},
            {"answer_code": "initial_severely_ill", "answer_value": "false"},
        ],
    }]
    response = client.post(
        f"/api/v1/admissions/{admission.id}/nutrition-care-encounters",
        json=payload,
        headers=headers,
    )
    assert response.status_code == 201, response.text
    screening = response.json()["screenings"][0]
    assert screening["total_score"] == "0.00"
    assert screening["classification"] == "initial_screen_negative"


def test_nrs_v2_derives_components_uses_maximum_and_calculates_exact_age(client, db_session) -> None:
    admission = active_admission(db_session)
    patient = db_session.get(Patient, admission.patient_id)
    assert patient is not None
    patient.date_of_birth = date(1950, 1, 1)
    patient.date_of_birth_is_estimated = False
    db_session.add(patient)
    db_session.commit()
    auth = authenticate(client)
    headers = {"X-CSRF-Token": auth["csrf_token"]}
    payload = complete_payload()
    payload["screenings"] = [{
        "tool_code": "nrs_2002",
        "tool_version": "ESPEN 2002",
        "applied_at": "2026-08-13T10:00:00Z",
        "answers": [
            {"answer_code": "screening_flow_version", "answer_value": "v2"},
            {"answer_code": "initial_bmi_below_20_5", "answer_value": "true"},
            {"answer_code": "initial_weight_loss_3_months", "answer_value": "true"},
            {"answer_code": "initial_reduced_intake_last_week", "answer_value": "true"},
            {"answer_code": "initial_severely_ill", "answer_value": "false"},
            {"answer_code": "weight_loss_category", "answer_value": "over_5_2_months"},
            {"answer_code": "intake_category", "answer_value": "50_75"},
            {"answer_code": "current_bmi", "answer_value": "19"},
            {"answer_code": "impaired_general_condition", "answer_value": "true"},
            {"answer_code": "disease_severity_score", "answer_value": "2"},
            {"answer_code": "age_70_or_more", "answer_value": "false"},
        ],
    }]
    response = client.post(
        f"/api/v1/admissions/{admission.id}/nutrition-care-encounters",
        json=payload,
        headers=headers,
    )
    assert response.status_code == 201, response.text
    screening = response.json()["screenings"][0]
    assert screening["algorithm_version"] == "espen-nrs2002-v2"
    assert screening["total_score"] == "5.00"
    assert screening["classification"] == "nutritional_risk"
    answers = {row["answer_code"]: row for row in screening["answers"]}
    assert answers["weight_loss_category"]["component_score"] == "2.00"
    assert answers["intake_category"]["component_score"] == "1.00"
    assert answers["current_bmi"]["component_score"] == "2.00"
    assert answers["nutritional_status_score"]["answer_value"] == "2"
    assert answers["age_70_or_more"]["answer_value"] == "true"


def test_nrs_v2_initial_negative_and_incomplete_final_validation(client, db_session) -> None:
    admission = active_admission(db_session)
    auth = authenticate(client)
    headers = {"X-CSRF-Token": auth["csrf_token"]}
    payload = complete_payload()
    initial_answers = [
        {"answer_code": "screening_flow_version", "answer_value": "v2"},
        {"answer_code": "initial_bmi_below_20_5", "answer_value": "false"},
        {"answer_code": "initial_weight_loss_3_months", "answer_value": "false"},
        {"answer_code": "initial_reduced_intake_last_week", "answer_value": "false"},
        {"answer_code": "initial_severely_ill", "answer_value": "false"},
    ]
    payload["screenings"] = [{
        "tool_code": "nrs_2002", "tool_version": "ESPEN 2002",
        "applied_at": "2026-08-13T10:00:00Z", "answers": initial_answers,
    }]
    negative = client.post(
        f"/api/v1/admissions/{admission.id}/nutrition-care-encounters",
        json=payload, headers=headers,
    )
    assert negative.status_code == 201, negative.text
    assert negative.json()["screenings"][0]["algorithm_version"] == "espen-nrs2002-v2"
    assert negative.json()["screenings"][0]["classification"] == "initial_screen_negative"

    payload["screenings"][0]["answers"][1]["answer_value"] = "true"
    payload["screenings"][0]["answers"].append(
        {"answer_code": "weight_loss_category", "answer_value": "over_5_3_months"}
    )
    incomplete = client.post(
        f"/api/v1/admissions/{admission.id}/nutrition-care-encounters",
        json=payload, headers=headers,
    )
    assert incomplete.status_code == 201, incomplete.text
    incomplete_screening = incomplete.json()["screenings"][0]
    assert incomplete_screening["classification"] == "incomplete"
    finalized = client.post(
        f"/api/v1/nutrition-care-encounters/{incomplete.json()['encounter']['id']}/finalize",
        json={"version": incomplete.json()["encounter"]["version"]},
        headers=headers,
    )
    assert finalized.status_code == 422
    assert "complete todas las respuestas" in finalized.text
