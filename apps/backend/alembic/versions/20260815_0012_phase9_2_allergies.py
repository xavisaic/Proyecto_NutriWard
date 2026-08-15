"""Add allergy and intolerance records for Phase 9.2.

Revision ID: 20260815_0012
Revises: 20260813_0011
Create Date: 2026-08-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260815_0012"
down_revision: str | None = "20260813_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = sa.Uuid
TZ = lambda: sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "patient_allergy_intolerances",
        sa.Column("id", UUID(), nullable=False),
        sa.Column("patient_id", UUID(), nullable=False),
        sa.Column("asserted_admission_id", UUID(), nullable=True),
        sa.Column("substance_name", sa.String(500), nullable=False),
        sa.Column("code_system", sa.String(100), nullable=True),
        sa.Column("code", sa.String(100), nullable=True),
        sa.Column("allergy_type", sa.String(30), nullable=True),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("clinical_status", sa.String(30), nullable=True),
        sa.Column("verification_status", sa.String(30), nullable=False),
        sa.Column("criticality", sa.String(30), nullable=False),
        sa.Column("onset_date", sa.Date(), nullable=True),
        sa.Column("source", sa.String(80), nullable=False),
        sa.Column("note", sa.String(2000), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_by_user_id", UUID(), nullable=False),
        sa.Column("updated_by_user_id", UUID(), nullable=False),
        sa.Column("created_at", TZ(), nullable=False),
        sa.Column("updated_at", TZ(), nullable=False),
        sa.CheckConstraint("allergy_type IS NULL OR allergy_type IN ('allergy','intolerance')", name="ck_patient_allergy_type"),
        sa.CheckConstraint("category IN ('food','medication','environment','biologic','other')", name="ck_patient_allergy_category"),
        sa.CheckConstraint("clinical_status IS NULL OR clinical_status IN ('active','inactive','resolved')", name="ck_patient_allergy_clinical_status"),
        sa.CheckConstraint("verification_status IN ('unconfirmed','presumed','confirmed','refuted','entered_in_error')", name="ck_patient_allergy_verification_status"),
        sa.CheckConstraint("criticality IN ('low','high','unable_to_assess')", name="ck_patient_allergy_criticality"),
        sa.CheckConstraint("version > 0", name="ck_patient_allergy_version_positive"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.ForeignKeyConstraint(["asserted_admission_id"], ["admissions.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("patient_id", "asserted_admission_id", "substance_name", "code", "allergy_type", "category", "clinical_status", "verification_status", "criticality"):
        op.create_index(f"ix_patient_allergy_intolerances_{column}", "patient_allergy_intolerances", [column])
    op.create_index("ix_patient_allergy_patient_status", "patient_allergy_intolerances", ["patient_id", "clinical_status"])
    op.create_index("ix_patient_allergy_patient_category", "patient_allergy_intolerances", ["patient_id", "category"])

    op.create_table(
        "allergy_intolerance_reactions",
        sa.Column("id", UUID(), nullable=False),
        sa.Column("allergy_intolerance_id", UUID(), nullable=False),
        sa.Column("manifestation", sa.String(500), nullable=False),
        sa.Column("severity", sa.String(20), nullable=True),
        sa.Column("occurred_at", TZ(), nullable=True),
        sa.Column("exposure_route", sa.String(100), nullable=True),
        sa.Column("note", sa.String(1000), nullable=True),
        sa.Column("created_by_user_id", UUID(), nullable=False),
        sa.Column("created_at", TZ(), nullable=False),
        sa.CheckConstraint("severity IS NULL OR severity IN ('mild','moderate','severe')", name="ck_allergy_reaction_severity"),
        sa.ForeignKeyConstraint(["allergy_intolerance_id"], ["patient_allergy_intolerances.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("allergy_intolerance_id", "manifestation", "severity", "occurred_at"):
        op.create_index(f"ix_allergy_intolerance_reactions_{column}", "allergy_intolerance_reactions", [column])

    op.create_table(
        "allergy_intolerance_status_history",
        sa.Column("id", UUID(), nullable=False),
        sa.Column("allergy_intolerance_id", UUID(), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("from_clinical_status", sa.String(30), nullable=True),
        sa.Column("to_clinical_status", sa.String(30), nullable=True),
        sa.Column("from_verification_status", sa.String(30), nullable=True),
        sa.Column("to_verification_status", sa.String(30), nullable=False),
        sa.Column("from_criticality", sa.String(30), nullable=True),
        sa.Column("to_criticality", sa.String(30), nullable=False),
        sa.Column("reason", sa.String(1000), nullable=False),
        sa.Column("source", sa.String(80), nullable=False),
        sa.Column("changed_by_user_id", UUID(), nullable=False),
        sa.Column("changed_at", TZ(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.CheckConstraint("sequence_number > 0", name="ck_allergy_status_history_sequence"),
        sa.ForeignKeyConstraint(["allergy_intolerance_id"], ["patient_allergy_intolerances.id"]),
        sa.ForeignKeyConstraint(["changed_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("allergy_intolerance_id", "sequence_number", name="uq_allergy_status_history_sequence"),
    )
    op.create_index("ix_allergy_intolerance_status_history_allergy_intolerance_id", "allergy_intolerance_status_history", ["allergy_intolerance_id"])
    op.create_index("ix_allergy_intolerance_status_history_changed_at", "allergy_intolerance_status_history", ["changed_at"])

    op.create_table(
        "patient_allergy_review_assertions",
        sa.Column("id", UUID(), nullable=False),
        sa.Column("patient_id", UUID(), nullable=False),
        sa.Column("admission_id", UUID(), nullable=False),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("assertion", sa.String(40), nullable=False),
        sa.Column("source", sa.String(80), nullable=False),
        sa.Column("note", sa.String(1000), nullable=True),
        sa.Column("recorded_by_user_id", UUID(), nullable=False),
        sa.Column("recorded_at", TZ(), nullable=False),
        sa.CheckConstraint("category IN ('all','food','medication','environment','biologic','other')", name="ck_allergy_review_category"),
        sa.CheckConstraint("assertion IN ('not_asked','information_unavailable','no_known','reviewed_with_findings')", name="ck_allergy_review_assertion"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.ForeignKeyConstraint(["admission_id"], ["admissions.id"]),
        sa.ForeignKeyConstraint(["recorded_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("patient_id", "admission_id", "category", "assertion", "recorded_at"):
        op.create_index(f"ix_patient_allergy_review_assertions_{column}", "patient_allergy_review_assertions", [column])
    op.create_index("ix_allergy_review_patient_admission_category", "patient_allergy_review_assertions", ["patient_id", "admission_id", "category"])


def downgrade() -> None:
    op.drop_table("patient_allergy_review_assertions")
    op.drop_table("allergy_intolerance_status_history")
    op.drop_table("allergy_intolerance_reactions")
    op.drop_table("patient_allergy_intolerances")
