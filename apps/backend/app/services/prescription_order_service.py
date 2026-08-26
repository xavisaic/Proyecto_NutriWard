import uuid
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException, status
from sqlalchemy import delete, func
from sqlmodel import Session, select

from app.models.admission import Admission
from app.models.nutrition import NutritionalCareEncounter, NutritionalRequirementCalculation
from app.models.prescription_order import (
    EnteralFormulaCatalogItem,
    NutritionPrescriptionMeal,
    NutritionPrescriptionMonitoring,
    NutritionPrescriptionOrder,
    NutritionPrescriptionProgression,
    NutritionPrescriptionSetting,
    NutritionPrescriptionSupplement,
)
from app.models.user import User
from app.schemas.prescription_order import (
    FormulaCatalogCreate,
    PrescriptionAction,
    PrescriptionClone,
    PrescriptionOrderCreate,
    PrescriptionOrderUpdate,
    PrescriptionSettingsUpdate,
    PrescriptionSuspension,
)
from app.services.audit_service import record_audit
from app.models.common import utc_now


Q = Decimal("0.01")
CHILD_MODELS = (
    NutritionPrescriptionMeal,
    NutritionPrescriptionSupplement,
    NutritionPrescriptionProgression,
    NutritionPrescriptionMonitoring,
)
NESTED_FIELDS = {"meals", "supplements", "progressions", "monitoring"}
DIFF_FIELDS = {
    "oral_enabled": "Alimentación oral", "enteral_enabled": "Nutrición enteral",
    "fasting_enabled": "Régimen cero", "energy_goal_kcal": "Meta energética",
    "protein_goal_g": "Meta proteica", "carbohydrate_goal_g": "Meta de carbohidratos",
    "lipid_goal_g": "Meta de lípidos", "fluid_goal_ml": "Meta de volumen",
    "fluid_goal_kind": "Tipo de meta hídrica", "regimen_type": "Régimen",
    "food_iddsi": "IDDSI alimentos", "liquid_iddsi": "IDDSI líquidos",
    "restrictions": "Restricciones", "feeding_assistance": "Asistencia",
    "enteral_formula_id": "Fórmula enteral", "enteral_access_route": "Acceso enteral",
    "enteral_modality": "Modalidad enteral", "enteral_rate_ml_h": "Velocidad enteral",
    "enteral_effective_hours": "Horas efectivas", "water_flush_ml": "Volumen de lavado",
    "water_flush_every_hours": "Frecuencia de lavado", "suggested_reassessment_at": "Reevaluación",
}


def _not_found(detail: str = "La prescripción no existe.") -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def _conflict(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


def _invalid(detail: str) -> HTTPException:
    return HTTPException(status_code=422, detail=detail)


def _admission(session: Session, admission_id: uuid.UUID, *, active: bool = False) -> Admission:
    admission = session.get(Admission, admission_id)
    if admission is None:
        raise _not_found("La hospitalización no existe.")
    if active and admission.status != "active":
        raise _conflict("El episodio histórico es de sólo lectura.")
    return admission


def _order(session: Session, order_id: uuid.UUID) -> NutritionPrescriptionOrder:
    row = session.get(NutritionPrescriptionOrder, order_id)
    if row is None:
        raise _not_found()
    return row


def _ensure_version(row: NutritionPrescriptionOrder, expected: int) -> None:
    if row.lock_version != expected:
        raise _conflict("La prescripción cambió en otra sesión. Recargue antes de continuar.")


def _settings(session: Session) -> NutritionPrescriptionSetting:
    row = session.get(NutritionPrescriptionSetting, "default")
    if row is None:
        row = NutritionPrescriptionSetting()
        session.add(row)
        session.flush()
    return row


def _children(session: Session, model, order_id: uuid.UUID) -> list:
    statement = select(model).where(model.order_id == order_id)
    if model is NutritionPrescriptionProgression:
        statement = statement.order_by(model.sequence, model.id)
    else:
        statement = statement.order_by(model.id)
    return list(session.exec(statement).all())


def _dump(row) -> dict:
    return row.model_dump(mode="json")


def _classify(value: Decimal, goal: Decimal | None, settings: NutritionPrescriptionSetting, *, maximum: bool = False) -> tuple[Decimal | None, str]:
    if goal is None or goal <= 0:
        return None, "neutral"
    percent = ((value / goal) * 100).quantize(Q, rounding=ROUND_HALF_UP)
    if maximum and value <= goal:
        return percent, "green"
    if settings.green_min_percent <= percent <= settings.green_max_percent:
        return percent, "green"
    if settings.yellow_min_percent <= percent <= settings.yellow_max_percent:
        return percent, "yellow"
    return percent, "red"


def _coverage(row: NutritionPrescriptionOrder, settings: NutritionPrescriptionSetting) -> list[dict]:
    metrics = [
        ("energy", "Energía", row.energy_goal_kcal, row.prescribed_energy_kcal, "kcal"),
        ("protein", "Proteínas", row.protein_goal_g, row.prescribed_protein_g, "g"),
        ("carbohydrate", "Carbohidratos", row.carbohydrate_goal_g, row.prescribed_carbohydrate_g, "g"),
        ("lipid", "Lípidos", row.lipid_goal_g, row.prescribed_lipid_g, "g"),
        ("fluid", "Volumen", row.fluid_goal_ml, row.prescribed_fluid_ml, "mL"),
    ]
    result = []
    for code, label, goal, prescribed, unit in metrics:
        percent, color = _classify(
            prescribed,
            goal,
            settings,
            maximum=code == "fluid" and row.fluid_goal_kind == "maximum",
        )
        result.append({
            "code": code, "label": label, "goal": goal, "prescribed": prescribed,
            "unit": unit, "percent": percent, "color": color,
            "goal_kind": row.fluid_goal_kind if code == "fluid" else "target",
        })
    return result


def _alerts(row: NutritionPrescriptionOrder, coverage: list[dict]) -> list[dict]:
    alerts: list[dict] = []
    if not (row.oral_enabled or row.enteral_enabled or row.fasting_enabled):
        alerts.append({"severity": "warning", "code": "strategy_missing", "message": "Seleccione al menos una estrategia nutricional."})
    if row.enteral_enabled and row.enteral_formula_id is None:
        alerts.append({"severity": "warning", "code": "formula_missing", "message": "La estrategia enteral no tiene una fórmula seleccionada."})
    for metric in coverage:
        if metric["color"] == "red" and metric["goal"] is not None:
            alerts.append({"severity": "error", "code": f"coverage_{metric['code']}", "message": f"{metric['label']}: aporte fuera del rango institucional de apoyo."})
    if row.fluid_goal_kind == "maximum" and row.fluid_goal_ml and row.prescribed_fluid_ml > row.fluid_goal_ml:
        alerts.append({"severity": "error", "code": "fluid_maximum", "message": "El volumen prescrito supera el máximo documentado."})
    return alerts


def _serialize(session: Session, row: NutritionPrescriptionOrder) -> dict:
    formula = session.get(EnteralFormulaCatalogItem, row.enteral_formula_id) if row.enteral_formula_id else None
    settings = _settings(session)
    result = _dump(row)
    result.update(
        author_name=session.get(User, row.created_by_user_id).full_name,
        formula=_dump(formula) if formula else None,
        meals=[_dump(item) for item in _children(session, NutritionPrescriptionMeal, row.id)],
        supplements=[_dump(item) for item in _children(session, NutritionPrescriptionSupplement, row.id)],
        progressions=[_dump(item) for item in _children(session, NutritionPrescriptionProgression, row.id)],
        monitoring=[_dump(item) for item in _children(session, NutritionPrescriptionMonitoring, row.id)],
    )
    result["coverage"] = _coverage(row, settings)
    result["alerts"] = _alerts(row, result["coverage"])
    changes: list[dict] = []
    if row.supersedes_order_id:
        previous = session.get(NutritionPrescriptionOrder, row.supersedes_order_id)
        if previous:
            for field, label in DIFF_FIELDS.items():
                before, after = getattr(previous, field), getattr(row, field)
                if before != after:
                    changes.append({"field": field, "label": label, "before": before, "after": after})
            child_labels = (
                (NutritionPrescriptionMeal, "Tiempos de comida"),
                (NutritionPrescriptionSupplement, "Suplementos y módulos"),
                (NutritionPrescriptionProgression, "Progresión enteral"),
                (NutritionPrescriptionMonitoring, "Monitoreo"),
            )
            for model, label in child_labels:
                before_count = len(_children(session, model, previous.id))
                after_count = len(_children(session, model, row.id))
                if before_count != after_count:
                    changes.append({"field": model.__tablename__, "label": label, "before": before_count, "after": after_count})
    result["changes"] = changes
    return result


def _replace_children(session: Session, row: NutritionPrescriptionOrder, payload) -> None:
    for model in CHILD_MODELS:
        session.exec(delete(model).where(model.order_id == row.id))
    session.flush()
    for item in payload.meals:
        session.add(NutritionPrescriptionMeal(order_id=row.id, **item.model_dump()))
    for item in payload.supplements:
        session.add(NutritionPrescriptionSupplement(order_id=row.id, **item.model_dump()))
    for item in payload.progressions:
        session.add(NutritionPrescriptionProgression(order_id=row.id, **item.model_dump()))
    for item in payload.monitoring:
        session.add(NutritionPrescriptionMonitoring(order_id=row.id, **item.model_dump()))


def _recipe(session: Session, row: NutritionPrescriptionOrder) -> str:
    parts: list[str] = []
    if row.fasting_enabled:
        parts.append("Régimen cero transitorio.")
    if row.oral_enabled:
        oral = f"Alimentación oral: {row.regimen_type or 'régimen individualizado'}"
        if row.food_iddsi is not None:
            oral += f", alimentos IDDSI {row.food_iddsi}"
        if row.liquid_iddsi is not None:
            oral += f", líquidos IDDSI {row.liquid_iddsi}"
        parts.append(oral + ".")
    if row.enteral_enabled:
        formula = session.get(EnteralFormulaCatalogItem, row.enteral_formula_id) if row.enteral_formula_id else None
        text = f"Nutrición enteral con {formula.display_name if formula else 'fórmula por confirmar'}"
        if row.enteral_access_route:
            text += f" por {row.enteral_access_route}"
        if row.enteral_modality:
            text += f", modalidad {row.enteral_modality}"
        if row.enteral_rate_ml_h and row.enteral_effective_hours:
            text += f" a {row.enteral_rate_ml_h:g} mL/h durante {row.enteral_effective_hours:g} horas efectivas"
        text += f". Volumen {row.enteral_volume_ml:g} mL/día."
        if row.water_flush_ml and row.water_flush_every_hours:
            text += f" Lavados de {row.water_flush_ml:g} mL cada {row.water_flush_every_hours:g} horas."
        parts.append(text)
    supplements = _children(session, NutritionPrescriptionSupplement, row.id)
    for item in supplements:
        dose = f" {item.dose:g} {item.dose_unit}" if item.dose is not None and item.dose_unit else ""
        schedule = f" {item.schedule}" if item.schedule else ""
        parts.append(f"Agregar {item.product_name}{dose}{schedule}.")
    if row.restrictions:
        parts.append(f"Restricciones: {row.restrictions}.")
    if row.nursing_instructions:
        parts.append(row.nursing_instructions.rstrip(".") + ".")
    monitoring = _children(session, NutritionPrescriptionMonitoring, row.id)
    if monitoring:
        parts.append("Monitorear " + "; ".join(f"{item.parameter} {item.frequency}" for item in monitoring) + ".")
    parts.append(f"Aporte calculado: {row.prescribed_energy_kcal:g} kcal, {row.prescribed_protein_g:g} g de proteína y {row.prescribed_fluid_ml:g} mL de volumen/día.")
    return " ".join(parts)


def _recalculate(session: Session, row: NutritionPrescriptionOrder) -> None:
    energy = row.oral_energy_kcal if row.oral_enabled else Decimal(0)
    protein = row.oral_protein_g if row.oral_enabled else Decimal(0)
    carbohydrate = row.oral_carbohydrate_g if row.oral_enabled else Decimal(0)
    lipid = row.oral_lipid_g if row.oral_enabled else Decimal(0)
    fluid = row.oral_fluid_ml if row.oral_enabled else Decimal(0)
    row.enteral_volume_ml = Decimal(0)
    if row.enteral_enabled and row.enteral_rate_ml_h and row.enteral_effective_hours:
        volume = row.enteral_rate_ml_h * row.enteral_effective_hours
        row.enteral_volume_ml = volume.quantize(Q, rounding=ROUND_HALF_UP)
        formula = session.get(EnteralFormulaCatalogItem, row.enteral_formula_id) if row.enteral_formula_id else None
        if formula:
            liters = volume / 1000
            energy += volume * formula.kcal_per_ml
            protein += liters * formula.protein_g_per_l
            carbohydrate += liters * formula.carbohydrate_g_per_l
            lipid += liters * formula.lipid_g_per_l
            fluid += liters * formula.free_water_ml_per_l
    flush_volume = Decimal(0)
    if row.water_flush_ml and row.water_flush_every_hours:
        flush_volume = row.water_flush_ml * (Decimal(24) / row.water_flush_every_hours)
        fluid += flush_volume
    for item in _children(session, NutritionPrescriptionSupplement, row.id):
        energy += item.energy_kcal
        protein += item.protein_g
        carbohydrate += item.carbohydrate_g
        lipid += item.lipid_g
        fluid += item.fluid_ml
    row.prescribed_energy_kcal = energy.quantize(Q, rounding=ROUND_HALF_UP)
    row.prescribed_protein_g = protein.quantize(Q, rounding=ROUND_HALF_UP)
    row.prescribed_carbohydrate_g = carbohydrate.quantize(Q, rounding=ROUND_HALF_UP)
    row.prescribed_lipid_g = lipid.quantize(Q, rounding=ROUND_HALF_UP)
    row.prescribed_fluid_ml = fluid.quantize(Q, rounding=ROUND_HALF_UP)
    session.add(row)
    session.flush()
    row.recipe_text = _recipe(session, row)
    session.add(row)


def _apply_data(row: NutritionPrescriptionOrder, payload) -> None:
    data = payload.model_dump(exclude=NESTED_FIELDS | {"expected_lock_version", "supersedes_order_id"})
    for key, value in data.items():
        setattr(row, key, value)


def create_order(session: Session, admission_id: uuid.UUID, payload: PrescriptionOrderCreate, actor_id: uuid.UUID) -> dict:
    _admission(session, admission_id, active=True)
    if payload.supersedes_order_id:
        previous = _order(session, payload.supersedes_order_id)
        if previous.admission_id != admission_id:
            raise _invalid("La versión anterior pertenece a otro episodio.")
    max_version = session.exec(select(func.max(NutritionPrescriptionOrder.version_number)).where(NutritionPrescriptionOrder.admission_id == admission_id)).one()
    row = NutritionPrescriptionOrder(
        admission_id=admission_id,
        version_number=int(max_version or 0) + 1,
        supersedes_order_id=payload.supersedes_order_id,
        change_reason=payload.change_reason,
        created_by_user_id=actor_id,
    )
    _apply_data(row, payload)
    session.add(row)
    session.flush()
    _replace_children(session, row, payload)
    session.flush()
    _recalculate(session, row)
    record_audit(session, action="nutrition_prescription_draft_created", actor_user_id=actor_id, entity_type="nutrition_prescription_order", entity_id=row.id, admission_id=admission_id, after_state={"status": row.status, "version": row.version_number, "lock_version": row.lock_version})
    session.commit()
    return _serialize(session, row)


def update_order(session: Session, order_id: uuid.UUID, payload: PrescriptionOrderUpdate, actor_id: uuid.UUID, roles: frozenset[str]) -> dict:
    row = _order(session, order_id)
    _admission(session, row.admission_id, active=True)
    _ensure_version(row, payload.expected_lock_version)
    if row.status != "draft":
        raise _conflict("Sólo los borradores pueden editarse.")
    if row.created_by_user_id != actor_id and "jefatura" not in roles:
        raise HTTPException(status_code=403, detail="Sólo el autor o jefatura puede editar este borrador.")
    before = row.model_dump()
    _apply_data(row, payload)
    row.lock_version += 1
    row.updated_at = utc_now()
    session.add(row)
    _replace_children(session, row, payload)
    session.flush()
    _recalculate(session, row)
    changed = sorted(key for key, value in before.items() if getattr(row, key, None) != value)
    record_audit(session, action="nutrition_prescription_draft_updated", actor_user_id=actor_id, entity_type="nutrition_prescription_order", entity_id=row.id, admission_id=row.admission_id, after_state={"status": row.status, "version": row.version_number, "lock_version": row.lock_version, "changed_fields": changed})
    session.commit()
    return _serialize(session, row)


def _validate_content(session: Session, row: NutritionPrescriptionOrder) -> None:
    if not (row.oral_enabled or row.enteral_enabled or row.fasting_enabled):
        raise _invalid("Seleccione una estrategia antes de validar.")
    if row.fasting_enabled and (row.oral_enabled or row.enteral_enabled or _children(session, NutritionPrescriptionSupplement, row.id)):
        raise _invalid("El régimen cero debe prescribirse sin aportes nutricionales simultáneos.")
    if row.oral_enabled and not row.regimen_type:
        raise _invalid("La estrategia oral requiere un tipo de régimen.")
    if row.enteral_enabled:
        if not row.enteral_formula_id:
            raise _invalid("La estrategia enteral requiere una fórmula del catálogo.")
        if not row.enteral_rate_ml_h or not row.enteral_effective_hours:
            raise _invalid("Informe velocidad y horas efectivas de nutrición enteral.")


def validate_order(session: Session, order_id: uuid.UUID, payload: PrescriptionAction, actor_id: uuid.UUID, roles: frozenset[str]) -> dict:
    row = _order(session, order_id)
    _admission(session, row.admission_id, active=True)
    _ensure_version(row, payload.expected_lock_version)
    if row.status != "draft":
        raise _conflict("Sólo un borrador puede validarse.")
    if row.created_by_user_id != actor_id and "jefatura" not in roles:
        raise HTTPException(status_code=403, detail="Sólo el autor o jefatura puede validar este borrador.")
    _validate_content(session, row)
    _recalculate(session, row)
    row.status = "validated"
    row.validated_by_user_id = actor_id
    row.validated_at = utc_now()
    row.updated_at = row.validated_at
    row.lock_version += 1
    session.add(row)
    record_audit(session, action="nutrition_prescription_validated", actor_user_id=actor_id, entity_type="nutrition_prescription_order", entity_id=row.id, admission_id=row.admission_id, after_state={"status": row.status, "version": row.version_number, "lock_version": row.lock_version})
    session.commit()
    return _serialize(session, row)


def activate_order(session: Session, order_id: uuid.UUID, payload: PrescriptionAction, actor_id: uuid.UUID) -> dict:
    row = _order(session, order_id)
    _admission(session, row.admission_id, active=True)
    _ensure_version(row, payload.expected_lock_version)
    if row.status != "validated":
        raise _conflict("Sólo una prescripción validada puede activarse.")
    now = utc_now()
    current = session.exec(select(NutritionPrescriptionOrder).where(NutritionPrescriptionOrder.admission_id == row.admission_id, NutritionPrescriptionOrder.status == "active")).first()
    if current and current.id != row.id:
        current.status = "superseded"
        current.updated_at = now
        current.lock_version += 1
        session.add(current)
        session.flush()
    row.status = "active"
    row.effective_from = row.effective_from or now
    row.activated_at = now
    row.activated_by_user_id = actor_id
    row.updated_at = now
    row.lock_version += 1
    session.add(row)
    record_audit(session, action="nutrition_prescription_activated", actor_user_id=actor_id, entity_type="nutrition_prescription_order", entity_id=row.id, admission_id=row.admission_id, after_state={"status": row.status, "version": row.version_number, "replaced_order_id": str(current.id) if current else None})
    session.commit()
    return _serialize(session, row)


def suspend_order(session: Session, order_id: uuid.UUID, payload: PrescriptionSuspension, actor_id: uuid.UUID) -> dict:
    row = _order(session, order_id)
    _admission(session, row.admission_id, active=True)
    _ensure_version(row, payload.expected_lock_version)
    if row.status != "active":
        raise _conflict("Sólo una prescripción activa puede suspenderse.")
    row.status = "suspended"
    row.suspension_reason = payload.reason
    row.suspended_by_user_id = actor_id
    row.suspended_at = utc_now()
    row.updated_at = row.suspended_at
    row.lock_version += 1
    session.add(row)
    record_audit(session, action="nutrition_prescription_suspended", actor_user_id=actor_id, entity_type="nutrition_prescription_order", entity_id=row.id, admission_id=row.admission_id, after_state={"status": row.status, "version": row.version_number, "lock_version": row.lock_version})
    session.commit()
    return _serialize(session, row)


def clone_order(session: Session, order_id: uuid.UUID, payload: PrescriptionClone, actor_id: uuid.UUID) -> dict:
    source = _order(session, order_id)
    _admission(session, source.admission_id, active=True)
    source_data = source.model_dump(exclude={
        "id", "admission_id", "version_number", "lock_version", "status", "supersedes_order_id",
        "created_by_user_id", "validated_by_user_id", "activated_by_user_id", "suspended_by_user_id",
        "created_at", "updated_at", "validated_at", "activated_at", "suspended_at", "suspension_reason",
        "prescribed_energy_kcal", "prescribed_protein_g", "prescribed_carbohydrate_g",
        "prescribed_lipid_g", "prescribed_fluid_ml", "enteral_volume_ml", "recipe_text", "change_reason",
    })
    source_data.update(
        change_reason=payload.reason,
        supersedes_order_id=source.id,
        meals=[{k: v for k, v in item.model_dump().items() if k not in {"id", "order_id"}} for item in _children(session, NutritionPrescriptionMeal, source.id)],
        supplements=[{k: v for k, v in item.model_dump().items() if k not in {"id", "order_id"}} for item in _children(session, NutritionPrescriptionSupplement, source.id)],
        progressions=[{k: v for k, v in item.model_dump().items() if k not in {"id", "order_id"}} for item in _children(session, NutritionPrescriptionProgression, source.id)],
        monitoring=[{k: v for k, v in item.model_dump().items() if k not in {"id", "order_id"}} for item in _children(session, NutritionPrescriptionMonitoring, source.id)],
    )
    return create_order(session, source.admission_id, PrescriptionOrderCreate.model_validate(source_data), actor_id)


def workspace(session: Session, admission_id: uuid.UUID, actor_id: uuid.UUID, roles: frozenset[str]) -> dict:
    _admission(session, admission_id)
    orders = list(session.exec(select(NutritionPrescriptionOrder).where(NutritionPrescriptionOrder.admission_id == admission_id).order_by(NutritionPrescriptionOrder.version_number.desc())).all())
    active = next((row for row in orders if row.status == "active"), None)
    drafts = [row for row in orders if row.status == "draft" and (row.created_by_user_id == actor_id or "jefatura" in roles)]
    final_encounters = select(NutritionalCareEncounter.id).where(NutritionalCareEncounter.admission_id == admission_id, NutritionalCareEncounter.status.in_(("finalized", "corrected")))
    requirements = list(session.exec(select(NutritionalRequirementCalculation).where(NutritionalRequirementCalculation.encounter_id.in_(final_encounters)).order_by(NutritionalRequirementCalculation.created_at.desc())).all())
    latest_by_code: dict[str, dict] = {}
    for requirement in requirements:
        latest_by_code.setdefault(requirement.nutrient_code, _dump(requirement))
    formulas = list(session.exec(select(EnteralFormulaCatalogItem).where(EnteralFormulaCatalogItem.is_active == True).order_by(EnteralFormulaCatalogItem.display_name)).all())  # noqa: E712
    return {
        "admission_id": admission_id,
        "requirements": list(latest_by_code.values()),
        "settings": _settings(session),
        "formulas": formulas,
        "active": _serialize(session, active) if active else None,
        "drafts": [_serialize(session, row) for row in drafts],
        "history": [_serialize(session, row) for row in orders if row.status != "draft"],
    }


def create_formula(session: Session, payload: FormulaCatalogCreate, actor_id: uuid.UUID) -> EnteralFormulaCatalogItem:
    duplicate = session.exec(select(EnteralFormulaCatalogItem).where(EnteralFormulaCatalogItem.code == payload.code, EnteralFormulaCatalogItem.catalog_version == payload.catalog_version)).first()
    if duplicate:
        raise _conflict("Ya existe esa versión de la fórmula.")
    row = EnteralFormulaCatalogItem(**payload.model_dump(), created_by_user_id=actor_id)
    session.add(row)
    session.flush()
    record_audit(session, action="enteral_formula_catalog_created", actor_user_id=actor_id, entity_type="enteral_formula_catalog_item", entity_id=row.id, after_state={"code": row.code, "catalog_version": row.catalog_version, "is_active": True})
    session.commit()
    session.refresh(row)
    return row


def update_settings(session: Session, payload: PrescriptionSettingsUpdate, actor_id: uuid.UUID) -> NutritionPrescriptionSetting:
    row = _settings(session)
    for key, value in payload.model_dump().items():
        setattr(row, key, value)
    row.updated_by_user_id = actor_id
    row.updated_at = utc_now()
    session.add(row)
    record_audit(session, action="nutrition_prescription_settings_updated", actor_user_id=actor_id, entity_type="nutrition_prescription_settings", after_state={"updated": True})
    session.commit()
    session.refresh(row)
    return row
