"""Generalize beds into typed care units.

Revision ID: 20260728_0003
Revises: 20260727_0002
Create Date: 2026-07-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260728_0003"
down_revision: str | None = "20260727_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.rename_table("beds", "care_units")
    op.execute(
        "ALTER TABLE care_units "
        "RENAME CONSTRAINT beds_room_id_fkey "
        "TO care_units_room_id_fkey"
    )
    op.drop_index("ix_beds_room_id", table_name="care_units")
    op.drop_index("ix_beds_is_active", table_name="care_units")
    op.drop_constraint("uq_beds_room_code", "care_units", type_="unique")
    op.create_index("ix_care_units_room_id", "care_units", ["room_id"])
    op.create_index("ix_care_units_is_active", "care_units", ["is_active"])
    op.create_unique_constraint(
        "uq_care_units_room_code",
        "care_units",
        ["room_id", "code"],
    )
    op.add_column(
        "care_units",
        sa.Column(
            "unit_type",
            sa.String(length=20),
            nullable=False,
            server_default="bed",
        ),
    )
    op.create_check_constraint(
        "ck_care_units_unit_type",
        "care_units",
        "unit_type IN ('bed', 'stretcher', 'station', 'box')",
    )
    op.create_index("ix_care_units_unit_type", "care_units", ["unit_type"])
    op.alter_column("care_units", "unit_type", server_default=None)

    op.rename_table("bed_layout_positions", "care_unit_layout_positions")
    op.drop_index(
        "ix_bed_layout_positions_bed_id",
        table_name="care_unit_layout_positions",
    )
    op.alter_column(
        "care_unit_layout_positions",
        "bed_id",
        new_column_name="care_unit_id",
        existing_type=sa.Uuid(),
        existing_nullable=False,
    )
    op.execute(
        "ALTER TABLE care_unit_layout_positions "
        "RENAME CONSTRAINT bed_layout_positions_bed_id_fkey "
        "TO care_unit_layout_positions_care_unit_id_fkey"
    )
    for suffix in ("grid_x", "grid_y", "width", "height"):
        op.execute(
            "ALTER TABLE care_unit_layout_positions "
            f"RENAME CONSTRAINT ck_bed_layout_positions_{suffix} "
            f"TO ck_care_unit_layout_positions_{suffix}"
        )
    op.create_index(
        "ix_care_unit_layout_positions_care_unit_id",
        "care_unit_layout_positions",
        ["care_unit_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_care_unit_layout_positions_care_unit_id",
        table_name="care_unit_layout_positions",
    )
    for suffix in ("grid_x", "grid_y", "width", "height"):
        op.execute(
            "ALTER TABLE care_unit_layout_positions "
            f"RENAME CONSTRAINT ck_care_unit_layout_positions_{suffix} "
            f"TO ck_bed_layout_positions_{suffix}"
        )
    op.execute(
        "ALTER TABLE care_unit_layout_positions "
        "RENAME CONSTRAINT care_unit_layout_positions_care_unit_id_fkey "
        "TO bed_layout_positions_bed_id_fkey"
    )
    op.alter_column(
        "care_unit_layout_positions",
        "care_unit_id",
        new_column_name="bed_id",
        existing_type=sa.Uuid(),
        existing_nullable=False,
    )
    op.create_index(
        "ix_bed_layout_positions_bed_id",
        "care_unit_layout_positions",
        ["bed_id"],
        unique=True,
    )
    op.rename_table("care_unit_layout_positions", "bed_layout_positions")

    op.drop_index("ix_care_units_unit_type", table_name="care_units")
    op.drop_constraint("ck_care_units_unit_type", "care_units", type_="check")
    op.drop_column("care_units", "unit_type")
    op.drop_constraint("uq_care_units_room_code", "care_units", type_="unique")
    op.drop_index("ix_care_units_is_active", table_name="care_units")
    op.drop_index("ix_care_units_room_id", table_name="care_units")
    op.create_unique_constraint(
        "uq_beds_room_code",
        "care_units",
        ["room_id", "code"],
    )
    op.create_index("ix_beds_is_active", "care_units", ["is_active"])
    op.create_index("ix_beds_room_id", "care_units", ["room_id"])
    op.execute(
        "ALTER TABLE care_units "
        "RENAME CONSTRAINT care_units_room_id_fkey "
        "TO beds_room_id_fkey"
    )
    op.rename_table("care_units", "beds")
