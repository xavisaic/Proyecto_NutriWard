import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.patient import normalize_optional_text, normalize_required_text


class PrescriptionMealInput(BaseModel):
    meal_time: str = Field(min_length=1, max_length=40)
    instruction: str = Field(min_length=1, max_length=1000)

    _required = field_validator("meal_time", "instruction")(normalize_required_text)


class PrescriptionSupplementInput(BaseModel):
    product_type: str = Field(min_length=1, max_length=60)
    product_name: str = Field(min_length=1, max_length=300)
    dose: Decimal | None = Field(default=None, ge=0)
    dose_unit: str | None = Field(default=None, max_length=40)
    schedule: str | None = Field(default=None, max_length=200)
    route: str | None = Field(default=None, max_length=60)
    duration: str | None = Field(default=None, max_length=200)
    energy_kcal: Decimal = Field(default=Decimal("0"), ge=0)
    protein_g: Decimal = Field(default=Decimal("0"), ge=0)
    carbohydrate_g: Decimal = Field(default=Decimal("0"), ge=0)
    lipid_g: Decimal = Field(default=Decimal("0"), ge=0)
    fluid_ml: Decimal = Field(default=Decimal("0"), ge=0)

    _required = field_validator("product_type", "product_name")(normalize_required_text)


class PrescriptionProgressionInput(BaseModel):
    sequence: int = Field(ge=1)
    stage: str = Field(min_length=1, max_length=100)
    rate_ml_h: Decimal = Field(gt=0)
    duration_hours: Decimal = Field(gt=0, le=24)
    condition: str | None = Field(default=None, max_length=1000)


class PrescriptionMonitoringInput(BaseModel):
    parameter: str = Field(min_length=1, max_length=200)
    frequency: str = Field(min_length=1, max_length=200)
    responsible: str | None = Field(default=None, max_length=200)
    instruction: str | None = Field(default=None, max_length=1000)


class PrescriptionElectrolyteInput(BaseModel):
    electrolyte_code: Literal["sodium", "potassium", "calcium", "magnesium", "phosphate", "chloride", "acetate", "other"]
    amount: Decimal = Field(ge=0)
    unit: str = Field(min_length=1, max_length=30)
    instruction: str | None = Field(default=None, max_length=500)

    _required = field_validator("unit")(normalize_required_text)


class PrescriptionNonNutritionalContributionInput(BaseModel):
    source_type: Literal["propofol", "dextrose_solution", "citrate", "medication_vehicle", "flush_water", "iv_fluid", "other"]
    label: str = Field(min_length=1, max_length=300)
    source_treatment_id: uuid.UUID | None = None
    energy_kcal: Decimal = Field(default=Decimal("0"), ge=0)
    carbohydrate_g: Decimal = Field(default=Decimal("0"), ge=0)
    lipid_g: Decimal = Field(default=Decimal("0"), ge=0)
    fluid_ml: Decimal = Field(default=Decimal("0"), ge=0)
    data_origin: Literal["manual", "treatment_snapshot"] = "manual"
    verification_status: Literal["suggested", "confirmed"] = "confirmed"

    _label = field_validator("label")(normalize_required_text)


class PrescriptionOrderData(BaseModel):
    source_encounter_id: uuid.UUID | None = None
    change_reason: str = Field(min_length=3, max_length=1000)
    effective_from: datetime | None = None
    suggested_reassessment_at: datetime | None = None
    oral_enabled: bool = False
    enteral_enabled: bool = False
    parenteral_enabled: bool = False
    fasting_enabled: bool = False
    energy_goal_kcal: Decimal | None = Field(default=None, ge=0)
    protein_goal_g: Decimal | None = Field(default=None, ge=0)
    carbohydrate_goal_g: Decimal | None = Field(default=None, ge=0)
    lipid_goal_g: Decimal | None = Field(default=None, ge=0)
    fluid_goal_ml: Decimal | None = Field(default=None, ge=0)
    fluid_goal_kind: Literal["target", "minimum", "maximum", "range"] = "target"
    regimen_type: str | None = Field(default=None, max_length=300)
    food_iddsi: int | None = Field(default=None, ge=3, le=7)
    liquid_iddsi: int | None = Field(default=None, ge=0, le=4)
    restrictions: str | None = Field(default=None, max_length=2000)
    allergies_snapshot: str | None = Field(default=None, max_length=2000)
    feeding_assistance: str | None = Field(default=None, max_length=200)
    kitchen_instructions: str | None = Field(default=None, max_length=3000)
    nursing_instructions: str | None = Field(default=None, max_length=3000)
    oral_energy_kcal: Decimal = Field(default=Decimal("0"), ge=0)
    oral_protein_g: Decimal = Field(default=Decimal("0"), ge=0)
    oral_carbohydrate_g: Decimal = Field(default=Decimal("0"), ge=0)
    oral_lipid_g: Decimal = Field(default=Decimal("0"), ge=0)
    oral_fluid_ml: Decimal = Field(default=Decimal("0"), ge=0)
    enteral_formula_id: uuid.UUID | None = None
    enteral_access_route: str | None = Field(default=None, max_length=100)
    enteral_tube_location: str | None = Field(default=None, max_length=100)
    enteral_modality: Literal["continuous", "cyclic", "intermittent", "bolus"] | None = None
    enteral_rate_ml_h: Decimal | None = Field(default=None, gt=0)
    enteral_effective_hours: Decimal | None = Field(default=None, gt=0, le=24)
    water_flush_ml: Decimal = Field(default=Decimal("0"), ge=0)
    water_flush_every_hours: Decimal | None = Field(default=None, gt=0, le=24)
    medication_pause_hours: Decimal = Field(default=Decimal("0"), ge=0, le=24)
    enteral_starts_at: datetime | None = None
    calculation_weight_kg: Decimal | None = Field(default=None, gt=0)
    parenteral_access: Literal["central", "peripheral"] | None = None
    parenteral_solution_type: Literal["standardized", "individualized"] | None = None
    parenteral_solution_name: str | None = Field(default=None, max_length=300)
    parenteral_total_volume_ml: Decimal = Field(default=Decimal("0"), ge=0)
    parenteral_infusion_hours: Decimal | None = Field(default=None, gt=0, le=24)
    amino_acids_g: Decimal = Field(default=Decimal("0"), ge=0)
    dextrose_g: Decimal = Field(default=Decimal("0"), ge=0)
    parenteral_lipid_g: Decimal = Field(default=Decimal("0"), ge=0)
    osmolarity_mosm_l: Decimal | None = Field(default=None, gt=0)
    vitamins_instruction: str | None = Field(default=None, max_length=1000)
    trace_elements_instruction: str | None = Field(default=None, max_length=1000)
    insulin_units: Decimal | None = Field(default=None, ge=0)
    parenteral_starts_at: datetime | None = None
    planned_duration_days: int | None = Field(default=None, ge=1, le=365)
    refeeding_risk_confirmed: bool = False
    general_observations: str | None = Field(default=None, max_length=3000)
    meals: list[PrescriptionMealInput] = Field(default_factory=list, max_length=12)
    supplements: list[PrescriptionSupplementInput] = Field(default_factory=list, max_length=30)
    progressions: list[PrescriptionProgressionInput] = Field(default_factory=list, max_length=20)
    monitoring: list[PrescriptionMonitoringInput] = Field(default_factory=list, max_length=30)
    electrolytes: list[PrescriptionElectrolyteInput] = Field(default_factory=list, max_length=30)
    non_nutritional_contributions: list[PrescriptionNonNutritionalContributionInput] = Field(default_factory=list, max_length=50)

    _reason = field_validator("change_reason")(normalize_required_text)
    _optional = field_validator(
        "regimen_type", "restrictions", "allergies_snapshot", "feeding_assistance",
        "kitchen_instructions", "nursing_instructions", "enteral_access_route",
        "enteral_tube_location", "parenteral_solution_name", "vitamins_instruction",
        "trace_elements_instruction", "general_observations",
    )(normalize_optional_text)

    @model_validator(mode="after")
    def validate_strategy(self):
        if self.fasting_enabled and (
            self.oral_enabled or self.enteral_enabled or self.parenteral_enabled or self.supplements
        ):
            raise ValueError("El régimen cero no puede combinarse con aportes nutricionales.")
        return self


class PrescriptionOrderCreate(PrescriptionOrderData):
    supersedes_order_id: uuid.UUID | None = None


class PrescriptionOrderUpdate(PrescriptionOrderData):
    expected_lock_version: int = Field(ge=1)


class PrescriptionAction(BaseModel):
    expected_lock_version: int = Field(ge=1)


class PrescriptionSuspension(PrescriptionAction):
    reason: str = Field(min_length=3, max_length=1000)

    _reason = field_validator("reason")(normalize_required_text)


class PrescriptionClone(BaseModel):
    reason: str = Field(min_length=3, max_length=1000)

    _reason = field_validator("reason")(normalize_required_text)


class PrescriptionDispatchCreate(BaseModel):
    target: Literal["pharmacy", "kitchen", "nursing"]
    note: str | None = Field(default=None, max_length=1000)


class PrescriptionDispatchAcknowledge(BaseModel):
    external_reference: str | None = Field(default=None, max_length=200)


class FormulaCatalogCreate(BaseModel):
    code: str = Field(min_length=1, max_length=60)
    display_name: str = Field(min_length=1, max_length=300)
    manufacturer: str | None = Field(default=None, max_length=200)
    catalog_version: str = Field(min_length=1, max_length=80)
    kcal_per_ml: Decimal = Field(gt=0)
    protein_g_per_l: Decimal = Field(default=0, ge=0)
    carbohydrate_g_per_l: Decimal = Field(default=0, ge=0)
    lipid_g_per_l: Decimal = Field(default=0, ge=0)
    fiber_g_per_l: Decimal = Field(default=0, ge=0)
    sodium_mg_per_l: Decimal = Field(default=0, ge=0)
    potassium_mg_per_l: Decimal = Field(default=0, ge=0)
    phosphorus_mg_per_l: Decimal = Field(default=0, ge=0)
    free_water_ml_per_l: Decimal = Field(default=0, ge=0, le=1000)


class FormulaCatalogRead(FormulaCatalogCreate):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    is_active: bool
    created_at: datetime


class PrescriptionSettingsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    green_min_percent: Decimal
    green_max_percent: Decimal
    yellow_min_percent: Decimal
    yellow_max_percent: Decimal
    peripheral_osmolarity_max_mosm_l: Decimal = Field(gt=0)
    gir_max_mg_kg_min: Decimal = Field(gt=0)
    lipid_max_g_kg_day: Decimal = Field(gt=0)
    amino_acid_kcal_per_g: Decimal = Field(gt=0)
    dextrose_kcal_per_g: Decimal = Field(gt=0)
    lipid_kcal_per_g: Decimal = Field(gt=0)


class PrescriptionSettingsUpdate(PrescriptionSettingsRead):
    @model_validator(mode="after")
    def validate_ranges(self):
        if not (0 <= self.yellow_min_percent < self.green_min_percent <= self.green_max_percent < self.yellow_max_percent):
            raise ValueError("Los umbrales de cobertura deben estar ordenados y no superponerse.")
        return self


class PrescriptionOrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    admission_id: uuid.UUID
    version_number: int
    lock_version: int
    supersedes_order_id: uuid.UUID | None
    status: str
    created_at: datetime
    updated_at: datetime
    validated_at: datetime | None
    activated_at: datetime | None
    suspended_at: datetime | None
    suspension_reason: str | None
    author_name: str
    formula: FormulaCatalogRead | None
    meals: list[dict]
    supplements: list[dict]
    progressions: list[dict]
    monitoring: list[dict]
    electrolytes: list[dict]
    non_nutritional_contributions: list[dict]
    dispatches: list[dict]
    coverage: list[dict]
    nutritional_coverage: list[dict]
    alerts: list[dict]
    changes: list[dict]
    # Clinical fields are returned as a flat immutable snapshot.
    source_encounter_id: uuid.UUID | None
    change_reason: str
    effective_from: datetime | None
    suggested_reassessment_at: datetime | None
    oral_enabled: bool
    enteral_enabled: bool
    parenteral_enabled: bool
    fasting_enabled: bool
    energy_goal_kcal: Decimal | None
    protein_goal_g: Decimal | None
    carbohydrate_goal_g: Decimal | None
    lipid_goal_g: Decimal | None
    fluid_goal_ml: Decimal | None
    fluid_goal_kind: str
    regimen_type: str | None
    food_iddsi: int | None
    liquid_iddsi: int | None
    restrictions: str | None
    allergies_snapshot: str | None
    feeding_assistance: str | None
    kitchen_instructions: str | None
    nursing_instructions: str | None
    oral_energy_kcal: Decimal
    oral_protein_g: Decimal
    oral_carbohydrate_g: Decimal
    oral_lipid_g: Decimal
    oral_fluid_ml: Decimal
    enteral_formula_id: uuid.UUID | None
    enteral_access_route: str | None
    enteral_tube_location: str | None
    enteral_modality: str | None
    enteral_rate_ml_h: Decimal | None
    enteral_effective_hours: Decimal | None
    enteral_volume_ml: Decimal
    water_flush_ml: Decimal
    water_flush_every_hours: Decimal | None
    medication_pause_hours: Decimal
    enteral_starts_at: datetime | None
    calculation_weight_kg: Decimal | None
    parenteral_access: str | None
    parenteral_solution_type: str | None
    parenteral_solution_name: str | None
    parenteral_total_volume_ml: Decimal | None
    parenteral_infusion_hours: Decimal | None
    parenteral_rate_ml_h: Decimal | None
    amino_acids_g: Decimal
    dextrose_g: Decimal
    parenteral_lipid_g: Decimal
    parenteral_gir_mg_kg_min: Decimal | None
    osmolarity_mosm_l: Decimal | None
    vitamins_instruction: str | None
    trace_elements_instruction: str | None
    insulin_units: Decimal | None
    parenteral_starts_at: datetime | None
    planned_duration_days: int | None
    refeeding_risk_confirmed: bool
    prescribed_energy_kcal: Decimal
    prescribed_protein_g: Decimal
    prescribed_carbohydrate_g: Decimal
    prescribed_lipid_g: Decimal
    prescribed_fluid_ml: Decimal
    non_nutritional_energy_kcal: Decimal
    non_nutritional_carbohydrate_g: Decimal
    non_nutritional_lipid_g: Decimal
    non_nutritional_fluid_ml: Decimal
    total_real_energy_kcal: Decimal
    total_real_protein_g: Decimal
    total_real_carbohydrate_g: Decimal
    total_real_lipid_g: Decimal
    total_real_fluid_ml: Decimal
    signature_kind: str | None
    signature_content_hash: str | None
    signed_by_user_id: uuid.UUID | None
    signed_at: datetime | None
    recipe_text: str | None
    general_observations: str | None


class PrescriptionWorkspaceRead(BaseModel):
    admission_id: uuid.UUID
    requirements: list[dict]
    settings: PrescriptionSettingsRead
    formulas: list[FormulaCatalogRead]
    treatment_suggestions: list[dict]
    lab_context: list[dict]
    active: PrescriptionOrderRead | None
    drafts: list[PrescriptionOrderRead]
    history: list[PrescriptionOrderRead]
