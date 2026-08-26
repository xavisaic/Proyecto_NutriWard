"""Add versioned nutrition prescription workspace.

Revision ID: 20260826_0017
Revises: 20260826_0016
Create Date: 2026-08-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260826_0017"
down_revision: str | None = "20260826_0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "enteral_formula_catalog_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(60), nullable=False),
        sa.Column("display_name", sa.String(300), nullable=False),
        sa.Column("manufacturer", sa.String(200), nullable=True),
        sa.Column("catalog_version", sa.String(80), nullable=False),
        sa.Column("kcal_per_ml", sa.Numeric(10, 4), nullable=False),
        sa.Column("protein_g_per_l", sa.Numeric(12, 4), nullable=False),
        sa.Column("carbohydrate_g_per_l", sa.Numeric(12, 4), nullable=False),
        sa.Column("lipid_g_per_l", sa.Numeric(12, 4), nullable=False),
        sa.Column("fiber_g_per_l", sa.Numeric(12, 4), nullable=False),
        sa.Column("sodium_mg_per_l", sa.Numeric(12, 4), nullable=False),
        sa.Column("potassium_mg_per_l", sa.Numeric(12, 4), nullable=False),
        sa.Column("phosphorus_mg_per_l", sa.Numeric(12, 4), nullable=False),
        sa.Column("free_water_ml_per_l", sa.Numeric(12, 4), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("kcal_per_ml > 0", name="ck_enteral_formula_kcal_positive"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", "catalog_version", name="uq_enteral_formula_code_version"),
    )
    op.create_index("ix_enteral_formula_active_name", "enteral_formula_catalog_items", ["is_active", "display_name"])
    for column in ("code", "display_name", "catalog_version", "is_active"):
        op.create_index(f"ix_enteral_formula_catalog_items_{column}", "enteral_formula_catalog_items", [column])

    op.create_table(
        "nutrition_prescription_settings",
        sa.Column("key", sa.String(40), nullable=False),
        sa.Column("green_min_percent", sa.Numeric(6, 2), nullable=False),
        sa.Column("green_max_percent", sa.Numeric(6, 2), nullable=False),
        sa.Column("yellow_min_percent", sa.Numeric(6, 2), nullable=False),
        sa.Column("yellow_max_percent", sa.Numeric(6, 2), nullable=False),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("key"),
    )

    op.create_table(
        "nutrition_prescription_orders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("admission_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("lock_version", sa.Integer(), nullable=False),
        sa.Column("supersedes_order_id", sa.Uuid(), nullable=True),
        sa.Column("source_encounter_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("change_reason", sa.String(1000), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("suggested_reassessment_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("oral_enabled", sa.Boolean(), nullable=False),
        sa.Column("enteral_enabled", sa.Boolean(), nullable=False),
        sa.Column("fasting_enabled", sa.Boolean(), nullable=False),
        sa.Column("energy_goal_kcal", sa.Numeric(12, 2), nullable=True),
        sa.Column("protein_goal_g", sa.Numeric(12, 2), nullable=True),
        sa.Column("carbohydrate_goal_g", sa.Numeric(12, 2), nullable=True),
        sa.Column("lipid_goal_g", sa.Numeric(12, 2), nullable=True),
        sa.Column("fluid_goal_ml", sa.Numeric(12, 2), nullable=True),
        sa.Column("fluid_goal_kind", sa.String(20), nullable=False),
        sa.Column("regimen_type", sa.String(300), nullable=True),
        sa.Column("food_iddsi", sa.Integer(), nullable=True),
        sa.Column("liquid_iddsi", sa.Integer(), nullable=True),
        sa.Column("restrictions", sa.String(2000), nullable=True),
        sa.Column("allergies_snapshot", sa.String(2000), nullable=True),
        sa.Column("feeding_assistance", sa.String(200), nullable=True),
        sa.Column("kitchen_instructions", sa.String(3000), nullable=True),
        sa.Column("nursing_instructions", sa.String(3000), nullable=True),
        sa.Column("oral_energy_kcal", sa.Numeric(12, 2), nullable=False),
        sa.Column("oral_protein_g", sa.Numeric(12, 2), nullable=False),
        sa.Column("oral_carbohydrate_g", sa.Numeric(12, 2), nullable=False),
        sa.Column("oral_lipid_g", sa.Numeric(12, 2), nullable=False),
        sa.Column("oral_fluid_ml", sa.Numeric(12, 2), nullable=False),
        sa.Column("enteral_formula_id", sa.Uuid(), nullable=True),
        sa.Column("enteral_access_route", sa.String(100), nullable=True),
        sa.Column("enteral_tube_location", sa.String(100), nullable=True),
        sa.Column("enteral_modality", sa.String(40), nullable=True),
        sa.Column("enteral_rate_ml_h", sa.Numeric(12, 2), nullable=True),
        sa.Column("enteral_effective_hours", sa.Numeric(8, 2), nullable=True),
        sa.Column("enteral_volume_ml", sa.Numeric(12, 2), nullable=False),
        sa.Column("water_flush_ml", sa.Numeric(12, 2), nullable=False),
        sa.Column("water_flush_every_hours", sa.Numeric(8, 2), nullable=True),
        sa.Column("medication_pause_hours", sa.Numeric(8, 2), nullable=False),
        sa.Column("enteral_starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("prescribed_energy_kcal", sa.Numeric(12, 2), nullable=False),
        sa.Column("prescribed_protein_g", sa.Numeric(12, 2), nullable=False),
        sa.Column("prescribed_carbohydrate_g", sa.Numeric(12, 2), nullable=False),
        sa.Column("prescribed_lipid_g", sa.Numeric(12, 2), nullable=False),
        sa.Column("prescribed_fluid_ml", sa.Numeric(12, 2), nullable=False),
        sa.Column("recipe_text", sa.String(8000), nullable=True),
        sa.Column("general_observations", sa.String(3000), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("validated_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("activated_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("suspended_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("suspended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("suspension_reason", sa.String(1000), nullable=True),
        sa.CheckConstraint("version_number > 0", name="ck_prescription_order_version_positive"),
        sa.CheckConstraint("lock_version > 0", name="ck_prescription_order_lock_positive"),
        sa.CheckConstraint("status IN ('draft','validated','active','suspended','superseded','cancelled')", name="ck_prescription_order_status"),
        sa.CheckConstraint("fluid_goal_kind IN ('target','minimum','maximum','range')", name="ck_prescription_order_fluid_goal_kind"),
        sa.CheckConstraint("food_iddsi IS NULL OR (food_iddsi >= 3 AND food_iddsi <= 7)", name="ck_prescription_food_iddsi"),
        sa.CheckConstraint("liquid_iddsi IS NULL OR (liquid_iddsi >= 0 AND liquid_iddsi <= 4)", name="ck_prescription_liquid_iddsi"),
        sa.ForeignKeyConstraint(["admission_id"], ["admissions.id"]),
        sa.ForeignKeyConstraint(["supersedes_order_id"], ["nutrition_prescription_orders.id"]),
        sa.ForeignKeyConstraint(["source_encounter_id"], ["nutritional_care_encounters.id"]),
        sa.ForeignKeyConstraint(["enteral_formula_id"], ["enteral_formula_catalog_items.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["validated_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["activated_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["suspended_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("admission_id", "version_number", name="uq_prescription_order_admission_version"),
    )
    op.create_index("ix_prescription_order_admission_status", "nutrition_prescription_orders", ["admission_id", "status"])
    op.create_index(
        "uq_prescription_order_one_active_per_admission",
        "nutrition_prescription_orders",
        ["admission_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
        sqlite_where=sa.text("status = 'active'"),
    )
    op.create_index("ix_nutrition_prescription_orders_admission_id", "nutrition_prescription_orders", ["admission_id"])
    op.create_index("ix_nutrition_prescription_orders_status", "nutrition_prescription_orders", ["status"])

    child_tables = (
        ("nutrition_prescription_order_meals", [sa.Column("meal_time", sa.String(40), nullable=False), sa.Column("instruction", sa.String(1000), nullable=False)]),
        ("nutrition_prescription_supplements", [
            sa.Column("product_type", sa.String(60), nullable=False), sa.Column("product_name", sa.String(300), nullable=False),
            sa.Column("dose", sa.Numeric(12, 2), nullable=True), sa.Column("dose_unit", sa.String(40), nullable=True),
            sa.Column("schedule", sa.String(200), nullable=True), sa.Column("route", sa.String(60), nullable=True),
            sa.Column("duration", sa.String(200), nullable=True), sa.Column("energy_kcal", sa.Numeric(12, 2), nullable=False),
            sa.Column("protein_g", sa.Numeric(12, 2), nullable=False), sa.Column("carbohydrate_g", sa.Numeric(12, 2), nullable=False),
            sa.Column("lipid_g", sa.Numeric(12, 2), nullable=False), sa.Column("fluid_ml", sa.Numeric(12, 2), nullable=False),
        ]),
        ("nutrition_prescription_progressions", [
            sa.Column("sequence", sa.Integer(), nullable=False), sa.Column("stage", sa.String(100), nullable=False),
            sa.Column("rate_ml_h", sa.Numeric(12, 2), nullable=False), sa.Column("duration_hours", sa.Numeric(8, 2), nullable=False),
            sa.Column("condition", sa.String(1000), nullable=True),
        ]),
        ("nutrition_prescription_monitoring", [
            sa.Column("parameter", sa.String(200), nullable=False), sa.Column("frequency", sa.String(200), nullable=False),
            sa.Column("responsible", sa.String(200), nullable=True), sa.Column("instruction", sa.String(1000), nullable=True),
        ]),
    )
    for table_name, columns in child_tables:
        op.create_table(
            table_name,
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("order_id", sa.Uuid(), nullable=False),
            *columns,
            sa.ForeignKeyConstraint(["order_id"], ["nutrition_prescription_orders.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(f"ix_{table_name}_order_id", table_name, ["order_id"])


def downgrade() -> None:
    for table_name in (
        "nutrition_prescription_monitoring",
        "nutrition_prescription_progressions",
        "nutrition_prescription_supplements",
        "nutrition_prescription_order_meals",
    ):
        op.drop_table(table_name)
    op.drop_table("nutrition_prescription_orders")
    op.drop_table("nutrition_prescription_settings")
    op.drop_table("enteral_formula_catalog_items")
