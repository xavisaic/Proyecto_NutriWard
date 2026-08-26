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

