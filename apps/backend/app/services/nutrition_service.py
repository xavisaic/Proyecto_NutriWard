import uuid
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Iterable

from fastapi import HTTPException, status
from sqlalchemy import delete
from sqlmodel import Session, select

from app.models.admission import Admission
from app.models.common import utc_now
from app.models.nutrition import (
    NutritionalAlert,
    NutritionalAnthropometricMeasurement,
    NutritionalAssessment,
    NutritionalCareEncounter,
    NutritionalClinicalContextItem,
    NutritionalDiagnosis,
    NutritionalIntakeRecord,
    NutritionalLabObservation,
    NutritionalMonitoringRecord,
    NutritionalPrescription,
    NutritionalPrescriptionMealTime,
    NutritionalRequirementCalculation,
    NutritionalScreening,
    NutritionalScreeningAnswer,
)
from app.models.user import User
from app.schemas.nutrition import (
    CancellationCreate,
    CorrectionCreate,
    NutritionCatalogs,
    NutritionEncounterCreate,
    NutritionEncounterList,
    NutritionEncounterPatch,
    NutritionEncounterRead,
    NutritionEncounterSummary,
    NutritionLatest,
    NutritionProjectionList,
    VersionedAction,
)
from app.services.audit_service import record_audit

FINAL_STATUSES = ("finalized", "corrected")

MODEL_GROUPS = {
    "context_items": NutritionalClinicalContextItem,
    "anthropometry": NutritionalAnthropometricMeasurement,
    "requirements": NutritionalRequirementCalculation,
    "diagnoses": NutritionalDiagnosis,
    "monitoring": NutritionalMonitoringRecord,
    "intake": NutritionalIntakeRecord,
    "labs": NutritionalLabObservation,
    "alerts": NutritionalAlert,
}


def _not_found(message: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)


def _conflict(message: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message)


def _invalid(message: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=message)


def _admission(session: Session, admission_id: uuid.UUID) -> Admission:
    admission = session.get(Admission, admission_id)
    if admission is None:
        raise _not_found("Hospitalización no encontrada.")
    return admission


def _encounter(session: Session, encounter_id: uuid.UUID) -> NutritionalCareEncounter:
    encounter = session.get(NutritionalCareEncounter, encounter_id)
    if encounter is None:
        raise _not_found("Atención nutricional no encontrada.")
    return encounter


def _user_name(session: Session, user_id: uuid.UUID | None) -> str | None:
    if user_id is None:
        return None
    user = session.get(User, user_id)
    return user.full_name if user else "Profesional no disponible"


def _dump(row: Any) -> dict[str, Any]:
    return row.model_dump(exclude={"password_hash"})


def _ensure_draft_access(
    encounter: NutritionalCareEncounter,
    actor_id: uuid.UUID,
    roles: frozenset[str],
) -> None:
    if encounter.status != "draft":
        raise _conflict("La atención ya no es un borrador editable.")
    if encounter.author_professional_id != actor_id and "jefatura" not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sólo el autor del borrador o jefatura puede modificarlo.",
        )


def _ensure_version(encounter: NutritionalCareEncounter, version: int) -> None:
    if encounter.version != version:
        raise _conflict(
            "El borrador fue modificado en otra sesión. Recargue antes de continuar."
        )


def _ensure_active(admission: Admission) -> None:
    if admission.status != "active":
        raise _conflict("Los episodios históricos son de solo lectura.")


def _rows(session: Session, model: type, encounter_id: uuid.UUID) -> list[Any]:
    return list(session.exec(select(model).where(model.encounter_id == encounter_id)).all())


def _screening_score(tool_code: str, answers: list[Any]) -> tuple[str, Decimal | None, str | None, dict[str, Decimal | None]]:
    values = {answer.answer_code: answer.answer_value.strip().lower() for answer in answers}
    if tool_code == "none":
        return "no-tool-v1", None, None, {code: None for code in values}
    if tool_code == "nrs_2002":
        initial_codes = (
            "initial_bmi_below_20_5",
            "initial_weight_loss_3_months",
            "initial_reduced_intake_last_week",
            "initial_severely_ill",
        )
        initial_present = all(code in values for code in initial_codes)
        if initial_present:
            initial_components = {
                code: Decimal(
                    int(values[code] in ("true", "1", "yes", "si", "sí"))
                )
                for code in initial_codes
            }
            if not any(initial_components.values()):
                return "espen-nrs2002-v1", Decimal(0), "initial_screen_negative", initial_components
        else:
            initial_components = {}
        try:
            nutritional = int(values["nutritional_status_score"])
            disease = int(values["disease_severity_score"])
        except (KeyError, ValueError) as exc:
            raise _invalid(
                "NRS-2002 requiere nutritional_status_score y disease_severity_score."
            ) from exc
        if nutritional not in range(4) or disease not in range(4):
            raise _invalid("Los componentes NRS-2002 deben estar entre 0 y 3.")
        age = values.get("age_70_or_more", "false") in ("true", "1", "yes", "si", "sí")
        total = Decimal(nutritional + disease + int(age))
        components = {
            **initial_components,
            "nutritional_status_score": Decimal(nutritional),
            "disease_severity_score": Decimal(disease),
            "age_70_or_more": Decimal(int(age)),
        }
        return "espen-nrs2002-v1", total, "nutritional_risk" if total >= 3 else "no_nutritional_risk", components
    if tool_code == "strongkids":
        weights = {
            "subjective_clinical_assessment": 1,
            "high_risk_disease": 2,
            "nutritional_intake_or_losses": 1,
            "weight_loss_or_poor_gain": 1,
        }
        missing = set(weights) - set(values)
        if missing:
            raise _invalid("STRONGkids requiere sus cuatro componentes estructurados.")
        components: dict[str, Decimal] = {}
        for code, weight in weights.items():
            selected = values[code] in ("true", "1", "yes", "si", "sí")
            components[code] = Decimal(weight if selected else 0)
        total = sum(components.values(), Decimal(0))
        classification = "low" if total == 0 else "medium" if total <= 3 else "high"
        return "strongkids-original-v1", total, classification, components
    raise _invalid("La herramienta de tamizaje no está configurada.")


def _requirement_result(method: str, inputs: dict[str, Any]) -> tuple[Decimal, Decimal | None, str, str]:
    def number(key: str) -> Decimal:
        try:
            return Decimal(str(inputs[key]))
        except (KeyError, ValueError, TypeError) as exc:
            raise _invalid(f"Falta una entrada numérica válida: {key}.") from exc

    if method == "factorial":
        basal = number("basal_result")
        activity = number("activity_factor")
        stress = number("stress_factor")
        thermal = Decimal(str(inputs.get("thermal_factor", 1)))
        result = basal * activity * stress * thermal
        return result, basal, "factorial-v1", "Resultado basal × actividad × estrés × factor térmico"
    if method == "kcal_per_kg":
        result = number("weight_kg") * number("kcal_per_kg")
        return result, None, "kcal-kg-v1", "peso (kg) × kcal/kg"
    if method == "mifflin_st_jeor":
        weight, height, age = number("weight_kg"), number("height_cm"), number("age_years")
        sex = str(inputs.get("sex", ""))
        offset = Decimal(5) if sex == "male" else Decimal(-161) if sex == "female" else None
        if offset is None:
            raise _invalid("Mifflin-St Jeor requiere sexo female o male.")
        result = Decimal(10) * weight + Decimal("6.25") * height - Decimal(5) * age + offset
        return result, result, "mifflin-st-jeor-1990", "10W + 6.25H - 5A + ajuste por sexo"
    if method == "harris_benedict":
        weight, height, age = number("weight_kg"), number("height_cm"), number("age_years")
        sex = str(inputs.get("sex", ""))
        if sex == "male":
            result = Decimal("88.362") + Decimal("13.397") * weight + Decimal("4.799") * height - Decimal("5.677") * age
        elif sex == "female":
            result = Decimal("447.593") + Decimal("9.247") * weight + Decimal("3.098") * height - Decimal("4.330") * age
        else:
            raise _invalid("Harris-Benedict requiere sexo female o male.")
        return result, result, "harris-benedict-revised-1984", "Ecuación revisada de Roza y Shizgal"
    if method == "schofield":
        weight, age = number("weight_kg"), number("age_years")
        sex = str(inputs.get("sex", ""))
        if age < 18:
            raise _invalid("Schofield pediátrico no está habilitado sin referencia local validada.")
        factors = {
            "male": ((30, Decimal("0.063"), Decimal("2.896")), (60, Decimal("0.048"), Decimal("3.653")), (999, Decimal("0.049"), Decimal("2.459"))),
            "female": ((30, Decimal("0.062"), Decimal("2.036")), (60, Decimal("0.034"), Decimal("3.538")), (999, Decimal("0.038"), Decimal("2.755"))),
        }
        if sex not in factors:
            raise _invalid("Schofield requiere sexo female o male.")
        _, coefficient, constant = next(row for row in factors[sex] if age < row[0])
        result = (coefficient * weight + constant) * Decimal("239.005736")
        return result, result, "schofield-1985-adult", "Ecuación Schofield en MJ/d convertida a kcal/d"
    if method in ("indirect_calorimetry", "manual", "other"):
        result = number("measured_or_manual_value")
        return result, result, f"{method}-v1", "Valor medido o razonado documentado"
    raise _invalid("El método de requerimiento no está configurado.")


def _replace_assessment(session: Session, encounter: NutritionalCareEncounter, payload: Any) -> None:
    existing = session.exec(
        select(NutritionalAssessment).where(NutritionalAssessment.encounter_id == encounter.id)
    ).first()
    if payload is None:
        if existing:
            session.delete(existing)
        return
    values = payload.model_dump()
    values["observed_at"] = values["observed_at"] or encounter.encounter_datetime
    values.update(
        admission_id=encounter.admission_id,
        encounter_id=encounter.id,
        author_professional_id=encounter.author_professional_id,
        updated_at=utc_now(),
    )
    if existing:
        for key, value in values.items():
            setattr(existing, key, value)
        session.add(existing)
    else:
        session.add(NutritionalAssessment(**values))


def _replace_simple_rows(
    session: Session,
    encounter: NutritionalCareEncounter,
    field_name: str,
    payloads: Iterable[Any],
) -> None:
    model = MODEL_GROUPS[field_name]
    session.exec(delete(model).where(model.encounter_id == encounter.id))
    session.flush()
    for payload in payloads:
        values = payload.model_dump()
        values.update(
            admission_id=encounter.admission_id,
            encounter_id=encounter.id,
            author_professional_id=encounter.author_professional_id,
        )
        if field_name == "diagnoses":
            values["generated_statement"] = (
                f"{values['problem']} relacionado con {values['etiology']}, "
                f"evidenciado por {values['signs_and_symptoms']}"
            )
        session.add(model(**values))


def _replace_anthropometry(session: Session, encounter: NutritionalCareEncounter, payloads: Iterable[Any]) -> None:
    _replace_simple_rows(session, encounter, "anthropometry", payloads)
    session.flush()
    rows = _rows(session, NutritionalAnthropometricMeasurement, encounter.id)
    current_weights = [r for r in rows if r.measurement_type in ("current_weight_measured", "current_weight_reported") and r.unit == "kg"]
    heights = [r for r in rows if r.measurement_type in ("standing_height", "recumbent_length", "estimated_height") and r.unit in ("cm", "m")]
    if current_weights and heights:
        weight = max(current_weights, key=lambda item: item.measured_at)
        height = max(heights, key=lambda item: item.measured_at)
        metres = height.value / Decimal(100) if height.unit == "cm" else height.value
        if metres > 0:
            bmi = (weight.value / (metres * metres)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            session.add(NutritionalAnthropometricMeasurement(
                admission_id=encounter.admission_id,
                encounter_id=encounter.id,
                measurement_type="body_mass_index",
                value=bmi,
                unit="kg/m2",
                measured_at=max(weight.measured_at, height.measured_at),
                method="weight_kg / height_m²",
                source="backend_calculation",
                reliability="unknown",
                value_nature="calculated",
                author_professional_id=encounter.author_professional_id,
                calculated_value=bmi,
            ))
    usual_weights = [r for r in rows if r.measurement_type == "usual_weight" and r.unit == "kg"]
    if current_weights and usual_weights:
        current = max(current_weights, key=lambda item: item.measured_at)
        usual = max(usual_weights, key=lambda item: item.measured_at)
        if usual.value > 0:
            change = ((current.value - usual.value) / usual.value * Decimal(100)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            session.add(NutritionalAnthropometricMeasurement(
                admission_id=encounter.admission_id,
                encounter_id=encounter.id,
                measurement_type="weight_change_percentage",
                value=abs(change),
                unit="%",
                measured_at=current.measured_at,
                method="(current_weight - usual_weight) / usual_weight × 100",
                source="backend_calculation",
                reliability="unknown",
                value_nature="calculated",
                author_professional_id=encounter.author_professional_id,
                observations="El signo y el intervalo se conservan en el método y fechas de origen.",
                calculated_value=change,
            ))


def _replace_screenings(session: Session, encounter: NutritionalCareEncounter, payloads: Iterable[Any]) -> None:
    previous = _rows(session, NutritionalScreening, encounter.id)
    for screening in previous:
        session.exec(delete(NutritionalScreeningAnswer).where(NutritionalScreeningAnswer.screening_id == screening.id))
    session.exec(delete(NutritionalScreening).where(NutritionalScreening.encounter_id == encounter.id))
    session.flush()
    for payload in payloads:
        algorithm, total, classification, components = _screening_score(payload.tool_code, payload.answers)
        snapshot = {answer.answer_code: answer.answer_value for answer in payload.answers}
        screening = NutritionalScreening(
            admission_id=encounter.admission_id,
            encounter_id=encounter.id,
            tool_code=payload.tool_code,
            tool_version=payload.tool_version,
            algorithm_version=algorithm,
            total_score=total,
            classification=classification,
            no_tool_reason=payload.no_tool_reason,
            applied_at=payload.applied_at,
            author_professional_id=encounter.author_professional_id,
            inputs_snapshot=snapshot,
        )
        session.add(screening)
        session.flush()
        for answer in payload.answers:
            session.add(NutritionalScreeningAnswer(
                screening_id=screening.id,
                answer_code=answer.answer_code,
                answer_value=answer.answer_value,
                component_score=components.get(answer.answer_code),
            ))


def _replace_requirements(session: Session, encounter: NutritionalCareEncounter, payloads: Iterable[Any]) -> None:
    session.exec(delete(NutritionalRequirementCalculation).where(NutritionalRequirementCalculation.encounter_id == encounter.id))
    session.flush()
    measurements = {row.id: row for row in _rows(session, NutritionalAnthropometricMeasurement, encounter.id)}
    assessment = session.exec(
        select(NutritionalAssessment).where(NutritionalAssessment.encounter_id == encounter.id)
    ).first()
    population = assessment.population_group if assessment else None
    adult_only = {"factorial", "kcal_per_kg", "mifflin_st_jeor", "harris_benedict", "schofield"}
    for payload in payloads:
        if population and population != "adult" and payload.method in adult_only:
            raise _invalid(
                "Este método no está validado localmente para la población seleccionada; use cálculo manual razonado o un valor medido."
            )
        result, basal, formula_version, equation = _requirement_result(payload.method, payload.inputs)
        result = result.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        adopted = payload.adopted_result if payload.adopted_result is not None else result
        measurement = measurements.get(payload.weight_measurement_id) if payload.weight_measurement_id else None
        if payload.weight_measurement_id and measurement is None:
            raise _invalid("El peso seleccionado no pertenece a esta atención y hospitalización.")
        session.add(NutritionalRequirementCalculation(
            admission_id=encounter.admission_id,
            encounter_id=encounter.id,
            nutrient_code=payload.nutrient_code,
            method=payload.method,
            formula_version=formula_version,
            reference=_requirement_reference(payload.method),
            base_equation=equation,
            weight_measurement_id=measurement.id if measurement else None,
            weight_type=measurement.measurement_type if measurement else None,
            weight_value=measurement.value if measurement else payload.inputs.get("weight_kg"),
            weight_measured_at=measurement.measured_at if measurement else None,
            weight_selection_reason=payload.weight_selection_reason,
            activity_factor=payload.inputs.get("activity_factor"),
            stress_factor=payload.inputs.get("stress_factor"),
            thermal_factor=payload.inputs.get("thermal_factor"),
            basal_result=basal,
            automatic_result=result,
            adopted_result=adopted,
            minimum_result=payload.minimum_result,
            maximum_result=payload.maximum_result,
            unit=payload.unit,
            rounding="0.01 half-up",
            was_manually_adjusted=payload.adopted_result is not None and payload.adopted_result != result,
            manual_adjustment_reason=payload.manual_adjustment_reason,
            inputs_snapshot={key: str(value) for key, value in payload.inputs.items()},
            author_professional_id=encounter.author_professional_id,
        ))


def _requirement_reference(method: str) -> str:
    return {
        "mifflin_st_jeor": "Mifflin MD et al. Am J Clin Nutr. 1990;51:241-247.",
        "harris_benedict": "Roza AM, Shizgal HM. Am J Clin Nutr. 1984;40:168-182.",
        "schofield": "Schofield WN. Hum Nutr Clin Nutr. 1985;39 Suppl 1:5-41.",
        "factorial": "Método factorial: factores seleccionados y confirmados por profesional.",
        "kcal_per_kg": "Método kcal/kg: tasa y peso seleccionados por profesional.",
        "indirect_calorimetry": "Valor medido por calorimetría indirecta.",
        "manual": "Cálculo manual razonado por profesional.",
        "other": "Otro método documentado por profesional.",
    }.get(method, "Método documentado por profesional.")


def _replace_prescription(session: Session, encounter: NutritionalCareEncounter, payload: Any) -> None:
    existing = session.exec(select(NutritionalPrescription).where(NutritionalPrescription.encounter_id == encounter.id)).first()
    if existing:
        session.exec(delete(NutritionalPrescriptionMealTime).where(NutritionalPrescriptionMealTime.prescription_id == existing.id))
        session.delete(existing)
        session.flush()
    if payload is None:
        return
    values = payload.model_dump(exclude={"meal_times"})
    values.update(admission_id=encounter.admission_id, encounter_id=encounter.id, author_professional_id=encounter.author_professional_id)
    prescription = NutritionalPrescription(**values)
    session.add(prescription)
    session.flush()
    for meal in payload.meal_times:
        session.add(NutritionalPrescriptionMealTime(prescription_id=prescription.id, **meal.model_dump()))


def _apply_payload(session: Session, encounter: NutritionalCareEncounter, payload: Any, *, creating: bool) -> None:
    fields = payload.model_fields_set if not creating else set(type(payload).model_fields)
    for name in ("encounter_datetime", "encounter_type", "clinical_summary", "reason_for_assessment", "information_source"):
        if name in fields:
            value = getattr(payload, name)
            if name == "encounter_datetime" and value is None:
                continue
            setattr(encounter, name, value)
    if "assessment" in fields:
        _replace_assessment(session, encounter, payload.assessment)
    if "anthropometry" in fields:
        _replace_anthropometry(session, encounter, payload.anthropometry)
    if "screenings" in fields:
        _replace_screenings(session, encounter, payload.screenings)
    if "requirements" in fields:
        _replace_requirements(session, encounter, payload.requirements)
    if "prescription" in fields:
        _replace_prescription(session, encounter, payload.prescription)
    for field_name in ("context_items", "diagnoses", "monitoring", "intake", "labs", "alerts"):
        if field_name in fields:
            _replace_simple_rows(session, encounter, field_name, getattr(payload, field_name))


def create_encounter(
    session: Session,
    admission_id: uuid.UUID,
    payload: NutritionEncounterCreate,
    actor_id: uuid.UUID,
) -> NutritionEncounterRead:
    admission = _admission(session, admission_id)
    _ensure_active(admission)
    encounter = NutritionalCareEncounter(
        admission_id=admission_id,
        encounter_datetime=payload.encounter_datetime or utc_now(),
        encounter_type=payload.encounter_type,
        author_professional_id=actor_id,
        clinical_summary=payload.clinical_summary,
        reason_for_assessment=payload.reason_for_assessment,
        information_source=payload.information_source,
    )
    session.add(encounter)
    session.flush()
    _apply_payload(session, encounter, payload, creating=True)
    record_audit(session, action="nutrition_encounter_created", actor_user_id=actor_id, entity_type="nutritional_care_encounter", entity_id=encounter.id, admission_id=admission_id, after_state={"status": "draft", "version": 1})
    session.commit()
    return get_encounter(session, encounter.id)


def update_encounter(
    session: Session,
    encounter_id: uuid.UUID,
    payload: NutritionEncounterPatch,
    actor_id: uuid.UUID,
    roles: frozenset[str],
) -> NutritionEncounterRead:
    encounter = _encounter(session, encounter_id)
    _ensure_draft_access(encounter, actor_id, roles)
    _ensure_active(_admission(session, encounter.admission_id))
    _ensure_version(encounter, payload.version)
    _apply_payload(session, encounter, payload, creating=False)
    encounter.version += 1
    encounter.updated_at = utc_now()
    session.add(encounter)
    record_audit(session, action="nutrition_encounter_updated", actor_user_id=actor_id, entity_type="nutritional_care_encounter", entity_id=encounter.id, admission_id=encounter.admission_id, after_state={"status": "draft", "version": encounter.version})
    session.commit()
    return get_encounter(session, encounter.id)


def _screening_with_answers(session: Session, screening: NutritionalScreening) -> dict[str, Any]:
    result = _dump(screening)
    result["answers"] = [_dump(row) for row in session.exec(select(NutritionalScreeningAnswer).where(NutritionalScreeningAnswer.screening_id == screening.id).order_by(NutritionalScreeningAnswer.answer_code)).all()]
    return result


def _prescription_with_meals(session: Session, prescription: NutritionalPrescription | None) -> dict[str, Any] | None:
    if prescription is None:
        return None
    result = _dump(prescription)
    result["meal_times"] = [_dump(row) for row in session.exec(select(NutritionalPrescriptionMealTime).where(NutritionalPrescriptionMealTime.prescription_id == prescription.id).order_by(NutritionalPrescriptionMealTime.meal_time, NutritionalPrescriptionMealTime.id)).all()]
    return result


def get_encounter(session: Session, encounter_id: uuid.UUID) -> NutritionEncounterRead:
    encounter = _encounter(session, encounter_id)
    assessment = session.exec(select(NutritionalAssessment).where(NutritionalAssessment.encounter_id == encounter.id)).first()
    screenings = _rows(session, NutritionalScreening, encounter.id)
    prescription = session.exec(select(NutritionalPrescription).where(NutritionalPrescription.encounter_id == encounter.id)).first()
    return NutritionEncounterRead(
        encounter=_dump(encounter),
        author_name=_user_name(session, encounter.author_professional_id) or "Profesional no disponible",
        finalized_by_name=_user_name(session, encounter.finalized_by),
        assessment=_dump(assessment) if assessment else None,
        context_items=[_dump(row) for row in _rows(session, NutritionalClinicalContextItem, encounter.id)],
        anthropometry=[_dump(row) for row in _rows(session, NutritionalAnthropometricMeasurement, encounter.id)],
        screenings=[_screening_with_answers(session, row) for row in screenings],
        requirements=[_dump(row) for row in _rows(session, NutritionalRequirementCalculation, encounter.id)],
        diagnoses=sorted([_dump(row) for row in _rows(session, NutritionalDiagnosis, encounter.id)], key=lambda row: (row["priority"], str(row["id"]))),
        prescription=_prescription_with_meals(session, prescription),
        monitoring=[_dump(row) for row in _rows(session, NutritionalMonitoringRecord, encounter.id)],
        intake=[_dump(row) for row in _rows(session, NutritionalIntakeRecord, encounter.id)],
        labs=[_dump(row) for row in _rows(session, NutritionalLabObservation, encounter.id)],
        alerts=[_dump(row) for row in _rows(session, NutritionalAlert, encounter.id)],
    )


def get_encounter_authorized(
    session: Session,
    encounter_id: uuid.UUID,
    actor_id: uuid.UUID,
    roles: frozenset[str],
) -> NutritionEncounterRead:
    encounter = _encounter(session, encounter_id)
    if (
        encounter.status == "draft"
        and encounter.author_professional_id != actor_id
        and "jefatura" not in roles
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos para consultar este borrador.",
        )
    return get_encounter(session, encounter_id)


def list_encounters(
    session: Session,
    admission_id: uuid.UUID,
    page: int,
    page_size: int,
    actor_id: uuid.UUID | None = None,
    roles: frozenset[str] = frozenset(),
) -> NutritionEncounterList:
    _admission(session, admission_id)
    statement = select(NutritionalCareEncounter).where(
        NutritionalCareEncounter.admission_id == admission_id
    )
    if actor_id is not None and "jefatura" not in roles:
        statement = statement.where(
            (NutritionalCareEncounter.status != "draft")
            | (NutritionalCareEncounter.author_professional_id == actor_id)
        )
    all_rows = list(session.exec(statement.order_by(NutritionalCareEncounter.encounter_datetime.desc(), NutritionalCareEncounter.id.desc())).all())
    start = (page - 1) * page_size
    return NutritionEncounterList(
        items=[
            NutritionEncounterSummary(
                **_dump(row),
                author_name=_user_name(session, row.author_professional_id)
                or "Profesional no disponible",
                documented_sections=_documented_sections(session, row),
            )
            for row in all_rows[start:start + page_size]
        ],
        total=len(all_rows),
        page=page,
        page_size=page_size,
    )


def _documented_sections(
    session: Session, encounter: NutritionalCareEncounter
) -> list[str]:
    sections: list[str] = []
    if encounter.reason_for_assessment or encounter.information_source or encounter.clinical_summary:
        sections.append("context")
    if session.exec(
        select(NutritionalAssessment.id).where(
            NutritionalAssessment.encounter_id == encounter.id
        )
    ).first():
        sections.append("assessment")
    checks = (
        ("anthropometry", NutritionalAnthropometricMeasurement),
        ("screening", NutritionalScreening),
        ("requirements", NutritionalRequirementCalculation),
        ("diagnoses", NutritionalDiagnosis),
        ("prescription", NutritionalPrescription),
        ("monitoring", NutritionalMonitoringRecord),
        ("intake", NutritionalIntakeRecord),
        ("labs", NutritionalLabObservation),
        ("alerts", NutritionalAlert),
    )
    for label, model in checks:
        if session.exec(select(model.id).where(model.encounter_id == encounter.id)).first():
            sections.append(label)
    return sections


def _finalization_errors(session: Session, encounter: NutritionalCareEncounter) -> list[str]:
    errors: list[str] = []
    assessment = session.exec(select(NutritionalAssessment).where(NutritionalAssessment.encounter_id == encounter.id)).first()
    if not encounter.reason_for_assessment:
        errors.append("Contexto: indique el motivo de evaluación.")
    if not encounter.information_source:
        errors.append("Contexto: indique la fuente de información.")
    if not encounter.clinical_summary:
        errors.append("Seguimiento: agregue una síntesis clínica.")
    if encounter.encounter_type == "initial_assessment":
        if assessment is None:
            errors.append("Evaluación inicial: declare la población clínica.")
        screenings = _rows(session, NutritionalScreening, encounter.id)
        if not screenings:
            errors.append(
                "Evaluación inicial: registre un tamizaje o documente que no aplica."
            )
        if not _rows(session, NutritionalDiagnosis, encounter.id):
            errors.append(
                "Evaluación inicial: registre al menos un diagnóstico PES estructurado."
            )
    return errors


def finalize_encounter(session: Session, encounter_id: uuid.UUID, payload: VersionedAction, actor_id: uuid.UUID, roles: frozenset[str]) -> NutritionEncounterRead:
    encounter = _encounter(session, encounter_id)
    _ensure_draft_access(encounter, actor_id, roles)
    _ensure_version(encounter, payload.version)
    _ensure_active(_admission(session, encounter.admission_id))
    errors = _finalization_errors(session, encounter)
    if errors:
        raise _invalid({"message": "La atención está incompleta.", "section_errors": errors})
    now = utc_now()
    encounter.status = "corrected" if encounter.corrected_encounter_id else "finalized"
    encounter.finalized_at = now
    encounter.finalized_by = actor_id
    encounter.updated_at = now
    encounter.version += 1
    session.add(encounter)
    record_audit(session, action="nutrition_encounter_finalized", actor_user_id=actor_id, entity_type="nutritional_care_encounter", entity_id=encounter.id, admission_id=encounter.admission_id, after_state={"status": encounter.status, "version": encounter.version})
    session.commit()
    return get_encounter(session, encounter.id)


def _clone_rows(session: Session, original: NutritionalCareEncounter, clone: NutritionalCareEncounter) -> None:
    assessment = session.exec(select(NutritionalAssessment).where(NutritionalAssessment.encounter_id == original.id)).first()
    if assessment:
        values = _dump(assessment)
        for key in ("id", "encounter_id", "created_at", "updated_at"):
            values.pop(key, None)
        values.update(encounter_id=clone.id, author_professional_id=clone.author_professional_id, created_at=utc_now(), updated_at=utc_now())
        session.add(NutritionalAssessment(**values))
    for model in MODEL_GROUPS.values():
        for row in _rows(session, model, original.id):
            values = _dump(row)
            values.pop("id", None)
            values["encounter_id"] = clone.id
            values["author_professional_id"] = clone.author_professional_id
            if "created_at" in values:
                values["created_at"] = utc_now()
            session.add(model(**values))
    for screening in _rows(session, NutritionalScreening, original.id):
        values = _dump(screening)
        old_id = values.pop("id")
        values.update(encounter_id=clone.id, author_professional_id=clone.author_professional_id, created_at=utc_now())
        new_screening = NutritionalScreening(**values)
        session.add(new_screening)
        session.flush()
        for answer in session.exec(select(NutritionalScreeningAnswer).where(NutritionalScreeningAnswer.screening_id == old_id)).all():
            session.add(NutritionalScreeningAnswer(screening_id=new_screening.id, answer_code=answer.answer_code, answer_value=answer.answer_value, component_score=answer.component_score))
    prescription = session.exec(select(NutritionalPrescription).where(NutritionalPrescription.encounter_id == original.id)).first()
    if prescription:
        values = _dump(prescription)
        old_id = values.pop("id")
        values.update(encounter_id=clone.id, author_professional_id=clone.author_professional_id, created_at=utc_now())
        new_prescription = NutritionalPrescription(**values)
        session.add(new_prescription)
        session.flush()
        for meal in session.exec(select(NutritionalPrescriptionMealTime).where(NutritionalPrescriptionMealTime.prescription_id == old_id)).all():
            meal_values = _dump(meal)
            meal_values.pop("id")
            meal_values["prescription_id"] = new_prescription.id
            session.add(NutritionalPrescriptionMealTime(**meal_values))


def correct_encounter(session: Session, encounter_id: uuid.UUID, payload: CorrectionCreate, actor_id: uuid.UUID) -> NutritionEncounterRead:
    original = _encounter(session, encounter_id)
    _ensure_version(original, payload.version)
    if original.status not in FINAL_STATUSES:
        raise _conflict("Sólo una atención finalizada puede corregirse.")
    _ensure_active(_admission(session, original.admission_id))
    clone = NutritionalCareEncounter(
        admission_id=original.admission_id,
        encounter_datetime=utc_now(),
        encounter_type=original.encounter_type,
        author_professional_id=actor_id,
        status="draft",
        clinical_summary=original.clinical_summary,
        reason_for_assessment=original.reason_for_assessment,
        information_source=original.information_source,
        correction_reason=payload.reason,
        corrected_encounter_id=original.id,
    )
    session.add(clone)
    session.flush()
    _clone_rows(session, original, clone)
    record_audit(session, action="nutrition_encounter_correction_created", actor_user_id=actor_id, entity_type="nutritional_care_encounter", entity_id=clone.id, admission_id=clone.admission_id, after_state={"status": "draft", "version": 1, "corrects": str(original.id)})
    session.commit()
    return get_encounter(session, clone.id)


def cancel_encounter(session: Session, encounter_id: uuid.UUID, payload: CancellationCreate, actor_id: uuid.UUID, roles: frozenset[str]) -> NutritionEncounterRead:
    encounter = _encounter(session, encounter_id)
    _ensure_draft_access(encounter, actor_id, roles)
    _ensure_version(encounter, payload.version)
    _ensure_active(_admission(session, encounter.admission_id))
    encounter.status = "cancelled"
    encounter.cancellation_reason = payload.reason
    encounter.cancelled_at = utc_now()
    encounter.cancelled_by = actor_id
    encounter.updated_at = utc_now()
    encounter.version += 1
    session.add(encounter)
    record_audit(session, action="nutrition_encounter_cancelled", actor_user_id=actor_id, entity_type="nutritional_care_encounter", entity_id=encounter.id, admission_id=encounter.admission_id, after_state={"status": "cancelled", "version": encounter.version})
    session.commit()
    return get_encounter(session, encounter.id)


def _final_encounters(session: Session, admission_id: uuid.UUID) -> list[NutritionalCareEncounter]:
    _admission(session, admission_id)
    return list(session.exec(select(NutritionalCareEncounter).where(NutritionalCareEncounter.admission_id == admission_id, NutritionalCareEncounter.status.in_(FINAL_STATUSES)).order_by(NutritionalCareEncounter.finalized_at.desc(), NutritionalCareEncounter.id.desc())).all())


def latest_nutrition(session: Session, admission_id: uuid.UUID) -> NutritionLatest:
    finals = _final_encounters(session, admission_id)
    if not finals:
        return NutritionLatest(admission_id=admission_id, latest_encounter=None, latest_screening=None, nutritional_status=None, active_diagnoses=[], current_prescription=None, adopted_requirements=[], active_alerts=[], suggested_reassessment_at=None)
    latest = finals[0]
    nutritional_status = None
    suggested_reassessment_at = None
    screening = None
    screening_seen = False
    prescription = None
    prescription_seen = False
    diagnoses: list[NutritionalDiagnosis] = []
    diagnoses_seen = False
    requirements: list[NutritionalRequirementCalculation] = []
    requirements_seen = False
    alerts: list[NutritionalAlert] = []
    alerts_seen = False
    for final in finals:
        current_assessment = None
        if nutritional_status is None or suggested_reassessment_at is None:
            current_assessment = session.exec(
                select(NutritionalAssessment).where(
                    NutritionalAssessment.encounter_id == final.id
                )
            ).first()
        if nutritional_status is None and current_assessment is not None:
            nutritional_status = current_assessment.nutritional_status
        if suggested_reassessment_at is None and current_assessment is not None:
            suggested_reassessment_at = current_assessment.suggested_reassessment_at
        if not screening_seen:
            screening = session.exec(
                select(NutritionalScreening)
                .where(NutritionalScreening.encounter_id == final.id)
                .order_by(NutritionalScreening.applied_at.desc(), NutritionalScreening.id.desc())
            ).first()
            screening_seen = screening is not None
        if not prescription_seen:
            documented_prescription = session.exec(
                select(NutritionalPrescription).where(
                    NutritionalPrescription.encounter_id == final.id
                )
            ).first()
            if documented_prescription is not None:
                prescription_seen = True
                prescription = (
                    documented_prescription
                    if documented_prescription.status == "active"
                    else None
                )
        if not diagnoses_seen:
            documented_diagnoses = list(session.exec(
                select(NutritionalDiagnosis).where(
                    NutritionalDiagnosis.encounter_id == final.id
                ).order_by(
                    NutritionalDiagnosis.priority,
                    NutritionalDiagnosis.created_at.desc(),
                    NutritionalDiagnosis.id,
                )
            ).all())
            if documented_diagnoses:
                diagnoses_seen = True
                diagnoses = [
                    row
                    for row in documented_diagnoses
                    if row.status in ("active", "improved")
                ]
        if not requirements_seen:
            documented_requirements = list(session.exec(
                select(NutritionalRequirementCalculation).where(
                    NutritionalRequirementCalculation.encounter_id == final.id
                ).order_by(
                    NutritionalRequirementCalculation.nutrient_code,
                    NutritionalRequirementCalculation.id,
                )
            ).all())
            if documented_requirements:
                requirements_seen = True
                requirements = documented_requirements
        if not alerts_seen:
            documented_alerts = list(session.exec(
                select(NutritionalAlert).where(
                    NutritionalAlert.encounter_id == final.id
                ).order_by(
                    NutritionalAlert.severity.desc(),
                    NutritionalAlert.created_at.desc(),
                    NutritionalAlert.id,
                )
            ).all())
            if documented_alerts:
                alerts_seen = True
                alerts = [row for row in documented_alerts if row.is_active]
    return NutritionLatest(
        admission_id=admission_id,
        latest_encounter={**_dump(latest), "professional_name": _user_name(session, latest.finalized_by or latest.author_professional_id)},
        latest_screening=_screening_with_answers(session, screening) if screening else None,
        nutritional_status=nutritional_status,
        active_diagnoses=[_dump(row) for row in diagnoses],
        current_prescription=_prescription_with_meals(session, prescription),
        adopted_requirements=[_dump(row) for row in requirements],
        active_alerts=[_dump(row) for row in alerts],
        suggested_reassessment_at=suggested_reassessment_at,
    )


def projection(session: Session, admission_id: uuid.UUID, kind: str, page: int, page_size: int) -> NutritionProjectionList:
    finals = _final_encounters(session, admission_id)
    final_ids = [row.id for row in finals]
    if not final_ids:
        return NutritionProjectionList(items=[], total=0, page=page, page_size=page_size)
    model, date_field = {
        "assessments": (NutritionalAssessment, NutritionalAssessment.observed_at),
        "prescriptions": (NutritionalPrescription, NutritionalPrescription.effective_from),
        "intake": (NutritionalIntakeRecord, NutritionalIntakeRecord.intake_date),
        "labs": (NutritionalLabObservation, NutritionalLabObservation.sampled_at),
    }[kind]
    rows = list(session.exec(select(model).where(model.encounter_id.in_(final_ids)).order_by(date_field.desc(), model.id.desc())).all())
    start = (page - 1) * page_size
    page_rows = rows[start:start + page_size]
    items = [_prescription_with_meals(session, row) if kind == "prescriptions" else _dump(row) for row in page_rows]
    return NutritionProjectionList(items=items, total=len(rows), page=page, page_size=page_size)


def catalogs() -> NutritionCatalogs:
    return NutritionCatalogs(
        encounter_types=["initial_assessment", "follow_up", "reassessment", "discharge_planning", "other"],
        population_groups=["adult", "pediatric", "neonatal", "pregnancy"],
        information_sources=["patient_interview", "family_or_caregiver", "clinical_record", "trakcare_manual", "care_team_observation", "combined", "other"],
        measurement_types=["current_weight_measured", "current_weight_reported", "usual_weight", "preadmission_weight", "dry_weight", "ideal_weight", "adjusted_weight", "target_weight", "prepregnancy_weight", "birth_weight", "neonatal_minimum_weight", "calculation_weight", "standing_height", "recumbent_length", "estimated_height", "mid_upper_arm_circumference", "head_circumference", "waist_circumference", "skinfold", "body_mass_index"],
        meal_times=["breakfast", "morning_snack", "lunch", "afternoon_snack", "dinner", "night_snack", "other"],
        screening_defaults={"adult": "nrs_2002", "pediatric": "strongkids", "neonatal": "none", "pregnancy": "none"},
        screening_tools=[
            {"code": "nrs_2002", "version": "ESPEN 2002", "population": ["adult"], "reference": "https://www.espen.org/documents/Screening.pdf"},
            {"code": "strongkids", "version": "original", "population": ["pediatric"], "reference": "Hulst et al., Clin Nutr. 2010"},
            {"code": "none", "version": "institutional-policy-pending", "population": ["neonatal", "pregnancy"]},
        ],
        requirement_methods=[
            {"code": "factorial", "population": ["adult"], "default": True, "limitations": "Factores elegidos y confirmados por profesional."},
            {"code": "kcal_per_kg", "population": ["adult"], "limitations": "Requiere selección explícita de peso y tasa."},
            {"code": "mifflin_st_jeor", "population": ["adult"], "version": "1990"},
            {"code": "harris_benedict", "population": ["adult"], "version": "revised-1984"},
            {"code": "schofield", "population": ["adult"], "version": "1985-adult"},
            {"code": "indirect_calorimetry", "population": ["adult", "pediatric", "neonatal", "pregnancy"]},
            {"code": "manual", "population": ["adult", "pediatric", "neonatal", "pregnancy"]},
            {"code": "other", "population": ["adult", "pediatric", "neonatal", "pregnancy"]},
        ],
    )
