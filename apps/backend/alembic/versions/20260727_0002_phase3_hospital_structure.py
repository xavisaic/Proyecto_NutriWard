"""Create Phase 3 hospital structure tables.

Revision ID: 20260727_0002
Revises: 20260727_0001
Create Date: 2026-07-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260727_0002"
down_revision: str | None = "20260727_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "services",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=30), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_services_code", "services", ["code"], unique=True)
    op.create_index("ix_services_name", "services", ["name"], unique=True)
    op.create_index("ix_services_is_active", "services", ["is_active"])

    op.create_table(
        "rooms",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("service_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=30), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("floor", sa.String(length=50), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["service_id"], ["services.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("service_id", "code", name="uq_rooms_service_code"),
    )
    op.create_index("ix_rooms_service_id", "rooms", ["service_id"])
    op.create_index("ix_rooms_is_active", "rooms", ["is_active"])

    op.create_table(
        "beds",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("room_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=30), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["room_id"], ["rooms.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("room_id", "code", name="uq_beds_room_code"),
    )
    op.create_index("ix_beds_room_id", "beds", ["room_id"])
    op.create_index("ix_beds_is_active", "beds", ["is_active"])

    op.create_table(
        "bed_layout_positions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("bed_id", sa.Uuid(), nullable=False),
        sa.Column("grid_x", sa.Integer(), nullable=False),
        sa.Column("grid_y", sa.Integer(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("grid_x >= 0", name="ck_bed_layout_positions_grid_x"),
        sa.CheckConstraint("grid_y >= 0", name="ck_bed_layout_positions_grid_y"),
        sa.CheckConstraint("width > 0", name="ck_bed_layout_positions_width"),
        sa.CheckConstraint("height > 0", name="ck_bed_layout_positions_height"),
        sa.ForeignKeyConstraint(["bed_id"], ["beds.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_bed_layout_positions_bed_id",
        "bed_layout_positions",
        ["bed_id"],
        unique=True,
    )

    op.create_foreign_key(
        "fk_nutritionist_service_assignments_service_id_services",
        "nutritionist_service_assignments",
        "services",
        ["service_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_nutritionist_service_assignments_service_id_services",
        "nutritionist_service_assignments",
        type_="foreignkey",
    )
    op.drop_table("bed_layout_positions")
    op.drop_table("beds")
    op.drop_table("rooms")
    op.drop_table("services")
