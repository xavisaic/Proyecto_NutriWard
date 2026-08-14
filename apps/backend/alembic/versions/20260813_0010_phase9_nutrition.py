"""Create the structured Phase 9 nutritional clinical record.

Revision ID: 20260813_0010
Revises: 20260812_0009
Create Date: 2026-08-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260813_0010"
down_revision: str | None = "20260812_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = sa.Uuid
TZ = lambda: sa.DateTime(timezone=True)


def _id() -> sa.Column:
    return sa.Column("id", UUID(), nullable=False)


def _audit_columns() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column("created_at", TZ(), nullable=False),
        sa.Column("updated_at", TZ(), nullable=False),
    )


def _encounter_links() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column("admission_id", UUID(), nullable=False),
        sa.Column("encounter_id", UUID(), nullable=False),
    )


def _link_constraints() -> tuple[sa.ForeignKeyConstraint, sa.ForeignKeyConstraint]:
    return (
        sa.ForeignKeyConstraint(["admission_id"], ["admissions.id"]),
        sa.ForeignKeyConstraint(["encounter_id"], ["nutritional_care_encounters.id"]),
    )


def _indexes(table: str, *columns: str) -> None:
    for column in columns:
        op.create_index(f"ix_{table}_{column}", table, [column])


def upgrade() -> None:
    op.create_table(
        "nutritional_care_encounters",
        _id(),
        sa.Column("admission_id", UUID(), nullable=False),
        sa.Column("encounter_datetime", TZ(), nullable=False),
        sa.Column("encounter_type", sa.String(30), nullable=False),
        sa.Column("author_professional_id", UUID(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("clinical_summary", sa.String(4000), nullable=True),
        sa.Column("reason_for_assessment", sa.String(2000), nullable=True),
        sa.Column("information_source", sa.String(80), nullable=True),
        sa.Column("finalized_at", TZ(), nullable=True),
        sa.Column("finalized_by", UUID(), nullable=True),
        sa.Column("correction_reason", sa.String(1000), nullable=True),
        sa.Column("corrected_encounter_id", UUID(), nullable=True),
        sa.Column("cancellation_reason", sa.String(1000), nullable=True),
        sa.Column("cancelled_at", TZ(), nullable=True),
        sa.Column("cancelled_by", UUID(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        *_audit_columns(),
        sa.CheckConstraint(
            "encounter_type IN ('initial_assessment','follow_up','reassessment',"
            "'discharge_planning','other')",
            name="ck_nutrition_encounter_type",
        ),
        sa.CheckConstraint(
            "status IN ('draft','finalized','corrected','cancelled')",
            name="ck_nutrition_encounter_status",
        ),
        sa.CheckConstraint("version > 0", name="ck_nutrition_encounter_version_positive"),
        sa.CheckConstraint(
            "corrected_encounter_id IS NULL OR corrected_encounter_id != id",
            name="ck_nutrition_encounter_not_self_corrected",
        ),
        sa.ForeignKeyConstraint(["admission_id"], ["admissions.id"]),
        sa.ForeignKeyConstraint(["author_professional_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["finalized_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["corrected_encounter_id"], ["nutritional_care_encounters.id"]),
        sa.ForeignKeyConstraint(["cancelled_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    _indexes(
        "nutritional_care_encounters",
        "admission_id", "encounter_datetime", "author_professional_id", "status",
        "corrected_encounter_id",
    )
    op.create_index(
        "ix_nutrition_encounter_admission_datetime_status",
        "nutritional_care_encounters",
        ["admission_id", "encounter_datetime", "status"],
    )

    op.create_table(
        "nutritional_assessments",
        _id(), *_encounter_links(),
        sa.Column("population_group", sa.String(20), nullable=False),
        sa.Column("medical_diagnoses_summary", sa.String(3000), nullable=True),
        sa.Column("hospitalization_reason", sa.String(2000), nullable=True),
        sa.Column("current_feeding_route", sa.String(50), nullable=True),
        sa.Column("appetite", sa.String(100), nullable=True),
        sa.Column("clinical_findings", sa.String(4000), nullable=True),
        sa.Column("digestive_findings", sa.String(4000), nullable=True),
        sa.Column("nutritional_status", sa.String(500), nullable=True),
        sa.Column("gestational_age_weeks", sa.Numeric(5, 2), nullable=True),
        sa.Column("gestation_type", sa.String(20), nullable=True),
        sa.Column("corrected_age_days", sa.Integer(), nullable=True),
        sa.Column("growth_reference_code", sa.String(80), nullable=True),
        sa.Column("growth_reference_version", sa.String(80), nullable=True),
        sa.Column("objectives", sa.String(4000), nullable=True),
        sa.Column("monitoring_plan", sa.String(4000), nullable=True),
        sa.Column("pending_actions", sa.String(3000), nullable=True),
        sa.Column("suggested_reassessment_at", TZ(), nullable=True),
        sa.Column("observations", sa.String(5000), nullable=True),
        sa.Column("observed_at", TZ(), nullable=False),
        sa.Column("author_professional_id", UUID(), nullable=False),
        *_audit_columns(),
        sa.CheckConstraint(
            "population_group IN ('adult','pediatric','neonatal','pregnancy')",
            name="ck_nutrition_assessment_population",
        ),
        *_link_constraints(),
        sa.ForeignKeyConstraint(["author_professional_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("encounter_id", name="uq_nutrition_assessment_encounter"),
    )
    _indexes("nutritional_assessments", "admission_id", "encounter_id", "population_group", "suggested_reassessment_at")

    op.create_table(
        "nutritional_clinical_context_items",
        _id(), *_encounter_links(),
        sa.Column("category", sa.String(60), nullable=False),
        sa.Column("description", sa.String(2000), nullable=False),
        sa.Column("item_status", sa.String(30), nullable=True),
        sa.Column("source", sa.String(80), nullable=True),
        sa.Column("verification_status", sa.String(30), nullable=True),
        sa.Column("observed_at", TZ(), nullable=False),
        sa.Column("author_professional_id", UUID(), nullable=False),
        sa.Column("complementary_observation", sa.String(2000), nullable=True),
        sa.Column("created_at", TZ(), nullable=False),
        *_link_constraints(),
        sa.ForeignKeyConstraint(["author_professional_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    _indexes("nutritional_clinical_context_items", "admission_id", "encounter_id", "category")

    op.create_table(
        "nutritional_anthropometric_measurements",
        _id(), *_encounter_links(),
        sa.Column("measurement_type", sa.String(60), nullable=False),
        sa.Column("value", sa.Numeric(12, 4), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False),
        sa.Column("measured_at", TZ(), nullable=False),
        sa.Column("method", sa.String(120), nullable=True),
        sa.Column("source", sa.String(80), nullable=True),
        sa.Column("reliability", sa.String(20), nullable=False),
        sa.Column("value_nature", sa.String(20), nullable=False),
        sa.Column("author_professional_id", UUID(), nullable=False),
        sa.Column("observations", sa.String(2000), nullable=True),
        sa.Column("calculated_value", sa.Numeric(12, 4), nullable=True),
        sa.Column("manual_value_used", sa.Numeric(12, 4), nullable=True),
        sa.Column("manual_adjustment_reason", sa.String(1000), nullable=True),
        sa.Column("created_at", TZ(), nullable=False),
        sa.CheckConstraint("value >= 0", name="ck_nutrition_measurement_non_negative"),
        sa.CheckConstraint("reliability IN ('high','medium','low','unknown')", name="ck_nutrition_measurement_reliability"),
        sa.CheckConstraint("value_nature IN ('measured','reported','estimated','calculated')", name="ck_nutrition_measurement_nature"),
        *_link_constraints(),
        sa.ForeignKeyConstraint(["author_professional_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    _indexes("nutritional_anthropometric_measurements", "admission_id", "encounter_id", "measurement_type", "measured_at")

    op.create_table(
        "nutritional_screenings",
        _id(), *_encounter_links(),
        sa.Column("tool_code", sa.String(50), nullable=False),
        sa.Column("tool_version", sa.String(50), nullable=False),
        sa.Column("algorithm_version", sa.String(80), nullable=False),
        sa.Column("total_score", sa.Numeric(8, 2), nullable=True),
        sa.Column("classification", sa.String(100), nullable=True),
        sa.Column("no_tool_reason", sa.String(1000), nullable=True),
        sa.Column("applied_at", TZ(), nullable=False),
        sa.Column("author_professional_id", UUID(), nullable=False),
        sa.Column("inputs_snapshot", sa.JSON(), nullable=True),
        sa.Column("created_at", TZ(), nullable=False),
        sa.CheckConstraint("total_score IS NULL OR total_score >= 0", name="ck_screening_score"),
        *_link_constraints(),
        sa.ForeignKeyConstraint(["author_professional_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    _indexes("nutritional_screenings", "admission_id", "encounter_id", "tool_code", "applied_at")

    op.create_table(
        "nutritional_screening_answers",
        _id(),
        sa.Column("screening_id", UUID(), nullable=False),
        sa.Column("answer_code", sa.String(80), nullable=False),
        sa.Column("answer_value", sa.String(500), nullable=False),
        sa.Column("component_score", sa.Numeric(8, 2), nullable=True),
        sa.ForeignKeyConstraint(["screening_id"], ["nutritional_screenings.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("screening_id", "answer_code", name="uq_screening_answer_code"),
    )
    _indexes("nutritional_screening_answers", "screening_id")

    op.create_table(
        "nutritional_requirement_calculations",
        _id(), *_encounter_links(),
        sa.Column("nutrient_code", sa.String(40), nullable=False),
        sa.Column("method", sa.String(50), nullable=False),
        sa.Column("formula_version", sa.String(80), nullable=False),
        sa.Column("reference", sa.String(500), nullable=True),
        sa.Column("base_equation", sa.String(500), nullable=True),
        sa.Column("weight_measurement_id", UUID(), nullable=True),
        sa.Column("weight_type", sa.String(60), nullable=True),
        sa.Column("weight_value", sa.Numeric(12, 4), nullable=True),
        sa.Column("weight_measured_at", TZ(), nullable=True),
        sa.Column("weight_selection_reason", sa.String(1000), nullable=True),
        sa.Column("activity_factor", sa.Numeric(8, 4), nullable=True),
        sa.Column("stress_factor", sa.Numeric(8, 4), nullable=True),
        sa.Column("thermal_factor", sa.Numeric(8, 4), nullable=True),
        sa.Column("basal_result", sa.Numeric(12, 2), nullable=True),
        sa.Column("automatic_result", sa.Numeric(12, 2), nullable=False),
        sa.Column("adopted_result", sa.Numeric(12, 2), nullable=False),
        sa.Column("minimum_result", sa.Numeric(12, 2), nullable=True),
        sa.Column("maximum_result", sa.Numeric(12, 2), nullable=True),
        sa.Column("unit", sa.String(30), nullable=False),
        sa.Column("rounding", sa.String(80), nullable=True),
        sa.Column("was_manually_adjusted", sa.Boolean(), nullable=False),
        sa.Column("manual_adjustment_reason", sa.String(1000), nullable=True),
        sa.Column("inputs_snapshot", sa.JSON(), nullable=True),
        sa.Column("author_professional_id", UUID(), nullable=False),
        sa.Column("created_at", TZ(), nullable=False),
        sa.CheckConstraint("automatic_result >= 0", name="ck_requirement_result_non_negative"),
        sa.CheckConstraint("adopted_result >= 0", name="ck_requirement_adopted_non_negative"),
        *_link_constraints(),
        sa.ForeignKeyConstraint(["weight_measurement_id"], ["nutritional_anthropometric_measurements.id"]),
        sa.ForeignKeyConstraint(["author_professional_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    _indexes("nutritional_requirement_calculations", "admission_id", "encounter_id", "nutrient_code", "method")

    op.create_table(
        "nutritional_diagnoses",
        _id(), *_encounter_links(),
        sa.Column("problem", sa.String(1000), nullable=False),
        sa.Column("etiology", sa.String(1000), nullable=False),
        sa.Column("signs_and_symptoms", sa.String(2000), nullable=False),
        sa.Column("generated_statement", sa.String(4000), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("resolved_at", TZ(), nullable=True),
        sa.Column("author_professional_id", UUID(), nullable=False),
        sa.Column("created_at", TZ(), nullable=False),
        sa.CheckConstraint("priority > 0", name="ck_nutrition_diagnosis_priority"),
        sa.CheckConstraint("status IN ('active','improved','resolved','discarded')", name="ck_nutrition_diagnosis_status"),
        *_link_constraints(),
        sa.ForeignKeyConstraint(["author_professional_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    _indexes("nutritional_diagnoses", "admission_id", "encounter_id", "status")

    op.create_table(
        "nutritional_prescriptions",
        _id(), *_encounter_links(),
        sa.Column("effective_from", TZ(), nullable=False),
        sa.Column("effective_until", TZ(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("primary_route", sa.String(20), nullable=False),
        sa.Column("complementary_routes", sa.String(200), nullable=True),
        sa.Column("energy_target", sa.Numeric(12, 2), nullable=True),
        sa.Column("protein_target", sa.Numeric(12, 2), nullable=True),
        sa.Column("fluid_target", sa.Numeric(12, 2), nullable=True),
        sa.Column("regimen_type", sa.String(300), nullable=True),
        sa.Column("texture", sa.String(200), nullable=True),
        sa.Column("restrictions", sa.String(2000), nullable=True),
        sa.Column("allergies_considered", sa.String(2000), nullable=True),
        sa.Column("oral_supplements", sa.String(2000), nullable=True),
        sa.Column("enteral_support", sa.String(2000), nullable=True),
        sa.Column("parenteral_support", sa.String(2000), nullable=True),
        sa.Column("general_instructions", sa.String(4000), nullable=True),
        sa.Column("observations", sa.String(3000), nullable=True),
        sa.Column("author_professional_id", UUID(), nullable=False),
        sa.Column("created_at", TZ(), nullable=False),
        sa.CheckConstraint("primary_route IN ('oral','enteral','parenteral','mixed','fasting','other')", name="ck_nutrition_prescription_route"),
        *_link_constraints(),
        sa.ForeignKeyConstraint(["author_professional_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("encounter_id", name="uq_nutrition_prescription_encounter"),
    )
    _indexes("nutritional_prescriptions", "admission_id", "encounter_id", "effective_from", "status")

    op.create_table(
        "nutritional_prescription_meal_times",
        _id(),
        sa.Column("prescription_id", UUID(), nullable=False),
        sa.Column("meal_time", sa.String(40), nullable=False),
        sa.Column("regimen", sa.String(1000), nullable=False),
        sa.Column("texture", sa.String(200), nullable=True),
        sa.Column("restrictions", sa.String(1000), nullable=True),
        sa.Column("supplement", sa.String(1000), nullable=True),
        sa.Column("observations", sa.String(1000), nullable=True),
        sa.ForeignKeyConstraint(["prescription_id"], ["nutritional_prescriptions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    _indexes("nutritional_prescription_meal_times", "prescription_id")

    op.create_table(
        "nutritional_monitoring_records",
        _id(), *_encounter_links(),
        sa.Column("record_type", sa.String(60), nullable=False),
        sa.Column("value", sa.String(1000), nullable=False),
        sa.Column("unit", sa.String(30), nullable=True),
        sa.Column("observed_at", TZ(), nullable=False),
        sa.Column("source", sa.String(80), nullable=True),
        sa.Column("author_professional_id", UUID(), nullable=False),
        sa.Column("observations", sa.String(2000), nullable=True),
        *_link_constraints(),
        sa.ForeignKeyConstraint(["author_professional_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    _indexes("nutritional_monitoring_records", "admission_id", "encounter_id", "record_type", "observed_at")

    op.create_table(
        "nutritional_intake_records",
        _id(), *_encounter_links(),
        sa.Column("intake_date", sa.Date(), nullable=False),
        sa.Column("meal_time", sa.String(40), nullable=False),
        sa.Column("consumed_percentage", sa.Numeric(5, 2), nullable=True),
        sa.Column("offered_amount", sa.Numeric(12, 3), nullable=True),
        sa.Column("consumed_amount", sa.Numeric(12, 3), nullable=True),
        sa.Column("unit", sa.String(30), nullable=True),
        sa.Column("incomplete_reason", sa.String(1000), nullable=True),
        sa.Column("observations", sa.String(2000), nullable=True),
        sa.Column("source", sa.String(80), nullable=True),
        sa.Column("author_professional_id", UUID(), nullable=False),
        sa.Column("created_at", TZ(), nullable=False),
        sa.CheckConstraint("consumed_percentage IS NULL OR (consumed_percentage >= 0 AND consumed_percentage <= 100)", name="ck_nutrition_intake_percentage"),
        *_link_constraints(),
        sa.ForeignKeyConstraint(["author_professional_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    _indexes("nutritional_intake_records", "admission_id", "encounter_id", "intake_date", "meal_time")

    op.create_table(
        "nutritional_lab_observations",
        _id(), *_encounter_links(),
        sa.Column("test_name", sa.String(200), nullable=False),
        sa.Column("local_code", sa.String(80), nullable=True),
        sa.Column("value", sa.String(200), nullable=False),
        sa.Column("unit", sa.String(40), nullable=True),
        sa.Column("reference_range", sa.String(200), nullable=True),
        sa.Column("flag", sa.String(20), nullable=True),
        sa.Column("sampled_at", TZ(), nullable=False),
        sa.Column("recorded_at", TZ(), nullable=False),
        sa.Column("source", sa.String(80), nullable=False),
        sa.Column("author_professional_id", UUID(), nullable=False),
        sa.Column("observation", sa.String(2000), nullable=True),
        sa.CheckConstraint("flag IS NULL OR flag IN ('low','normal','high','critical')", name="ck_nutrition_lab_flag"),
        *_link_constraints(),
        sa.ForeignKeyConstraint(["author_professional_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    _indexes("nutritional_lab_observations", "admission_id", "encounter_id", "test_name", "sampled_at")

    op.create_table(
        "nutritional_alerts",
        _id(), *_encounter_links(),
        sa.Column("alert_type", sa.String(60), nullable=False),
        sa.Column("description", sa.String(2000), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("source", sa.String(80), nullable=True),
        sa.Column("verification_status", sa.String(30), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("author_professional_id", UUID(), nullable=False),
        sa.Column("created_at", TZ(), nullable=False),
        sa.CheckConstraint("severity IN ('info','warning','critical')", name="ck_nutrition_alert_severity"),
        *_link_constraints(),
        sa.ForeignKeyConstraint(["author_professional_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    _indexes("nutritional_alerts", "admission_id", "encounter_id", "alert_type", "is_active")


def downgrade() -> None:
    for table in (
        "nutritional_alerts",
        "nutritional_lab_observations",
        "nutritional_intake_records",
        "nutritional_monitoring_records",
        "nutritional_prescription_meal_times",
        "nutritional_prescriptions",
        "nutritional_diagnoses",
        "nutritional_requirement_calculations",
        "nutritional_screening_answers",
        "nutritional_screenings",
        "nutritional_anthropometric_measurements",
        "nutritional_clinical_context_items",
        "nutritional_assessments",
        "nutritional_care_encounters",
    ):
        op.drop_table(table)
