"""Add structured meal plans, catalog and modular preparations.

Revision ID: 20260829_0017
Revises: 20260826_0016
Create Date: 2026-08-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260829_0017"
down_revision: str | None = "20260826_0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "food_regimen_catalog_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(80), nullable=False),
        sa.Column("display_name", sa.String(300), nullable=False),
        sa.Column("normalized_name", sa.String(400), nullable=False),
        sa.Column("item_type", sa.String(30), nullable=False),
        sa.Column("default_unit", sa.String(30), nullable=False),
        sa.Column("standard_recipe_note", sa.String(1000), nullable=True),
        sa.Column("source_version", sa.String(80), nullable=False),
        sa.Column("source_row", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "item_type IN ('base_regimen','beverage','supplement','dessert',"
            "'bread_or_cereal','modifier','modular_product','other')",
            name="ck_food_catalog_item_type",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    for column in ("code", "display_name", "normalized_name", "item_type", "is_active"):
        op.create_index(
            f"ix_food_regimen_catalog_items_{column}",
            "food_regimen_catalog_items",
            [column],
        )
    op.create_index(
        "ix_food_catalog_search_active",
        "food_regimen_catalog_items",
        ["normalized_name", "is_active"],
    )

    op.create_table(
        "nutritional_meal_plans",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("admission_id", sa.Uuid(), nullable=False),
        sa.Column("source_prescription_id", sa.Uuid(), nullable=True),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_until", sa.Date(), nullable=True),
        sa.Column("validity_mode", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("oral_enabled", sa.Boolean(), nullable=False),
        sa.Column("enteral_enabled", sa.Boolean(), nullable=False),
        sa.Column("parenteral_enabled", sa.Boolean(), nullable=False),
        sa.Column("general_instructions", sa.String(4000), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("finalized_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('draft','finalized','superseded','cancelled')",
            name="ck_meal_plan_status",
        ),
        sa.CheckConstraint(
            "validity_mode IN ('until_changed','single_day','date_range')",
            name="ck_meal_plan_validity_mode",
        ),
        sa.CheckConstraint("version >= 1", name="ck_meal_plan_version"),
        sa.CheckConstraint(
            "effective_until IS NULL OR effective_until >= effective_from",
            name="ck_meal_plan_dates",
        ),
        sa.CheckConstraint(
            "oral_enabled OR enteral_enabled OR parenteral_enabled",
            name="ck_meal_plan_has_route",
        ),
        sa.ForeignKeyConstraint(["admission_id"], ["admissions.id"]),
        sa.ForeignKeyConstraint(
            ["source_prescription_id"], ["nutritional_prescriptions.id"]
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["finalized_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in (
        "admission_id",
        "source_prescription_id",
        "effective_from",
        "effective_until",
        "status",
    ):
        op.create_index(
            f"ix_nutritional_meal_plans_{column}",
            "nutritional_meal_plans",
            [column],
        )
    op.create_index(
        "ix_meal_plan_admission_status_dates",
        "nutritional_meal_plans",
        ["admission_id", "status", "effective_from"],
    )

    op.create_table(
        "nutritional_meal_plan_slots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("meal_plan_id", sa.Uuid(), nullable=False),
        sa.Column("meal_time", sa.String(30), nullable=False),
        sa.Column("fulfillment_status", sa.String(20), nullable=False),
        sa.Column("is_special", sa.Boolean(), nullable=False),
        sa.Column("special_instructions", sa.String(3000), nullable=True),
        sa.CheckConstraint(
            "meal_time IN ('breakfast','morning_snack','lunch','afternoon_snack',"
            "'dinner','night_snack')",
            name="ck_meal_plan_slot_time",
        ),
        sa.CheckConstraint(
            "fulfillment_status IN ('ordered','no_tray','not_applicable','hold')",
            name="ck_meal_plan_slot_fulfillment",
        ),
        sa.ForeignKeyConstraint(["meal_plan_id"], ["nutritional_meal_plans.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("meal_plan_id", "meal_time", name="uq_meal_plan_slot_time"),
    )
    op.create_index(
        "ix_nutritional_meal_plan_slots_meal_plan_id",
        "nutritional_meal_plan_slots",
        ["meal_plan_id"],
    )
    op.create_index(
        "ix_nutritional_meal_plan_slots_meal_time",
        "nutritional_meal_plan_slots",
        ["meal_time"],
    )
    op.create_index(
        "ix_nutritional_meal_plan_slots_is_special",
        "nutritional_meal_plan_slots",
        ["is_special"],
    )

    op.create_table(
        "nutritional_meal_plan_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("meal_plan_slot_id", sa.Uuid(), nullable=False),
        sa.Column("catalog_item_id", sa.Uuid(), nullable=True),
        sa.Column("custom_name", sa.String(500), nullable=True),
        sa.Column("quantity", sa.Numeric(12, 3), nullable=False),
        sa.Column("unit", sa.String(30), nullable=False),
        sa.Column("instructions", sa.String(2000), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "(catalog_item_id IS NOT NULL AND custom_name IS NULL) OR "
            "(catalog_item_id IS NULL AND custom_name IS NOT NULL)",
            name="ck_meal_plan_item_source",
        ),
        sa.CheckConstraint("quantity > 0", name="ck_meal_plan_item_quantity"),
        sa.ForeignKeyConstraint(
            ["meal_plan_slot_id"], ["nutritional_meal_plan_slots.id"]
        ),
        sa.ForeignKeyConstraint(
            ["catalog_item_id"], ["food_regimen_catalog_items.id"]
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_nutritional_meal_plan_items_meal_plan_slot_id",
        "nutritional_meal_plan_items",
        ["meal_plan_slot_id"],
    )
    op.create_index(
        "ix_nutritional_meal_plan_items_catalog_item_id",
        "nutritional_meal_plan_items",
        ["catalog_item_id"],
    )

    op.create_table(
        "nutritional_modular_preparations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("meal_plan_id", sa.Uuid(), nullable=False),
        sa.Column("preparation_type", sa.String(30), nullable=False),
        sa.Column("product_name", sa.String(300), nullable=False),
        sa.Column("powder_grams", sa.Numeric(12, 3), nullable=False),
        sa.Column("diluent", sa.String(100), nullable=False),
        sa.Column("dilution_volume_ml", sa.Numeric(12, 3), nullable=False),
        sa.Column("units_per_delivery", sa.Integer(), nullable=False),
        sa.Column("meal_time", sa.String(30), nullable=True),
        sa.Column("scheduled_time", sa.Time(), nullable=True),
        sa.Column("instructions", sa.String(2000), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "preparation_type IN ('protein_bolus','modular_preparation')",
            name="ck_modular_preparation_type",
        ),
        sa.CheckConstraint("powder_grams > 0", name="ck_modular_preparation_powder"),
        sa.CheckConstraint("dilution_volume_ml > 0", name="ck_modular_preparation_volume"),
        sa.CheckConstraint("units_per_delivery > 0", name="ck_modular_preparation_units"),
        sa.CheckConstraint(
            "meal_time IS NULL OR meal_time IN ('breakfast','morning_snack','lunch',"
            "'afternoon_snack','dinner','night_snack')",
            name="ck_modular_preparation_meal_time",
        ),
        sa.CheckConstraint(
            "meal_time IS NOT NULL OR scheduled_time IS NOT NULL",
            name="ck_modular_preparation_schedule",
        ),
        sa.ForeignKeyConstraint(["meal_plan_id"], ["nutritional_meal_plans.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_nutritional_modular_preparations_meal_plan_id",
        "nutritional_modular_preparations",
        ["meal_plan_id"],
    )
    op.create_index(
        "ix_nutritional_modular_preparations_meal_time",
        "nutritional_modular_preparations",
        ["meal_time"],
    )


def downgrade() -> None:
    op.drop_table("nutritional_modular_preparations")
    op.drop_table("nutritional_meal_plan_items")
    op.drop_table("nutritional_meal_plan_slots")
    op.drop_table("nutritional_meal_plans")
    op.drop_table("food_regimen_catalog_items")
