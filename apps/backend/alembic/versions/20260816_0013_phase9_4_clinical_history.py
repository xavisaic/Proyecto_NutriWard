"""Add versioned admission clinical history for Phase 9.4.

Revision ID: 20260816_0013
Revises: 20260815_0012
Create Date: 2026-08-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260816_0013"
down_revision: str | None = "20260815_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = sa.Uuid
TZ = lambda: sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "admission_clinical_history_versions",
        sa.Column("id", UUID(), nullable=False),
        sa.Column("admission_id", UUID(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("narrative", sa.String(10000), nullable=False),
        sa.Column("event_start_date", sa.Date(), nullable=True),
        sa.Column("source", sa.String(80), nullable=False),
        sa.Column("change_reason", sa.String(1000), nullable=True),
        sa.Column("recorded_by_user_id", UUID(), nullable=False),
        sa.Column("recorded_at", TZ(), nullable=False),
        sa.CheckConstraint(
            "source IN ('trakcare_manual','clinical_record','care_team','patient',"
            "'family_or_caregiver','combined','other')",
            name="ck_admission_clinical_history_source",
        ),
        sa.CheckConstraint(
            "version > 0", name="ck_admission_clinical_history_version_positive"
        ),
        sa.ForeignKeyConstraint(["admission_id"], ["admissions.id"]),
        sa.ForeignKeyConstraint(["recorded_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "admission_id", "version", name="uq_admission_clinical_history_version"
        ),
    )
    op.create_index(
        "ix_admission_clinical_history_versions_admission_id",
        "admission_clinical_history_versions",
        ["admission_id"],
    )
    op.create_index(
        "ix_admission_clinical_history_versions_recorded_at",
        "admission_clinical_history_versions",
        ["recorded_at"],
    )
    op.create_index(
        "ix_admission_clinical_history_admission_version",
        "admission_clinical_history_versions",
        ["admission_id", "version"],
    )


def downgrade() -> None:
    op.drop_table("admission_clinical_history_versions")
