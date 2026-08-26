"""Add institutional medication catalog and infusion tracking.

Revision ID: 20260826_0016
Revises: 20260819_0015
Create Date: 2026-08-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260826_0016"
down_revision: str | None = "20260819_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "medication_catalog_items",
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("alternate_code", sa.String(40), nullable=True),
        sa.Column("display_name", sa.String(300), nullable=False),
        sa.Column("normalized_name", sa.String(400), nullable=False),
        sa.Column("route", sa.String(80), nullable=True),
        sa.Column("available_inpatient", sa.Boolean(), nullable=False),
        sa.Column("available_outpatient", sa.Boolean(), nullable=False),
        sa.Column("restriction", sa.String(1000), nullable=True),
        sa.Column("clinical_profile", sa.String(30), nullable=False),
        sa.Column("default_category", sa.String(40), nullable=False),
        sa.Column("source_version", sa.String(80), nullable=False),
        sa.Column("source_row", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            "clinical_profile IN ('standard','intravenous','continuous_infusion')",
            name="ck_medication_catalog_clinical_profile",
        ),
        sa.PrimaryKeyConstraint("code"),
    )
    for column in (
        "alternate_code",
        "display_name",
        "normalized_name",
        "clinical_profile",
        "source_version",
        "is_active",
    ):
        op.create_index(
            f"ix_medication_catalog_items_{column}",
            "medication_catalog_items",
            [column],
        )
    op.create_index(
        "ix_medication_catalog_search_active",
        "medication_catalog_items",
        ["normalized_name", "is_active"],
    )

    with op.batch_alter_table("admission_treatment_versions") as batch:
        batch.add_column(sa.Column("medication_catalog_code", sa.String(40), nullable=True))
        batch.add_column(sa.Column("raw_medication_text", sa.String(2000), nullable=True))
        batch.add_column(
            sa.Column("infusion_duration_hours", sa.Numeric(10, 2), nullable=True)
        )
        batch.add_column(
            sa.Column("administered_volume_ml", sa.Numeric(12, 2), nullable=True)
        )
        batch.create_foreign_key(
            "fk_treatment_version_medication_catalog",
            "medication_catalog_items",
            ["medication_catalog_code"],
            ["code"],
        )
        batch.create_check_constraint(
            "ck_treatment_version_infusion_duration_non_negative",
            "infusion_duration_hours IS NULL OR infusion_duration_hours >= 0",
        )
        batch.create_check_constraint(
            "ck_treatment_version_administered_volume_non_negative",
            "administered_volume_ml IS NULL OR administered_volume_ml >= 0",
        )
        batch.create_index(
            "ix_admission_treatment_versions_medication_catalog_code",
            ["medication_catalog_code"],
        )


def downgrade() -> None:
    with op.batch_alter_table("admission_treatment_versions") as batch:
        batch.drop_index("ix_admission_treatment_versions_medication_catalog_code")
        batch.drop_constraint(
            "ck_treatment_version_administered_volume_non_negative",
            type_="check",
        )
        batch.drop_constraint(
            "ck_treatment_version_infusion_duration_non_negative",
            type_="check",
        )
        batch.drop_constraint(
            "fk_treatment_version_medication_catalog",
            type_="foreignkey",
        )
        batch.drop_column("administered_volume_ml")
        batch.drop_column("infusion_duration_hours")
        batch.drop_column("raw_medication_text")
        batch.drop_column("medication_catalog_code")
    op.drop_table("medication_catalog_items")
