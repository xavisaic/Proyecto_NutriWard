import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.patient import normalize_optional_text, normalize_required_text


class EncounterType(StrEnum):
    INITIAL_ASSESSMENT = "initial_assessment"
    FOLLOW_UP = "follow_up"
    REASSESSMENT = "reassessment"
    DISCHARGE_PLANNING = "discharge_planning"
    OTHER = "other"


class PopulationGroup(StrEnum):
    ADULT = "adult"
    PEDIATRIC = "pediatric"
    NEONATAL = "neonatal"
    PREGNANCY = "pregnancy"


class AssessmentInput(BaseModel):
    population_group: PopulationGroup
    medical_diagnoses_summary: str | None = Field(default=None, max_length=3000)
    hospitalization_reason: str | None = Field(default=None, max_length=2000)
    current_feeding_route: str | None = Field(default=None, max_length=50)
    appetite: str | None = Field(default=None, max_length=100)
    clinical_findings: str | None = Field(default=None, max_length=4000)
    digestive_findings: str | None = Field(default=None, max_length=4000)
    nutritional_status: str | None = Field(default=None, max_length=500)
    gestational_age_weeks: Decimal | None = Field(default=None, ge=0, le=50)
    gestation_type: str | None = Field(default=None, max_length=20)
    corrected_age_days: int | None = Field(default=None, ge=0)
    growth_reference_code: str | None = Field(default=None, max_length=80)
    growth_reference_version: str | None = Field(default=None, max_length=80)
    objectives: str | None = Field(default=None, max_length=4000)
    monitoring_plan: str | None = Field(default=None, max_length=4000)
    pending_actions: str | None = Field(default=None, max_length=3000)
    suggested_reassessment_at: datetime | None = None
    observations: str | None = Field(default=None, max_length=5000)
    observed_at: datetime | None = None


class ClinicalContextItemInput(BaseModel):
    category: str = Field(min_length=1, max_length=60)
    description: str = Field(min_length=1, max_length=2000)
    item_status: str | None = Field(default=None, max_length=30)
    source: str | None = Field(default=None, max_length=80)
    verification_status: str | None = Field(default=None, max_length=30)
    observed_at: datetime
    complementary_observation: str | None = Field(default=None, max_length=2000)

    _normalize_category = field_validator("category", "description")(normalize_required_text)


class AnthropometricMeasurementInput(BaseModel):
    measurement_type: str = Field(min_length=1, max_length=60)
    value: Decimal = Field(ge=0)
    unit: str = Field(min_length=1, max_length=20)
    measured_at: datetime
    method: str | None = Field(default=None, max_length=120)
    source: str | None = Field(default=None, max_length=80)
    reliability: str = Field(default="unknown", pattern="^(high|medium|low|unknown)$")
    value_nature: str = Field(
        default="measured", pattern="^(measured|reported|estimated|calculated)$"
    )
    observations: str | None = Field(default=None, max_length=2000)
    manual_value_used: Decimal | None = Field(default=None, ge=0)
    manual_adjustment_reason: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_manual_adjustment(self):
        if self.manual_value_used is not None and not self.manual_adjustment_reason:
            raise ValueError("Un valor antropométrico manual requiere motivo documentado.")
        return self


class ScreeningAnswerInput(BaseModel):
    answer_code: str = Field(min_length=1, max_length=80)
    answer_value: str = Field(min_length=1, max_length=500)


class ScreeningInput(BaseModel):
    tool_code: str = Field(min_length=1, max_length=50)
    tool_version: str = Field(min_length=1, max_length=50)
    applied_at: datetime
    no_tool_reason: str | None = Field(default=None, max_length=1000)
    answers: list[ScreeningAnswerInput] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_no_tool(self):
        if self.tool_code == "none" and not self.no_tool_reason:
            raise ValueError("Debe documentar por qué no se aplica una herramienta.")
        if self.tool_code != "none" and not self.answers:
            raise ValueError("La herramienta seleccionada requiere respuestas estructuradas.")
        return self


class RequirementCalculationInput(BaseModel):
    nutrient_code: str = Field(min_length=1, max_length=40)
    method: str = Field(min_length=1, max_length=50)
    unit: str = Field(min_length=1, max_length=30)
    weight_measurement_id: uuid.UUID | None = None
    weight_selection_reason: str | None = Field(default=None, max_length=1000)
    inputs: dict[str, Decimal | int | str] = Field(default_factory=dict)
    adopted_result: Decimal | None = Field(default=None, ge=0)
    minimum_result: Decimal | None = Field(default=None, ge=0)
    maximum_result: Decimal | None = Field(default=None, ge=0)
    manual_adjustment_reason: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_adopted_result(self):
        if self.adopted_result is not None and not self.manual_adjustment_reason:
            raise ValueError("Un resultado adoptado distinto requiere justificación.")
        if (
            self.minimum_result is not None
            and self.maximum_result is not None
            and self.minimum_result > self.maximum_result
        ):
            raise ValueError("El rango de requerimiento no es válido.")
        return self


class DiagnosisInput(BaseModel):
    problem: str = Field(min_length=1, max_length=1000)
    etiology: str = Field(min_length=1, max_length=1000)
    signs_and_symptoms: str = Field(min_length=1, max_length=2000)
    priority: int = Field(default=1, ge=1)
    status: str = Field(default="active", pattern="^(active|improved|resolved|discarded)$")
    resolved_at: datetime | None = None

    _normalize = field_validator("problem", "etiology", "signs_and_symptoms")(
        normalize_required_text
    )


class PrescriptionMealTimeInput(BaseModel):
    meal_time: str = Field(min_length=1, max_length=40)
    regimen: str = Field(min_length=1, max_length=1000)
    texture: str | None = Field(default=None, max_length=200)
    restrictions: str | None = Field(default=None, max_length=1000)
    supplement: str | None = Field(default=None, max_length=1000)
    observations: str | None = Field(default=None, max_length=1000)


class PrescriptionInput(BaseModel):
    effective_from: datetime
    effective_until: datetime | None = None
    status: str = Field(default="active", max_length=20)
    primary_route: str = Field(pattern="^(oral|enteral|parenteral|mixed|fasting|other)$")
    complementary_routes: str | None = Field(default=None, max_length=200)
    energy_target: Decimal | None = Field(default=None, ge=0)
    protein_target: Decimal | None = Field(default=None, ge=0)
    fluid_target: Decimal | None = Field(default=None, ge=0)
    regimen_type: str | None = Field(default=None, max_length=300)
    texture: str | None = Field(default=None, max_length=200)
    restrictions: str | None = Field(default=None, max_length=2000)
    allergies_considered: str | None = Field(default=None, max_length=2000)
    oral_supplements: str | None = Field(default=None, max_length=2000)
    enteral_support: str | None = Field(default=None, max_length=2000)
    parenteral_support: str | None = Field(default=None, max_length=2000)
    general_instructions: str | None = Field(default=None, max_length=4000)
    observations: str | None = Field(default=None, max_length=3000)
    meal_times: list[PrescriptionMealTimeInput] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_dates(self):
        if self.effective_until and self.effective_until < self.effective_from:
            raise ValueError("La fecha de término no puede preceder al inicio.")
        return self


class MonitoringRecordInput(BaseModel):
    record_type: str = Field(min_length=1, max_length=60)
    value: str = Field(min_length=1, max_length=1000)
    unit: str | None = Field(default=None, max_length=30)
    observed_at: datetime
    source: str | None = Field(default=None, max_length=80)
    observations: str | None = Field(default=None, max_length=2000)


class IntakeRecordInput(BaseModel):
    intake_date: date
    meal_time: str = Field(min_length=1, max_length=40)
    consumed_percentage: Decimal | None = Field(default=None, ge=0, le=100)
    offered_amount: Decimal | None = Field(default=None, ge=0)
    consumed_amount: Decimal | None = Field(default=None, ge=0)
    unit: str | None = Field(default=None, max_length=30)
    incomplete_reason: str | None = Field(default=None, max_length=1000)
    observations: str | None = Field(default=None, max_length=2000)
    source: str | None = Field(default=None, max_length=80)


class LabObservationInput(BaseModel):
    test_name: str = Field(min_length=1, max_length=200)
    local_code: str | None = Field(default=None, max_length=80)
    value: str = Field(min_length=1, max_length=200)
    unit: str | None = Field(default=None, max_length=40)
    reference_range: str | None = Field(default=None, max_length=200)
    flag: str | None = Field(default=None, pattern="^(low|normal|high|critical)$")
    sampled_at: datetime
    source: str = Field(min_length=1, max_length=80)
    observation: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_flag_traceability(self):
        if self.flag and not self.reference_range and self.source != "trakcare_manual":
            raise ValueError("La clasificación requiere rango o fuente informada.")
        return self


class AlertInput(BaseModel):
    alert_type: str = Field(min_length=1, max_length=60)
    description: str = Field(min_length=1, max_length=2000)
    severity: str = Field(default="warning", pattern="^(info|warning|critical)$")
    source: str | None = Field(default=None, max_length=80)
    verification_status: str | None = Field(default=None, max_length=30)
    is_active: bool = True


class NutritionEncounterCreate(BaseModel):
    encounter_datetime: datetime | None = None
    encounter_type: EncounterType = EncounterType.INITIAL_ASSESSMENT
    clinical_summary: str | None = Field(default=None, max_length=4000)
    reason_for_assessment: str | None = Field(default=None, max_length=2000)
    information_source: str | None = Field(default=None, max_length=80)
    assessment: AssessmentInput | None = None
    context_items: list[ClinicalContextItemInput] = Field(default_factory=list)
    anthropometry: list[AnthropometricMeasurementInput] = Field(default_factory=list)
    screenings: list[ScreeningInput] = Field(default_factory=list)
    requirements: list[RequirementCalculationInput] = Field(default_factory=list)
    diagnoses: list[DiagnosisInput] = Field(default_factory=list)
    prescription: PrescriptionInput | None = None
    monitoring: list[MonitoringRecordInput] = Field(default_factory=list)
    intake: list[IntakeRecordInput] = Field(default_factory=list)
    labs: list[LabObservationInput] = Field(default_factory=list)
    alerts: list[AlertInput] = Field(default_factory=list)

    _normalize_optional = field_validator(
        "clinical_summary", "reason_for_assessment", "information_source"
    )(normalize_optional_text)


class NutritionEncounterPatch(NutritionEncounterCreate):
    version: int = Field(ge=1)


class VersionedAction(BaseModel):
    version: int = Field(ge=1)


class CorrectionCreate(VersionedAction):
    reason: str = Field(min_length=10, max_length=1000)

    _normalize_reason = field_validator("reason")(normalize_required_text)


class CancellationCreate(VersionedAction):
    reason: str = Field(min_length=5, max_length=1000)

    _normalize_reason = field_validator("reason")(normalize_required_text)


class NutritionEncounterSummary(BaseModel):
    id: uuid.UUID
    admission_id: uuid.UUID
    encounter_datetime: datetime
    encounter_type: str
    author_professional_id: uuid.UUID
    author_name: str
    status: str
    clinical_summary: str | None
    finalized_at: datetime | None
    corrected_encounter_id: uuid.UUID | None
    version: int
    documented_sections: list[str] = Field(default_factory=list)


class NutritionEncounterList(BaseModel):
    items: list[NutritionEncounterSummary]
    total: int
    page: int
    page_size: int


class NutritionEncounterRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    encounter: dict[str, Any]
    author_name: str
    finalized_by_name: str | None
    assessment: dict[str, Any] | None
    context_items: list[dict[str, Any]]
    anthropometry: list[dict[str, Any]]
    screenings: list[dict[str, Any]]
    requirements: list[dict[str, Any]]
    diagnoses: list[dict[str, Any]]
    prescription: dict[str, Any] | None
    monitoring: list[dict[str, Any]]
    intake: list[dict[str, Any]]
    labs: list[dict[str, Any]]
    alerts: list[dict[str, Any]]


class NutritionProjectionList(BaseModel):
    items: list[dict[str, Any]]
    total: int
    page: int
    page_size: int


class NutritionLatest(BaseModel):
    admission_id: uuid.UUID
    latest_encounter: dict[str, Any] | None
    latest_screening: dict[str, Any] | None
    nutritional_status: str | None
    active_diagnoses: list[dict[str, Any]]
    current_prescription: dict[str, Any] | None
    adopted_requirements: list[dict[str, Any]]
    active_alerts: list[dict[str, Any]]
    suggested_reassessment_at: datetime | None


class NutritionCatalogs(BaseModel):
    encounter_types: list[str]
    population_groups: list[str]
    information_sources: list[str]
    measurement_types: list[str]
    meal_times: list[str]
    requirement_methods: list[dict[str, Any]]
    screening_defaults: dict[str, str]
    screening_tools: list[dict[str, Any]]
