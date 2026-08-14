"""Add longitudinal conditions and admission diagnoses for Phase 9.1.

Revision ID: 20260813_0011
Revises: 20260813_0010
Create Date: 2026-08-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260813_0011"
down_revision: str | None = "20260813_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = sa.Uuid
TZ = lambda: sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "patient_conditions",
        sa.Column("id", UUID(), nullable=False),
        sa.Column("patient_id", UUID(), nullable=False),
        sa.Column("condition_name", sa.String(500), nullable=False),
        sa.Column("code_system", sa.String(50), nullable=True),
        sa.Column("code", sa.String(50), nullable=True),
        sa.Column("clinical_status", sa.String(30), nullable=False),
        sa.Column("verification_status", sa.String(30), nullable=False),
        sa.Column("onset_date", sa.Date(), nullable=True),
        sa.Column("resolved_on", sa.Date(), nullable=True),
        sa.Column("source", sa.String(80), nullable=False),
        sa.Column("note", sa.String(2000), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_by_user_id", UUID(), nullable=False),
        sa.Column("updated_by_user_id", UUID(), nullable=False),
        sa.Column("created_at", TZ(), nullable=False),
        sa.Column("updated_at", TZ(), nullable=False),
        sa.CheckConstraint("clinical_status IN ('active','inactive','remission','resolved','entered_in_error')", name="ck_patient_condition_clinical_status"),
        sa.CheckConstraint("verification_status IN ('unconfirmed','confirmed','refuted')", name="ck_patient_condition_verification_status"),
        sa.CheckConstraint("version > 0", name="ck_patient_condition_version_positive"),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("patient_id", "condition_name", "code", "clinical_status", "verification_status"):
        op.create_index(f"ix_patient_conditions_{column}", "patient_conditions", [column])
    op.create_index("ix_patient_condition_patient_status", "patient_conditions", ["patient_id", "clinical_status"])

    op.create_table(
        "patient_condition_status_history",
        sa.Column("id", UUID(), nullable=False),
        sa.Column("patient_condition_id", UUID(), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("from_clinical_status", sa.String(30), nullable=True),
        sa.Column("to_clinical_status", sa.String(30), nullable=False),
        sa.Column("from_verification_status", sa.String(30), nullable=True),
        sa.Column("to_verification_status", sa.String(30), nullable=False),
        sa.Column("reason", sa.String(1000), nullable=False),
        sa.Column("source", sa.String(80), nullable=False),
        sa.Column("changed_by_user_id", UUID(), nullable=False),
        sa.Column("changed_at", TZ(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.CheckConstraint("sequence_number > 0", name="ck_patient_condition_history_sequence"),
        sa.ForeignKeyConstraint(["patient_condition_id"], ["patient_conditions.id"]),
        sa.ForeignKeyConstraint(["changed_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("patient_condition_id", "sequence_number", name="uq_patient_condition_history_sequence"),
    )
    op.create_index("ix_patient_condition_status_history_patient_condition_id", "patient_condition_status_history", ["patient_condition_id"])
    op.create_index("ix_patient_condition_status_history_changed_at", "patient_condition_status_history", ["changed_at"])

    op.create_table(
        "admission_diagnoses",
        sa.Column("id", UUID(), nullable=False),
        sa.Column("admission_id", UUID(), nullable=False),
        sa.Column("diagnosis_name", sa.String(500), nullable=False),
        sa.Column("code_system", sa.String(50), nullable=True),
        sa.Column("code", sa.String(50), nullable=True),
        sa.Column("diagnosis_type", sa.String(30), nullable=False),
        sa.Column("clinical_status", sa.String(30), nullable=False),
        sa.Column("verification_status", sa.String(30), nullable=False),
        sa.Column("present_on_admission", sa.Boolean(), nullable=False),
        sa.Column("diagnosed_at", TZ(), nullable=False),
        sa.Column("resolved_at", TZ(), nullable=True),
        sa.Column("source", sa.String(80), nullable=False),
        sa.Column("note", sa.String(2000), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_by_user_id", UUID(), nullable=False),
        sa.Column("updated_by_user_id", UUID(), nullable=False),
        sa.Column("created_at", TZ(), nullable=False),
        sa.Column("updated_at", TZ(), nullable=False),
        sa.CheckConstraint("diagnosis_type IN ('principal','secondary','complication')", name="ck_admission_diagnosis_type"),
        sa.CheckConstraint("clinical_status IN ('active','resolved','entered_in_error')", name="ck_admission_diagnosis_clinical_status"),
        sa.CheckConstraint("verification_status IN ('provisional','confirmed','ruled_out')", name="ck_admission_diagnosis_verification_status"),
        sa.CheckConstraint("version > 0", name="ck_admission_diagnosis_version_positive"),
        sa.ForeignKeyConstraint(["admission_id"], ["admissions.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("admission_id", "diagnosis_name", "code", "diagnosis_type", "clinical_status", "verification_status", "diagnosed_at"):
        op.create_index(f"ix_admission_diagnoses_{column}", "admission_diagnoses", [column])
    op.create_index("ix_admission_diagnosis_admission_status", "admission_diagnoses", ["admission_id", "clinical_status"])

    op.create_table(
        "admission_diagnosis_status_history",
        sa.Column("id", UUID(), nullable=False),
        sa.Column("admission_diagnosis_id", UUID(), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("from_clinical_status", sa.String(30), nullable=True),
        sa.Column("to_clinical_status", sa.String(30), nullable=False),
        sa.Column("from_verification_status", sa.String(30), nullable=True),
        sa.Column("to_verification_status", sa.String(30), nullable=False),
        sa.Column("reason", sa.String(1000), nullable=False),
        sa.Column("source", sa.String(80), nullable=False),
        sa.Column("changed_by_user_id", UUID(), nullable=False),
        sa.Column("changed_at", TZ(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.CheckConstraint("sequence_number > 0", name="ck_admission_diagnosis_history_sequence"),
        sa.ForeignKeyConstraint(["admission_diagnosis_id"], ["admission_diagnoses.id"]),
        sa.ForeignKeyConstraint(["changed_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("admission_diagnosis_id", "sequence_number", name="uq_admission_diagnosis_history_sequence"),
    )
    op.create_index("ix_admission_diagnosis_status_history_admission_diagnosis_id", "admission_diagnosis_status_history", ["admission_diagnosis_id"])
    op.create_index("ix_admission_diagnosis_status_history_changed_at", "admission_diagnosis_status_history", ["changed_at"])


def downgrade() -> None:
    op.drop_table("admission_diagnosis_status_history")
    op.drop_table("admission_diagnoses")
    op.drop_table("patient_condition_status_history")
    op.drop_table("patient_conditions")
