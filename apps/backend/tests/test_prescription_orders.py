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


def test_prescription_calculation_lifecycle_versioning_and_audit_privacy(client, db_session) -> None:
    admission = active_admission(db_session)
    auth = authenticate(client, "jefatura")
    headers = {"X-CSRF-Token": auth["csrf_token"]}
    formula = client.post(
        "/api/v1/enteral-formula-catalog",
        headers=headers,
        json={
            "code": "FORM-STD",
            "display_name": "Fórmula estándar institucional",
            "catalog_version": "2026.1",
            "kcal_per_ml": 1,
            "protein_g_per_l": 40,
            "carbohydrate_g_per_l": 120,
            "lipid_g_per_l": 35,
            "fiber_g_per_l": 10,
            "sodium_mg_per_l": 800,
            "potassium_mg_per_l": 1200,
            "phosphorus_mg_per_l": 700,
            "free_water_ml_per_l": 850,
        },
    )
    assert formula.status_code == 201, formula.text
    formula_id = formula.json()["id"]

    client.cookies.clear()
    auth = authenticate(client)
    headers = {"X-CSRF-Token": auth["csrf_token"]}
    payload = {
        "change_reason": "Prescripción nutricional inicial.",
        "oral_enabled": True,
        "enteral_enabled": True,
        "energy_goal_kcal": 1700,
        "protein_goal_g": 85,
        "fluid_goal_ml": 1500,
        "fluid_goal_kind": "maximum",
        "regimen_type": "Papilla hiperproteica",
        "food_iddsi": 4,
        "liquid_iddsi": 2,
        "restrictions": "Hiposódico",
        "feeding_assistance": "Parcial",
        "oral_energy_kcal": 500,
        "oral_protein_g": 20,
        "oral_carbohydrate_g": 70,
        "oral_lipid_g": 15,
        "oral_fluid_ml": 300,
        "enteral_formula_id": formula_id,
        "enteral_access_route": "SNG",
        "enteral_modality": "continuous",
        "enteral_rate_ml_h": 40,
        "enteral_effective_hours": 20,
        "water_flush_ml": 30,
        "water_flush_every_hours": 4,
        "meals": [{"meal_time": "breakfast", "instruction": "Papilla IDDSI 4"}],
        "supplements": [{
            "product_type": "protein_module", "product_name": "Módulo proteico",
            "dose": 20, "dose_unit": "g", "schedule": "cada 12 horas",
            "energy_kcal": 100, "protein_g": 10, "fluid_ml": 100,
        }],
        "progressions": [{"sequence": 1, "stage": "Inicio", "rate_ml_h": 20, "duration_hours": 6, "condition": "Si tolera"}],
        "monitoring": [{"parameter": "tolerancia gastrointestinal", "frequency": "cada turno", "responsible": "Enfermería"}],
    }
    created = client.post(
        f"/api/v1/admissions/{admission.id}/nutrition-prescription-orders",
        headers=headers,
        json=payload,
    )
    assert created.status_code == 201, created.text
    draft = created.json()
    assert draft["status"] == "draft"
    assert draft["enteral_volume_ml"] == "800.00"
    assert draft["prescribed_energy_kcal"] == "1400.00"
    assert draft["prescribed_protein_g"] == "62.00"
    assert draft["prescribed_fluid_ml"] == "1260.00"
    assert next(row for row in draft["coverage"] if row["code"] == "energy")["color"] == "yellow"
    assert "Fórmula estándar institucional" in draft["recipe_text"]
    assert "tolerancia gastrointestinal" in draft["recipe_text"]

    validated = client.post(
        f"/api/v1/nutrition-prescription-orders/{draft['id']}/validate",
        headers=headers,
        json={"expected_lock_version": 1},
    )
    assert validated.status_code == 200, validated.text
    assert validated.json()["status"] == "validated"
    active = client.post(
        f"/api/v1/nutrition-prescription-orders/{draft['id']}/activate",
        headers=headers,
        json={"expected_lock_version": 2},
    )
    assert active.status_code == 200, active.text
    assert active.json()["status"] == "active"

    workspace = client.get(f"/api/v1/admissions/{admission.id}/nutrition-prescription-workspace")
    assert workspace.status_code == 200
    assert workspace.json()["active"]["id"] == draft["id"]
    assert workspace.json()["formulas"][0]["catalog_version"] == "2026.1"

    cloned = client.post(
        f"/api/v1/nutrition-prescription-orders/{draft['id']}/clone",
        headers=headers,
        json={"reason": "Ajuste por nueva tolerancia clínica."},
    )
    assert cloned.status_code == 201, cloned.text
    assert cloned.json()["version_number"] == 2
    assert cloned.json()["status"] == "draft"
    assert cloned.json()["supplements"][0]["product_name"] == "Módulo proteico"

    stale = client.patch(
        f"/api/v1/nutrition-prescription-orders/{cloned.json()['id']}",
        headers=headers,
        json={**payload, "change_reason": "Cambio documentado.", "expected_lock_version": 99},
    )
    assert stale.status_code == 409

    suspended = client.post(
        f"/api/v1/nutrition-prescription-orders/{draft['id']}/suspend",
        headers=headers,
        json={"expected_lock_version": 3, "reason": "Procedimiento transitorio."},
    )
    assert suspended.status_code == 200
    assert suspended.json()["status"] == "suspended"

    audits = db_session.exec(select(AuditLog).where(AuditLog.entity_type == "nutrition_prescription_order")).all()
    assert audits
    assert all("recipe_text" not in str(row.after_state) for row in audits)
    assert all("regimen_type" not in str(row.after_state) for row in audits)


def test_prescription_permissions_and_structural_validation(client, db_session) -> None:
    admission = active_admission(db_session)
    url = f"/api/v1/admissions/{admission.id}/nutrition-prescription-workspace"
    assert client.get(url).status_code == 401
    for role in ("administrador", "alimentacion"):
        client.cookies.clear()
        authenticate(client, role)
        assert client.get(url).status_code == 403

    client.cookies.clear()
    auth = authenticate(client)
    headers = {"X-CSRF-Token": auth["csrf_token"]}
    created = client.post(
        f"/api/v1/admissions/{admission.id}/nutrition-prescription-orders",
        headers=headers,
        json={"change_reason": "Borrador incompleto."},
    )
    assert created.status_code == 201
    rejected = client.post(
        f"/api/v1/nutrition-prescription-orders/{created.json()['id']}/validate",
        headers=headers,
        json={"expected_lock_version": 1},
    )
    assert rejected.status_code == 422


def test_parenteral_real_totals_signature_and_dispatch_outbox(client, db_session) -> None:
    admission = active_admission(db_session)
    auth = authenticate(client)
    headers = {"X-CSRF-Token": auth["csrf_token"]}
    treatment = client.post(
        f"/api/v1/admissions/{admission.id}/treatments",
        headers=headers,
        json={
            "kind": "medication", "name": "Propofol 2%", "category": "sedative_analgesic",
            "prescription_text": "Infusión continua", "rate_value": 8, "rate_unit": "mL/h",
            "prescribed_energy_kcal_day": 300, "order_status": "active",
            "source_type": "medical_order", "observed_at": "2026-08-26T08:00:00Z",
            "verification_status": "verified",
        },
    )
    assert treatment.status_code == 201, treatment.text
    suggested_workspace = client.get(f"/api/v1/admissions/{admission.id}/nutrition-prescription-workspace")
    assert suggested_workspace.status_code == 200
    assert suggested_workspace.json()["treatment_suggestions"][0]["source_type"] == "propofol"
    created = client.post(
        f"/api/v1/admissions/{admission.id}/nutrition-prescription-orders",
        headers=headers,
        json={
            "change_reason": "Inicio de nutrición parenteral individualizada.",
            "parenteral_enabled": True,
            "energy_goal_kcal": 1800,
            "protein_goal_g": 80,
            "lipid_goal_g": 80,
            "fluid_goal_ml": 1600,
            "fluid_goal_kind": "maximum",
            "calculation_weight_kg": 70,
            "parenteral_access": "peripheral",
            "parenteral_solution_type": "individualized",
            "parenteral_solution_name": "Mezcla individualizada 01",
            "parenteral_total_volume_ml": 1440,
            "parenteral_infusion_hours": 24,
            "amino_acids_g": 80,
            "dextrose_g": 200,
            "parenteral_lipid_g": 50,
            "osmolarity_mosm_l": 950,
            "vitamins_instruction": "Multivitamínico según protocolo.",
            "trace_elements_instruction": "Oligoelementos diarios.",
            "refeeding_risk_confirmed": True,
            "electrolytes": [
                {"electrolyte_code": "sodium", "amount": 70, "unit": "mmol"},
                {"electrolyte_code": "phosphate", "amount": 20, "unit": "mmol"},
            ],
            "non_nutritional_contributions": [{
                "source_type": "propofol",
                "label": "Propofol confirmado por tratamiento vigente",
                "source_treatment_id": treatment.json()["id"],
                "energy_kcal": 300,
                "lipid_g": 30,
                "fluid_ml": 100,
                "data_origin": "treatment_snapshot",
                "verification_status": "confirmed",
            }],
        },
    )
    assert created.status_code == 201, created.text
    draft = created.json()
    assert draft["parenteral_rate_ml_h"] == "60.00"
    assert draft["parenteral_gir_mg_kg_min"] == "1.984"
    assert draft["prescribed_energy_kcal"] == "1500.00"
    assert draft["non_nutritional_energy_kcal"] == "300.00"
    assert draft["total_real_energy_kcal"] == "1800.00"
    assert draft["total_real_lipid_g"] == "80.00"
    assert draft["total_real_fluid_ml"] == "1540.00"
    assert next(item for item in draft["coverage"] if item["code"] == "energy")["percent"] == "100.00"
    assert {item["code"] for item in draft["alerts"]} >= {"peripheral_osmolarity", "refeeding_monitoring"}

    validated = client.post(
        f"/api/v1/nutrition-prescription-orders/{draft['id']}/validate",
        headers=headers,
        json={"expected_lock_version": draft["lock_version"]},
    )
    assert validated.status_code == 200, validated.text
    signed = validated.json()
    assert signed["signature_kind"] == "internal_clinical_attestation"
    assert len(signed["signature_content_hash"]) == 64
    assert signed["signed_at"] is not None

    activated = client.post(
        f"/api/v1/nutrition-prescription-orders/{draft['id']}/activate",
        headers=headers,
        json={"expected_lock_version": signed["lock_version"]},
    )
    assert activated.status_code == 200, activated.text
    dispatched = client.post(
        f"/api/v1/nutrition-prescription-orders/{draft['id']}/dispatch",
        headers=headers,
        json={"target": "pharmacy", "note": "Revisión y preparación institucional."},
    )
    assert dispatched.status_code == 200, dispatched.text
    outbox = dispatched.json()["dispatches"]
    assert outbox[0]["channel"] == "internal_outbox"
    assert outbox[0]["status"] == "queued"
    assert outbox[0]["payload_hash"] == signed["signature_content_hash"]

    audits = db_session.exec(select(AuditLog).where(AuditLog.entity_type == "nutrition_prescription_dispatch")).all()
    assert audits
    assert all("recipe_text" not in str(row.after_state) for row in audits)
