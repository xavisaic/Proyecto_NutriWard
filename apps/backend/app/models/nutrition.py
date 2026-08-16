import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, CheckConstraint, DateTime, Index, Numeric, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from app.models.common import utc_now

CLINICAL_JSON = JSON().with_variant(JSONB(), "postgresql")


class NutritionalCareEncounter(SQLModel, table=True):
    __tablename__ = "nutritional_care_encounters"
    __table_args__ = (
        CheckConstraint(
            "encounter_type IN ('initial_assessment','follow_up','reassessment',"
            "'discharge_planning','other')",
            name="ck_nutrition_encounter_type",
        ),
        CheckConstraint(
            "status IN ('draft','finalized','corrected','cancelled')",
            name="ck_nutrition_encounter_status",
        ),
        CheckConstraint("version > 0", name="ck_nutrition_encounter_version_positive"),
        CheckConstraint(
            "corrected_encounter_id IS NULL OR corrected_encounter_id != id",
            name="ck_nutrition_encounter_not_self_corrected",
        ),
        Index(
            "ix_nutrition_encounter_admission_datetime_status",
            "admission_id",
            "encounter_datetime",
            "status",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    admission_id: uuid.UUID = Field(foreign_key="admissions.id", index=True)
    encounter_datetime: datetime = Field(
        default_factory=utc_now, sa_type=DateTime(timezone=True), index=True
    )
    encounter_type: str = Field(default="initial_assessment", max_length=30)
    author_professional_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    status: str = Field(default="draft", max_length=20, index=True)
    clinical_summary: str | None = Field(default=None, max_length=4000)
    reason_for_assessment: str | None = Field(default=None, max_length=2000)
    information_source: str | None = Field(default=None, max_length=80)
    finalized_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    finalized_by: uuid.UUID | None = Field(default=None, foreign_key="users.id")
    correction_reason: str | None = Field(default=None, max_length=1000)
    corrected_encounter_id: uuid.UUID | None = Field(
        default=None, foreign_key="nutritional_care_encounters.id", index=True
    )
    cancellation_reason: str | None = Field(default=None, max_length=1000)
    cancelled_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    cancelled_by: uuid.UUID | None = Field(default=None, foreign_key="users.id")
    version: int = Field(default=1)
    created_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True))
    updated_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True))


class NutritionalAssessment(SQLModel, table=True):
    __tablename__ = "nutritional_assessments"
    __table_args__ = (
        CheckConstraint(
            "population_group IN ('adult','pediatric','neonatal','pregnancy')",
            name="ck_nutrition_assessment_population",
        ),
        UniqueConstraint("encounter_id", name="uq_nutrition_assessment_encounter"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    admission_id: uuid.UUID = Field(foreign_key="admissions.id", index=True)
    encounter_id: uuid.UUID = Field(foreign_key="nutritional_care_encounters.id", index=True)
    population_group: str = Field(max_length=20, index=True)
    medical_diagnoses_summary: str | None = Field(default=None, max_length=3000)
    hospitalization_reason: str | None = Field(default=None, max_length=2000)
    current_feeding_route: str | None = Field(default=None, max_length=50)
    appetite: str | None = Field(default=None, max_length=100)
    clinical_findings: str | None = Field(default=None, max_length=4000)
    digestive_findings: str | None = Field(default=None, max_length=4000)
    nutritional_status: str | None = Field(default=None, max_length=500)
    gestational_age_weeks: Decimal | None = Field(default=None, sa_type=Numeric(5, 2))
    gestation_type: str | None = Field(default=None, max_length=20)
    corrected_age_days: int | None = Field(default=None)
    growth_reference_code: str | None = Field(default=None, max_length=80)
    growth_reference_version: str | None = Field(default=None, max_length=80)
    objectives: str | None = Field(default=None, max_length=4000)
    monitoring_plan: str | None = Field(default=None, max_length=4000)
    pending_actions: str | None = Field(default=None, max_length=3000)
    suggested_reassessment_at: datetime | None = Field(
        default=None, sa_type=DateTime(timezone=True), index=True
    )
    observations: str | None = Field(default=None, max_length=5000)
    observed_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True))
    author_professional_id: uuid.UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True))
    updated_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True))


class NutritionalClinicalContextItem(SQLModel, table=True):
    __tablename__ = "nutritional_clinical_context_items"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    admission_id: uuid.UUID = Field(foreign_key="admissions.id", index=True)
    encounter_id: uuid.UUID = Field(foreign_key="nutritional_care_encounters.id", index=True)
    category: str = Field(index=True, max_length=60)
    description: str = Field(max_length=2000)
    item_status: str | None = Field(default=None, max_length=30)
    source: str | None = Field(default=None, max_length=80)
    verification_status: str | None = Field(default=None, max_length=30)
    observed_at: datetime = Field(sa_type=DateTime(timezone=True))
    author_professional_id: uuid.UUID = Field(foreign_key="users.id")
    complementary_observation: str | None = Field(default=None, max_length=2000)
    created_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True))


class NutritionalAnthropometricMeasurement(SQLModel, table=True):
    __tablename__ = "nutritional_anthropometric_measurements"
    __table_args__ = (
        CheckConstraint("value >= 0", name="ck_nutrition_measurement_non_negative"),
        CheckConstraint(
            "reliability IN ('high','medium','low','unknown')",
            name="ck_nutrition_measurement_reliability",
        ),
        CheckConstraint(
            "value_nature IN ('measured','reported','estimated','calculated')",
            name="ck_nutrition_measurement_nature",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    admission_id: uuid.UUID = Field(foreign_key="admissions.id", index=True)
    encounter_id: uuid.UUID = Field(foreign_key="nutritional_care_encounters.id", index=True)
    measurement_type: str = Field(index=True, max_length=60)
    value: Decimal = Field(sa_type=Numeric(12, 4))
    unit: str = Field(max_length=20)
    measured_at: datetime = Field(sa_type=DateTime(timezone=True), index=True)
    method: str | None = Field(default=None, max_length=120)
    source: str | None = Field(default=None, max_length=80)
    reliability: str = Field(default="unknown", max_length=20)
    value_nature: str = Field(default="measured", max_length=20)
    author_professional_id: uuid.UUID = Field(foreign_key="users.id")
    observations: str | None = Field(default=None, max_length=2000)
    calculated_value: Decimal | None = Field(default=None, sa_type=Numeric(12, 4))
    manual_value_used: Decimal | None = Field(default=None, sa_type=Numeric(12, 4))
    manual_adjustment_reason: str | None = Field(default=None, max_length=1000)
    created_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True))


class NutritionalMeasurementSession(SQLModel, table=True):
    __tablename__ = "nutritional_measurement_sessions"
    __table_args__ = (
        CheckConstraint(
            "session_type IN ('circumference','handgrip','skinfold_4','bioimpedance')",
            name="ck_nutrition_measurement_session_type",
        ),
        CheckConstraint(
            "reliability IN ('high','medium','low','unknown')",
            name="ck_nutrition_measurement_session_reliability",
        ),
        CheckConstraint(
            "preparation_status IS NULL OR preparation_status IN "
            "('standard','nonstandard','unknown')",
            name="ck_nutrition_measurement_preparation_status",
        ),
        CheckConstraint(
            "hydration_status IS NULL OR hydration_status IN "
            "('usual','altered','unknown')",
            name="ck_nutrition_measurement_hydration_status",
        ),
        Index(
            "ix_nutrition_measurement_session_encounter_type",
            "encounter_id",
            "session_type",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    admission_id: uuid.UUID = Field(foreign_key="admissions.id", index=True)
    encounter_id: uuid.UUID = Field(
        foreign_key="nutritional_care_encounters.id", index=True
    )
    session_type: str = Field(max_length=30, index=True)
    measured_at: datetime = Field(sa_type=DateTime(timezone=True), index=True)
    protocol_code: str = Field(max_length=80)
    protocol_version: str = Field(max_length=40)
    algorithm_version: str | None = Field(default=None, max_length=100)
    device_manufacturer: str | None = Field(default=None, max_length=120)
    device_model: str | None = Field(default=None, max_length=120)
    device_serial: str | None = Field(default=None, max_length=120)
    technology: str | None = Field(default=None, max_length=80)
    frequencies_khz: str | None = Field(default=None, max_length=200)
    position: str | None = Field(default=None, max_length=80)
    source: str | None = Field(default=None, max_length=80)
    reliability: str = Field(default="unknown", max_length=20)
    preparation_status: str | None = Field(default=None, max_length=20)
    fasting_hours: Decimal | None = Field(default=None, sa_type=Numeric(6, 2))
    recent_exercise: bool | None = None
    bladder_emptied: bool | None = None
    hydration_status: str | None = Field(default=None, max_length=20)
    edema_present: bool | None = None
    observations: str | None = Field(default=None, max_length=3000)
    author_professional_id: uuid.UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True))


class NutritionalMeasurementValue(SQLModel, table=True):
    __tablename__ = "nutritional_measurement_values"
    __table_args__ = (
        CheckConstraint("value >= 0", name="ck_nutrition_measurement_value_non_negative"),
        CheckConstraint(
            "laterality IN ('none','left','right','bilateral')",
            name="ck_nutrition_measurement_value_laterality",
        ),
        CheckConstraint(
            "value_nature IN ('measured','calculated','device_reported')",
            name="ck_nutrition_measurement_value_nature",
        ),
        CheckConstraint(
            "attempt_number IS NULL OR attempt_number BETWEEN 1 AND 3",
            name="ck_nutrition_measurement_value_attempt",
        ),
        Index(
            "ix_nutrition_measurement_value_session_code",
            "session_id",
            "measurement_code",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    session_id: uuid.UUID = Field(
        foreign_key="nutritional_measurement_sessions.id", index=True
    )
    measurement_code: str = Field(max_length=80, index=True)
    body_site: str | None = Field(default=None, max_length=80)
    laterality: str = Field(default="none", max_length=20)
    attempt_number: int | None = None
    value: Decimal = Field(sa_type=Numeric(12, 4))
    unit: str = Field(max_length=20)
    value_nature: str = Field(max_length=30)
    observations: str | None = Field(default=None, max_length=1000)
    created_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True))


class NutritionalScreening(SQLModel, table=True):
    __tablename__ = "nutritional_screenings"
    __table_args__ = (
        CheckConstraint("total_score IS NULL OR total_score >= 0", name="ck_screening_score"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    admission_id: uuid.UUID = Field(foreign_key="admissions.id", index=True)
    encounter_id: uuid.UUID = Field(foreign_key="nutritional_care_encounters.id", index=True)
    tool_code: str = Field(index=True, max_length=50)
    tool_version: str = Field(max_length=50)
    algorithm_version: str = Field(max_length=80)
    total_score: Decimal | None = Field(default=None, sa_type=Numeric(8, 2))
    classification: str | None = Field(default=None, max_length=100)
    no_tool_reason: str | None = Field(default=None, max_length=1000)
    applied_at: datetime = Field(sa_type=DateTime(timezone=True), index=True)
    author_professional_id: uuid.UUID = Field(foreign_key="users.id")
    inputs_snapshot: dict[str, Any] | None = Field(default=None, sa_type=CLINICAL_JSON)
    created_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True))


class NutritionalScreeningAnswer(SQLModel, table=True):
    __tablename__ = "nutritional_screening_answers"
    __table_args__ = (
        UniqueConstraint("screening_id", "answer_code", name="uq_screening_answer_code"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    screening_id: uuid.UUID = Field(foreign_key="nutritional_screenings.id", index=True)
    answer_code: str = Field(max_length=80)
    answer_value: str = Field(max_length=500)
    component_score: Decimal | None = Field(default=None, sa_type=Numeric(8, 2))


class NutritionalRequirementCalculation(SQLModel, table=True):
    __tablename__ = "nutritional_requirement_calculations"
    __table_args__ = (
        CheckConstraint("automatic_result >= 0", name="ck_requirement_result_non_negative"),
        CheckConstraint("adopted_result >= 0", name="ck_requirement_adopted_non_negative"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    admission_id: uuid.UUID = Field(foreign_key="admissions.id", index=True)
    encounter_id: uuid.UUID = Field(foreign_key="nutritional_care_encounters.id", index=True)
    nutrient_code: str = Field(index=True, max_length=40)
    method: str = Field(index=True, max_length=50)
    formula_version: str = Field(max_length=80)
    reference: str | None = Field(default=None, max_length=500)
    base_equation: str | None = Field(default=None, max_length=500)
    weight_measurement_id: uuid.UUID | None = Field(
        default=None, foreign_key="nutritional_anthropometric_measurements.id"
    )
    weight_type: str | None = Field(default=None, max_length=60)
    weight_value: Decimal | None = Field(default=None, sa_type=Numeric(12, 4))
    weight_measured_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    weight_selection_reason: str | None = Field(default=None, max_length=1000)
    activity_factor: Decimal | None = Field(default=None, sa_type=Numeric(8, 4))
    stress_factor: Decimal | None = Field(default=None, sa_type=Numeric(8, 4))
    thermal_factor: Decimal | None = Field(default=None, sa_type=Numeric(8, 4))
    basal_result: Decimal | None = Field(default=None, sa_type=Numeric(12, 2))
    automatic_result: Decimal = Field(sa_type=Numeric(12, 2))
    adopted_result: Decimal = Field(sa_type=Numeric(12, 2))
    minimum_result: Decimal | None = Field(default=None, sa_type=Numeric(12, 2))
    maximum_result: Decimal | None = Field(default=None, sa_type=Numeric(12, 2))
    unit: str = Field(max_length=30)
    rounding: str | None = Field(default=None, max_length=80)
    was_manually_adjusted: bool = False
    manual_adjustment_reason: str | None = Field(default=None, max_length=1000)
    inputs_snapshot: dict[str, Any] | None = Field(default=None, sa_type=CLINICAL_JSON)
    author_professional_id: uuid.UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True))


class NutritionalDiagnosis(SQLModel, table=True):
    __tablename__ = "nutritional_diagnoses"
    __table_args__ = (
        CheckConstraint("priority > 0", name="ck_nutrition_diagnosis_priority"),
        CheckConstraint(
            "status IN ('active','improved','resolved','discarded')",
            name="ck_nutrition_diagnosis_status",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    admission_id: uuid.UUID = Field(foreign_key="admissions.id", index=True)
    encounter_id: uuid.UUID = Field(foreign_key="nutritional_care_encounters.id", index=True)
    problem: str = Field(max_length=1000)
    etiology: str = Field(max_length=1000)
    signs_and_symptoms: str = Field(max_length=2000)
    generated_statement: str = Field(max_length=4000)
    priority: int = Field(default=1)
    status: str = Field(default="active", max_length=20, index=True)
    resolved_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    author_professional_id: uuid.UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True))


class NutritionalPrescription(SQLModel, table=True):
    __tablename__ = "nutritional_prescriptions"
    __table_args__ = (
        UniqueConstraint("encounter_id", name="uq_nutrition_prescription_encounter"),
        CheckConstraint(
            "primary_route IN ('oral','enteral','parenteral','mixed','fasting','other')",
            name="ck_nutrition_prescription_route",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    admission_id: uuid.UUID = Field(foreign_key="admissions.id", index=True)
    encounter_id: uuid.UUID = Field(foreign_key="nutritional_care_encounters.id", index=True)
    effective_from: datetime = Field(sa_type=DateTime(timezone=True), index=True)
    effective_until: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    status: str = Field(default="active", max_length=20, index=True)
    primary_route: str = Field(max_length=20)
    complementary_routes: str | None = Field(default=None, max_length=200)
    energy_target: Decimal | None = Field(default=None, sa_type=Numeric(12, 2))
    protein_target: Decimal | None = Field(default=None, sa_type=Numeric(12, 2))
    fluid_target: Decimal | None = Field(default=None, sa_type=Numeric(12, 2))
    regimen_type: str | None = Field(default=None, max_length=300)
    texture: str | None = Field(default=None, max_length=200)
    restrictions: str | None = Field(default=None, max_length=2000)
    allergies_considered: str | None = Field(default=None, max_length=2000)
    oral_supplements: str | None = Field(default=None, max_length=2000)
    enteral_support: str | None = Field(default=None, max_length=2000)
    parenteral_support: str | None = Field(default=None, max_length=2000)
    general_instructions: str | None = Field(default=None, max_length=4000)
    observations: str | None = Field(default=None, max_length=3000)
    author_professional_id: uuid.UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True))


class NutritionalPrescriptionMealTime(SQLModel, table=True):
    __tablename__ = "nutritional_prescription_meal_times"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    prescription_id: uuid.UUID = Field(foreign_key="nutritional_prescriptions.id", index=True)
    meal_time: str = Field(max_length=40)
    regimen: str = Field(max_length=1000)
    texture: str | None = Field(default=None, max_length=200)
    restrictions: str | None = Field(default=None, max_length=1000)
    supplement: str | None = Field(default=None, max_length=1000)
    observations: str | None = Field(default=None, max_length=1000)


class NutritionalMonitoringRecord(SQLModel, table=True):
    __tablename__ = "nutritional_monitoring_records"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    admission_id: uuid.UUID = Field(foreign_key="admissions.id", index=True)
    encounter_id: uuid.UUID = Field(foreign_key="nutritional_care_encounters.id", index=True)
    record_type: str = Field(index=True, max_length=60)
    value: str = Field(max_length=1000)
    unit: str | None = Field(default=None, max_length=30)
    observed_at: datetime = Field(sa_type=DateTime(timezone=True), index=True)
    source: str | None = Field(default=None, max_length=80)
    author_professional_id: uuid.UUID = Field(foreign_key="users.id")
    observations: str | None = Field(default=None, max_length=2000)


class NutritionalIntakeRecord(SQLModel, table=True):
    __tablename__ = "nutritional_intake_records"
    __table_args__ = (
        CheckConstraint(
            "consumed_percentage IS NULL OR (consumed_percentage >= 0 AND consumed_percentage <= 100)",
            name="ck_nutrition_intake_percentage",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    admission_id: uuid.UUID = Field(foreign_key="admissions.id", index=True)
    encounter_id: uuid.UUID = Field(foreign_key="nutritional_care_encounters.id", index=True)
    intake_date: date = Field(index=True)
    meal_time: str = Field(index=True, max_length=40)
    consumed_percentage: Decimal | None = Field(default=None, sa_type=Numeric(5, 2))
    offered_amount: Decimal | None = Field(default=None, sa_type=Numeric(12, 3))
    consumed_amount: Decimal | None = Field(default=None, sa_type=Numeric(12, 3))
    unit: str | None = Field(default=None, max_length=30)
    incomplete_reason: str | None = Field(default=None, max_length=1000)
    observations: str | None = Field(default=None, max_length=2000)
    source: str | None = Field(default=None, max_length=80)
    author_professional_id: uuid.UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True))


class NutritionalLabObservation(SQLModel, table=True):
    __tablename__ = "nutritional_lab_observations"
    __table_args__ = (
        CheckConstraint(
            "flag IS NULL OR flag IN ('low','normal','high','critical')",
            name="ck_nutrition_lab_flag",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    admission_id: uuid.UUID = Field(foreign_key="admissions.id", index=True)
    encounter_id: uuid.UUID = Field(foreign_key="nutritional_care_encounters.id", index=True)
    test_name: str = Field(index=True, max_length=200)
    local_code: str | None = Field(default=None, max_length=80)
    value: str = Field(max_length=200)
    unit: str | None = Field(default=None, max_length=40)
    reference_range: str | None = Field(default=None, max_length=200)
    flag: str | None = Field(default=None, max_length=20)
    sampled_at: datetime = Field(sa_type=DateTime(timezone=True), index=True)
    recorded_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True))
    source: str = Field(max_length=80)
    author_professional_id: uuid.UUID = Field(foreign_key="users.id")
    observation: str | None = Field(default=None, max_length=2000)


class NutritionalAlert(SQLModel, table=True):
    __tablename__ = "nutritional_alerts"
    __table_args__ = (
        CheckConstraint("severity IN ('info','warning','critical')", name="ck_nutrition_alert_severity"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    admission_id: uuid.UUID = Field(foreign_key="admissions.id", index=True)
    encounter_id: uuid.UUID = Field(foreign_key="nutritional_care_encounters.id", index=True)
    alert_type: str = Field(index=True, max_length=60)
    description: str = Field(max_length=2000)
    severity: str = Field(default="warning", max_length=20)
    source: str | None = Field(default=None, max_length=80)
    verification_status: str | None = Field(default=None, max_length=30)
    is_active: bool = Field(default=True, index=True)
    author_professional_id: uuid.UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True))
