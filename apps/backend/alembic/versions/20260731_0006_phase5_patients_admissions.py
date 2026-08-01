"""Create Phase 5 patients, admissions, and location history.

Revision ID: 20260731_0006
Revises: 20260728_0005
Create Date: 2026-07-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260731_0006"
down_revision: str | None = "20260728_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "patients",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("identity_status", sa.String(length=20), nullable=False),
        sa.Column("temporary_identifier", sa.String(length=40), nullable=True),
        sa.Column("rut", sa.String(length=12), nullable=True),
        sa.Column("given_names", sa.String(length=160), nullable=True),
        sa.Column("first_surname", sa.String(length=100), nullable=True),
        sa.Column("second_surname", sa.String(length=100), nullable=True),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("date_of_birth_is_estimated", sa.Boolean(), nullable=False),
        sa.Column("sex", sa.String(length=20), nullable=True),
        sa.Column("hospital_identifier", sa.String(length=80), nullable=True),
        sa.Column("phone", sa.String(length=40), nullable=True),
        sa.Column("provisional_description", sa.String(length=1000), nullable=True),
        sa.Column("identified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("identified_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("merged_into_patient_id", sa.Uuid(), nullable=True),
        sa.Column("merged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("merged_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("merge_reason", sa.String(length=500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=True),
        sa.CheckConstraint(
            "identity_status IN ('unidentified', 'provisional', 'identified')",
            name="ck_patients_identity_status",
        ),
        sa.CheckConstraint(
            "sex IS NULL OR sex IN ('female', 'male', 'intersex', 'unknown')",
            name="ck_patients_sex",
        ),
        sa.CheckConstraint(
            "(identity_status != 'identified') OR rut IS NOT NULL",
            name="ck_patients_identified_has_rut",
        ),
        sa.CheckConstraint(
            "(identity_status = 'identified') OR temporary_identifier IS NOT NULL",
            name="ck_patients_non_identified_has_temporary_identifier",
        ),
        sa.ForeignKeyConstraint(["identified_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["merged_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["merged_into_patient_id"], ["patients.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_patients_identity_status", "patients", ["identity_status"])
    op.create_index("ix_patients_temporary_identifier", "patients", ["temporary_identifier"], unique=True)
    op.create_index(
        "uq_patients_rut_not_null",
        "patients",
        ["rut"],
        unique=True,
        postgresql_where=sa.text("rut IS NOT NULL"),
    )
    op.create_index("ix_patients_given_names", "patients", ["given_names"])
    op.create_index("ix_patients_first_surname", "patients", ["first_surname"])
    op.create_index("ix_patients_hospital_identifier", "patients", ["hospital_identifier"])
    op.create_index("ix_patients_merged_into_patient_id", "patients", ["merged_into_patient_id"])
    op.create_index("ix_patients_is_active", "patients", ["is_active"])

    op.create_table(
        "admissions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("patient_id", sa.Uuid(), nullable=False),
        sa.Column("admission_identifier", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("admitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_reason", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=True),
        sa.CheckConstraint(
            "status IN ('active', 'discharged', 'deceased', 'closed')",
            name="ck_admissions_status",
        ),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_admissions_patient_id", "admissions", ["patient_id"])
    op.create_index(
        "ix_admissions_admission_identifier",
        "admissions",
        ["admission_identifier"],
        unique=True,
    )
    op.create_index("ix_admissions_status", "admissions", ["status"])
    op.create_index("ix_admissions_admitted_at", "admissions", ["admitted_at"])
    op.create_index(
        "uq_admissions_one_active_per_patient",
        "admissions",
        ["patient_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "admission_status_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("admission_id", sa.Uuid(), nullable=False),
        sa.Column("from_status", sa.String(length=20), nullable=True),
        sa.Column("to_status", sa.String(length=20), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("changed_by_user_id", sa.Uuid(), nullable=True),
        sa.CheckConstraint(
            "from_status IS NULL OR from_status IN ('active', 'discharged', 'deceased', 'closed')",
            name="ck_admission_status_history_from",
        ),
        sa.CheckConstraint(
            "to_status IN ('active', 'discharged', 'deceased', 'closed')",
            name="ck_admission_status_history_to",
        ),
        sa.ForeignKeyConstraint(["admission_id"], ["admissions.id"]),
        sa.ForeignKeyConstraint(["changed_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_admission_status_history_admission_id",
        "admission_status_history",
        ["admission_id"],
    )
    op.create_index(
        "ix_admission_status_history_changed_at",
        "admission_status_history",
        ["changed_at"],
    )

    op.create_table(
        "patient_location_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("admission_id", sa.Uuid(), nullable=False),
        sa.Column("care_unit_id", sa.Uuid(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("assigned_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("ended_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["admission_id"], ["admissions.id"]),
        sa.ForeignKeyConstraint(["care_unit_id"], ["care_units.id"]),
        sa.ForeignKeyConstraint(["assigned_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["ended_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_patient_location_history_admission_id",
        "patient_location_history",
        ["admission_id"],
    )
    op.create_index(
        "ix_patient_location_history_care_unit_id",
        "patient_location_history",
        ["care_unit_id"],
    )
    op.create_index(
        "ix_patient_location_history_started_at",
        "patient_location_history",
        ["started_at"],
    )
    op.create_index(
        "ix_patient_location_history_ended_at",
        "patient_location_history",
        ["ended_at"],
    )
    op.create_index(
        "uq_patient_location_one_current_per_admission",
        "patient_location_history",
        ["admission_id"],
        unique=True,
        postgresql_where=sa.text("ended_at IS NULL"),
    )
    op.create_index(
        "uq_patient_location_one_current_per_bed",
        "patient_location_history",
        ["care_unit_id"],
        unique=True,
        postgresql_where=sa.text("ended_at IS NULL"),
    )
    op.create_foreign_key(
        "fk_audit_logs_admission_id_admissions",
        "audit_logs",
        "admissions",
        ["admission_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_audit_logs_admission_id_admissions",
        "audit_logs",
        type_="foreignkey",
    )
    op.drop_table("patient_location_history")
    op.drop_table("admission_status_history")
    op.drop_table("admissions")
    op.drop_table("patients")
