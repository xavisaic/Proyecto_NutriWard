"""Add parenteral prescription, real contributions and dispatch outbox.

Revision ID: 20260826_0018
Revises: 20260826_0017
Create Date: 2026-08-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260826_0018"
down_revision: str | None = "20260826_0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("nutrition_prescription_settings") as batch:
        batch.add_column(sa.Column("peripheral_osmolarity_max_mosm_l", sa.Numeric(10, 2), nullable=False, server_default="900"))
        batch.add_column(sa.Column("gir_max_mg_kg_min", sa.Numeric(8, 2), nullable=False, server_default="5"))
        batch.add_column(sa.Column("lipid_max_g_kg_day", sa.Numeric(8, 2), nullable=False, server_default="2.5"))
        batch.add_column(sa.Column("amino_acid_kcal_per_g", sa.Numeric(8, 3), nullable=False, server_default="4"))
        batch.add_column(sa.Column("dextrose_kcal_per_g", sa.Numeric(8, 3), nullable=False, server_default="3.4"))
        batch.add_column(sa.Column("lipid_kcal_per_g", sa.Numeric(8, 3), nullable=False, server_default="10"))

    with op.batch_alter_table("nutrition_prescription_orders") as batch:
        batch.add_column(sa.Column("parenteral_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column("calculation_weight_kg", sa.Numeric(10, 3), nullable=True))
        batch.add_column(sa.Column("parenteral_access", sa.String(20), nullable=True))
        batch.add_column(sa.Column("parenteral_solution_type", sa.String(30), nullable=True))
        batch.add_column(sa.Column("parenteral_solution_name", sa.String(300), nullable=True))
        batch.add_column(sa.Column("parenteral_total_volume_ml", sa.Numeric(12, 2), nullable=False, server_default="0"))
        batch.add_column(sa.Column("parenteral_infusion_hours", sa.Numeric(8, 2), nullable=True))
        batch.add_column(sa.Column("parenteral_rate_ml_h", sa.Numeric(12, 2), nullable=False, server_default="0"))
        batch.add_column(sa.Column("amino_acids_g", sa.Numeric(12, 2), nullable=False, server_default="0"))
        batch.add_column(sa.Column("dextrose_g", sa.Numeric(12, 2), nullable=False, server_default="0"))
        batch.add_column(sa.Column("parenteral_lipid_g", sa.Numeric(12, 2), nullable=False, server_default="0"))
        batch.add_column(sa.Column("parenteral_gir_mg_kg_min", sa.Numeric(10, 3), nullable=True))
        batch.add_column(sa.Column("osmolarity_mosm_l", sa.Numeric(12, 2), nullable=True))
        batch.add_column(sa.Column("vitamins_instruction", sa.String(1000), nullable=True))
        batch.add_column(sa.Column("trace_elements_instruction", sa.String(1000), nullable=True))
        batch.add_column(sa.Column("insulin_units", sa.Numeric(10, 2), nullable=True))
        batch.add_column(sa.Column("parenteral_starts_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("planned_duration_days", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("refeeding_risk_confirmed", sa.Boolean(), nullable=False, server_default=sa.false()))
        for name in (
            "non_nutritional_energy_kcal", "non_nutritional_carbohydrate_g", "non_nutritional_lipid_g",
            "non_nutritional_fluid_ml", "total_real_energy_kcal", "total_real_protein_g",
            "total_real_carbohydrate_g", "total_real_lipid_g", "total_real_fluid_ml",
        ):
            batch.add_column(sa.Column(name, sa.Numeric(12, 2), nullable=False, server_default="0"))
        batch.add_column(sa.Column("signature_kind", sa.String(40), nullable=True))
        batch.add_column(sa.Column("signature_content_hash", sa.String(64), nullable=True))
        batch.add_column(sa.Column("signed_by_user_id", sa.Uuid(), nullable=True))
        batch.add_column(sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True))
        batch.create_foreign_key("fk_prescription_signed_by_user", "users", ["signed_by_user_id"], ["id"])

    op.execute(sa.text("""
        UPDATE nutrition_prescription_orders
        SET total_real_energy_kcal = prescribed_energy_kcal,
            total_real_protein_g = prescribed_protein_g,
            total_real_carbohydrate_g = prescribed_carbohydrate_g,
            total_real_lipid_g = prescribed_lipid_g,
            total_real_fluid_ml = prescribed_fluid_ml
    """))

    op.create_table(
        "nutrition_prescription_electrolytes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("electrolyte_code", sa.String(30), nullable=False),
        sa.Column("amount", sa.Numeric(12, 3), nullable=False),
        sa.Column("unit", sa.String(30), nullable=False),
        sa.Column("instruction", sa.String(500), nullable=True),
        sa.CheckConstraint("electrolyte_code IN ('sodium','potassium','calcium','magnesium','phosphate','chloride','acetate','other')", name="ck_prescription_electrolyte_code"),
        sa.ForeignKeyConstraint(["order_id"], ["nutrition_prescription_orders.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_nutrition_prescription_electrolytes_order_id", "nutrition_prescription_electrolytes", ["order_id"])

    op.create_table(
        "nutrition_prescription_non_nutritional_contributions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("source_type", sa.String(40), nullable=False),
        sa.Column("label", sa.String(300), nullable=False),
        sa.Column("source_treatment_id", sa.Uuid(), nullable=True),
        sa.Column("energy_kcal", sa.Numeric(12, 2), nullable=False),
        sa.Column("carbohydrate_g", sa.Numeric(12, 2), nullable=False),
        sa.Column("lipid_g", sa.Numeric(12, 2), nullable=False),
        sa.Column("fluid_ml", sa.Numeric(12, 2), nullable=False),
        sa.Column("data_origin", sa.String(40), nullable=False),
        sa.Column("verification_status", sa.String(30), nullable=False),
        sa.CheckConstraint("source_type IN ('propofol','dextrose_solution','citrate','medication_vehicle','flush_water','iv_fluid','other')", name="ck_non_nutritional_source_type"),
        sa.ForeignKeyConstraint(["order_id"], ["nutrition_prescription_orders.id"]),
        sa.ForeignKeyConstraint(["source_treatment_id"], ["admission_treatments.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_nutrition_prescription_non_nutritional_contributions_order_id", "nutrition_prescription_non_nutritional_contributions", ["order_id"])

    op.create_table(
        "nutrition_prescription_dispatches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("target", sa.String(30), nullable=False),
        sa.Column("channel", sa.String(40), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("note", sa.String(1000), nullable=True),
        sa.Column("external_reference", sa.String(200), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("target IN ('pharmacy','kitchen','nursing')", name="ck_prescription_dispatch_target"),
        sa.CheckConstraint("status IN ('queued','sent','acknowledged','failed','cancelled')", name="ck_prescription_dispatch_status"),
        sa.ForeignKeyConstraint(["order_id"], ["nutrition_prescription_orders.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_nutrition_prescription_dispatches_order_id", "nutrition_prescription_dispatches", ["order_id"])
    op.create_index("ix_nutrition_prescription_dispatches_target", "nutrition_prescription_dispatches", ["target"])
    op.create_index("ix_nutrition_prescription_dispatches_status", "nutrition_prescription_dispatches", ["status"])
    op.create_index("ix_prescription_dispatch_target_status", "nutrition_prescription_dispatches", ["target", "status"])


def downgrade() -> None:
    op.drop_table("nutrition_prescription_dispatches")
    op.drop_table("nutrition_prescription_non_nutritional_contributions")
    op.drop_table("nutrition_prescription_electrolytes")
    with op.batch_alter_table("nutrition_prescription_orders") as batch:
        batch.drop_constraint("fk_prescription_signed_by_user", type_="foreignkey")
        for name in (
            "signed_at", "signed_by_user_id", "signature_content_hash", "signature_kind",
            "total_real_fluid_ml", "total_real_lipid_g", "total_real_carbohydrate_g", "total_real_protein_g", "total_real_energy_kcal",
            "non_nutritional_fluid_ml", "non_nutritional_lipid_g", "non_nutritional_carbohydrate_g", "non_nutritional_energy_kcal",
            "refeeding_risk_confirmed", "planned_duration_days", "parenteral_starts_at", "insulin_units",
            "trace_elements_instruction", "vitamins_instruction", "osmolarity_mosm_l", "parenteral_gir_mg_kg_min",
            "parenteral_lipid_g", "dextrose_g", "amino_acids_g", "parenteral_rate_ml_h",
            "parenteral_infusion_hours", "parenteral_total_volume_ml", "parenteral_solution_name",
            "parenteral_solution_type", "parenteral_access", "calculation_weight_kg", "parenteral_enabled",
        ):
            batch.drop_column(name)
    with op.batch_alter_table("nutrition_prescription_settings") as batch:
        for name in (
            "lipid_kcal_per_g", "dextrose_kcal_per_g", "amino_acid_kcal_per_g",
            "lipid_max_g_kg_day", "gir_max_mg_kg_min", "peripheral_osmolarity_max_mosm_l",
        ):
            batch.drop_column(name)
