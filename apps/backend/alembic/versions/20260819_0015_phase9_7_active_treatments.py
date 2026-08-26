"""Add versioned active treatments for Phase 9.7.

Revision ID: 20260819_0015
Revises: 20260817_0014
Create Date: 2026-08-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260819_0015"
down_revision: str | None = "20260817_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = sa.Uuid
TZ = lambda: sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "admission_treatments",
        sa.Column("id", UUID(), nullable=False),
        sa.Column("admission_id", UUID(), nullable=False),
        sa.Column("kind", sa.String(30), nullable=False),
        sa.Column("created_by_user_id", UUID(), nullable=False),
        sa.Column("created_at", TZ(), nullable=False),
        sa.CheckConstraint(
            "kind IN ('medication','nutritional_support')",
            name="ck_admission_treatment_kind",
        ),
        sa.ForeignKeyConstraint(["admission_id"], ["admissions.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_admission_treatments_admission_id", "admission_treatments", ["admission_id"])
    op.create_index("ix_admission_treatments_kind", "admission_treatments", ["kind"])
    op.create_index(
        "ix_admission_treatments_admission_created",
        "admission_treatments",
        ["admission_id", "created_at"],
    )

    op.create_table(
        "admission_treatment_versions",
        sa.Column("id", UUID(), nullable=False),
        sa.Column("treatment_id", UUID(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("previous_version_id", UUID(), nullable=True),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("category", sa.String(40), nullable=False),
        sa.Column("prescription_text", sa.String(2000), nullable=False),
        sa.Column("concentration_value", sa.Numeric(12, 4), nullable=True),
        sa.Column("concentration_unit", sa.String(40), nullable=True),
        sa.Column("diluent_volume_ml", sa.Numeric(12, 2), nullable=True),
        sa.Column("dose_value", sa.Numeric(12, 4), nullable=True),
        sa.Column("dose_unit", sa.String(40), nullable=True),
        sa.Column("route", sa.String(80), nullable=True),
        sa.Column("modality", sa.String(80), nullable=True),
        sa.Column("frequency", sa.String(160), nullable=True),
        sa.Column("rate_value", sa.Numeric(12, 4), nullable=True),
        sa.Column("rate_unit", sa.String(40), nullable=True),
        sa.Column("prescribed_energy_kcal_day", sa.Numeric(12, 2), nullable=True),
        sa.Column("starts_at", TZ(), nullable=True),
        sa.Column("planned_ends_at", TZ(), nullable=True),
        sa.Column("indication", sa.String(1000), nullable=True),
        sa.Column("order_status", sa.String(30), nullable=False),
        sa.Column("source_type", sa.String(80), nullable=False),
        sa.Column("source_reference", sa.String(500), nullable=True),
        sa.Column("observed_at", TZ(), nullable=False),
        sa.Column("verification_status", sa.String(20), nullable=False),
        sa.Column("verified_at", TZ(), nullable=True),
        sa.Column("verified_by_user_id", UUID(), nullable=True),
        sa.Column("nutritional_note", sa.String(2000), nullable=True),
        sa.Column("change_reason", sa.String(1000), nullable=False),
        sa.Column("created_by_user_id", UUID(), nullable=False),
        sa.Column("created_at", TZ(), nullable=False),
        sa.CheckConstraint("version > 0", name="ck_treatment_version_positive"),
        sa.CheckConstraint(
            "category IN ('nutritional_support','vasoactive','sedative_analgesic',"
            "'antimicrobial','corticosteroid','diuretic','insulin_glycemic',"
            "'gastrointestinal','anticoagulant','other')",
            name="ck_treatment_version_category",
        ),
        sa.CheckConstraint(
            "order_status IN ('draft','active','on_hold','ended','stopped','completed',"
            "'cancelled','entered_in_error','unknown')",
            name="ck_treatment_version_order_status",
        ),
        sa.CheckConstraint(
            "verification_status IN ('pending','verified','stale')",
            name="ck_treatment_version_verification_status",
        ),
        sa.CheckConstraint("dose_value IS NULL OR dose_value >= 0", name="ck_treatment_version_dose_non_negative"),
        sa.CheckConstraint("concentration_value IS NULL OR concentration_value >= 0", name="ck_treatment_version_concentration_non_negative"),
        sa.CheckConstraint("diluent_volume_ml IS NULL OR diluent_volume_ml >= 0", name="ck_treatment_version_diluent_non_negative"),
        sa.CheckConstraint("rate_value IS NULL OR rate_value >= 0", name="ck_treatment_version_rate_non_negative"),
        sa.CheckConstraint("prescribed_energy_kcal_day IS NULL OR prescribed_energy_kcal_day >= 0", name="ck_treatment_version_energy_non_negative"),
        sa.ForeignKeyConstraint(["treatment_id"], ["admission_treatments.id"]),
        sa.ForeignKeyConstraint(["previous_version_id"], ["admission_treatment_versions.id"]),
        sa.ForeignKeyConstraint(["verified_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("treatment_id", "version", name="uq_treatment_version_number"),
    )
    for column in ("treatment_id", "name", "category", "order_status", "verification_status", "starts_at", "observed_at"):
        op.create_index(
            f"ix_admission_treatment_versions_{column}",
            "admission_treatment_versions",
            [column],
        )
    op.create_index(
        "ix_treatment_versions_treatment_version",
        "admission_treatment_versions",
        ["treatment_id", "version"],
    )
    op.create_index(
        "ix_treatment_versions_status",
        "admission_treatment_versions",
        ["order_status", "verification_status"],
    )

    op.create_table(
        "admission_treatment_reviews",
        sa.Column("id", UUID(), nullable=False),
        sa.Column("admission_id", UUID(), nullable=False),
        sa.Column("assertion", sa.String(40), nullable=False),
        sa.Column("source_type", sa.String(80), nullable=False),
        sa.Column("note", sa.String(1000), nullable=True),
        sa.Column("recorded_by_user_id", UUID(), nullable=False),
        sa.Column("recorded_at", TZ(), nullable=False),
        sa.CheckConstraint(
            "assertion IN ('reviewed_with_findings','no_known','information_unavailable')",
            name="ck_admission_treatment_review_assertion",
        ),
        sa.ForeignKeyConstraint(["admission_id"], ["admissions.id"]),
        sa.ForeignKeyConstraint(["recorded_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_admission_treatment_reviews_admission_id", "admission_treatment_reviews", ["admission_id"])
    op.create_index("ix_admission_treatment_reviews_assertion", "admission_treatment_reviews", ["assertion"])
    op.create_index(
        "ix_treatment_reviews_admission_recorded",
        "admission_treatment_reviews",
        ["admission_id", "recorded_at"],
    )


def downgrade() -> None:
    op.drop_table("admission_treatment_reviews")
    op.drop_table("admission_treatment_versions")
    op.drop_table("admission_treatments")
