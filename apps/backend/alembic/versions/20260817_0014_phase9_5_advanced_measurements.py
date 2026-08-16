"""Add advanced anthropometry and body-composition sessions for Phase 9.5.

Revision ID: 20260817_0014
Revises: 20260816_0013
Create Date: 2026-08-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260817_0014"
down_revision: str | None = "20260816_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = sa.Uuid
TZ = lambda: sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "nutritional_measurement_sessions",
        sa.Column("id", UUID(), nullable=False),
        sa.Column("admission_id", UUID(), nullable=False),
        sa.Column("encounter_id", UUID(), nullable=False),
        sa.Column("session_type", sa.String(30), nullable=False),
        sa.Column("measured_at", TZ(), nullable=False),
        sa.Column("protocol_code", sa.String(80), nullable=False),
        sa.Column("protocol_version", sa.String(40), nullable=False),
        sa.Column("algorithm_version", sa.String(100), nullable=True),
        sa.Column("device_manufacturer", sa.String(120), nullable=True),
        sa.Column("device_model", sa.String(120), nullable=True),
        sa.Column("device_serial", sa.String(120), nullable=True),
        sa.Column("technology", sa.String(80), nullable=True),
        sa.Column("frequencies_khz", sa.String(200), nullable=True),
        sa.Column("position", sa.String(80), nullable=True),
        sa.Column("source", sa.String(80), nullable=True),
        sa.Column("reliability", sa.String(20), nullable=False),
        sa.Column("preparation_status", sa.String(20), nullable=True),
        sa.Column("fasting_hours", sa.Numeric(6, 2), nullable=True),
        sa.Column("recent_exercise", sa.Boolean(), nullable=True),
        sa.Column("bladder_emptied", sa.Boolean(), nullable=True),
        sa.Column("hydration_status", sa.String(20), nullable=True),
        sa.Column("edema_present", sa.Boolean(), nullable=True),
        sa.Column("observations", sa.String(3000), nullable=True),
        sa.Column("author_professional_id", UUID(), nullable=False),
        sa.Column("created_at", TZ(), nullable=False),
        sa.CheckConstraint(
            "session_type IN ('circumference','handgrip','skinfold_4','bioimpedance')",
            name="ck_nutrition_measurement_session_type",
        ),
        sa.CheckConstraint(
            "reliability IN ('high','medium','low','unknown')",
            name="ck_nutrition_measurement_session_reliability",
        ),
        sa.CheckConstraint(
            "preparation_status IS NULL OR preparation_status IN "
            "('standard','nonstandard','unknown')",
            name="ck_nutrition_measurement_preparation_status",
        ),
        sa.CheckConstraint(
            "hydration_status IS NULL OR hydration_status IN "
            "('usual','altered','unknown')",
            name="ck_nutrition_measurement_hydration_status",
        ),
        sa.ForeignKeyConstraint(["admission_id"], ["admissions.id"]),
        sa.ForeignKeyConstraint(["encounter_id"], ["nutritional_care_encounters.id"]),
        sa.ForeignKeyConstraint(["author_professional_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("admission_id", "encounter_id", "session_type", "measured_at"):
        op.create_index(
            f"ix_nutritional_measurement_sessions_{column}",
            "nutritional_measurement_sessions",
            [column],
        )
    op.create_index(
        "ix_nutrition_measurement_session_encounter_type",
        "nutritional_measurement_sessions",
        ["encounter_id", "session_type"],
    )

    op.create_table(
        "nutritional_measurement_values",
        sa.Column("id", UUID(), nullable=False),
        sa.Column("session_id", UUID(), nullable=False),
        sa.Column("measurement_code", sa.String(80), nullable=False),
        sa.Column("body_site", sa.String(80), nullable=True),
        sa.Column("laterality", sa.String(20), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=True),
        sa.Column("value", sa.Numeric(12, 4), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False),
        sa.Column("value_nature", sa.String(30), nullable=False),
        sa.Column("observations", sa.String(1000), nullable=True),
        sa.Column("created_at", TZ(), nullable=False),
        sa.CheckConstraint(
            "value >= 0", name="ck_nutrition_measurement_value_non_negative"
        ),
        sa.CheckConstraint(
            "laterality IN ('none','left','right','bilateral')",
            name="ck_nutrition_measurement_value_laterality",
        ),
        sa.CheckConstraint(
            "value_nature IN ('measured','calculated','device_reported')",
            name="ck_nutrition_measurement_value_nature",
        ),
        sa.CheckConstraint(
            "attempt_number IS NULL OR attempt_number BETWEEN 1 AND 3",
            name="ck_nutrition_measurement_value_attempt",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"], ["nutritional_measurement_sessions.id"]
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("session_id", "measurement_code"):
        op.create_index(
            f"ix_nutritional_measurement_values_{column}",
            "nutritional_measurement_values",
            [column],
        )
    op.create_index(
        "ix_nutrition_measurement_value_session_code",
        "nutritional_measurement_values",
        ["session_id", "measurement_code"],
    )


def downgrade() -> None:
    op.drop_table("nutritional_measurement_values")
    op.drop_table("nutritional_measurement_sessions")
