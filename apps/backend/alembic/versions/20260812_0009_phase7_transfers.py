"""Create Phase 7 transfer requests and deterministic status history.

Revision ID: 20260812_0009
Revises: 20260805_0008
Create Date: 2026-08-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260812_0009"
down_revision: str | None = "20260805_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "patient_transfer_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("admission_id", sa.Uuid(), nullable=False),
        sa.Column("origin_service_id", sa.Uuid(), nullable=False),
        sa.Column("destination_service_id", sa.Uuid(), nullable=False),
        sa.Column("origin_care_unit_id", sa.Uuid(), nullable=False),
        sa.Column("destination_care_unit_id", sa.Uuid(), nullable=True),
        sa.Column("transfer_mode", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("request_reason", sa.String(length=500), nullable=True),
        sa.Column("requested_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "origin_service_id != destination_service_id",
            name="ck_transfer_request_different_services",
        ),
        sa.CheckConstraint(
            "transfer_mode IN ('direct', 'reception_tray')",
            name="ck_transfer_request_mode",
        ),
        sa.CheckConstraint(
            "status IN ('requested', 'pending_reception', 'accepted', 'pending_bed', "
            "'assigned_to_bed', 'rejected', 'returned', 'cancelled')",
            name="ck_transfer_request_status",
        ),
        sa.CheckConstraint(
            "status != 'assigned_to_bed' OR destination_care_unit_id IS NOT NULL",
            name="ck_transfer_request_assigned_has_bed",
        ),
        sa.ForeignKeyConstraint(["admission_id"], ["admissions.id"]),
        sa.ForeignKeyConstraint(["origin_service_id"], ["services.id"]),
        sa.ForeignKeyConstraint(["destination_service_id"], ["services.id"]),
        sa.ForeignKeyConstraint(["origin_care_unit_id"], ["care_units.id"]),
        sa.ForeignKeyConstraint(["destination_care_unit_id"], ["care_units.id"]),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in (
        "admission_id", "origin_service_id", "destination_service_id", "origin_care_unit_id",
        "destination_care_unit_id", "transfer_mode", "status", "requested_at",
    ):
        op.create_index(f"ix_patient_transfer_requests_{column}", "patient_transfer_requests", [column])
    open_filter = sa.text(
        "status IN ('requested', 'pending_reception', 'accepted', 'pending_bed')"
    )
    op.create_index(
        "uq_transfer_request_one_open_per_admission",
        "patient_transfer_requests",
        ["admission_id"],
        unique=True,
        postgresql_where=open_filter,
        sqlite_where=open_filter,
    )

    op.create_table(
        "patient_transfer_request_status_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("transfer_request_id", sa.Uuid(), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("from_status", sa.String(length=30), nullable=True),
        sa.Column("to_status", sa.String(length=30), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("changed_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_coverage", sa.Boolean(), nullable=False),
        sa.CheckConstraint("sequence_number > 0", name="ck_transfer_status_history_sequence_positive"),
        sa.CheckConstraint(
            "from_status IS NULL OR from_status IN ('requested', 'pending_reception', 'accepted', "
            "'pending_bed', 'assigned_to_bed', 'rejected', 'returned', 'cancelled')",
            name="ck_transfer_status_history_from",
        ),
        sa.CheckConstraint(
            "to_status IN ('requested', 'pending_reception', 'accepted', 'pending_bed', "
            "'assigned_to_bed', 'rejected', 'returned', 'cancelled')",
            name="ck_transfer_status_history_to",
        ),
        sa.ForeignKeyConstraint(["transfer_request_id"], ["patient_transfer_requests.id"]),
        sa.ForeignKeyConstraint(["changed_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "transfer_request_id", "sequence_number", name="uq_transfer_status_history_sequence"
        ),
    )
    op.create_index(
        "ix_patient_transfer_request_status_history_transfer_request_id",
        "patient_transfer_request_status_history",
        ["transfer_request_id"],
    )
    op.create_index(
        "ix_patient_transfer_request_status_history_to_status",
        "patient_transfer_request_status_history",
        ["to_status"],
    )
    op.create_index(
        "ix_patient_transfer_request_status_history_changed_at",
        "patient_transfer_request_status_history",
        ["changed_at"],
    )


def downgrade() -> None:
    op.drop_table("patient_transfer_request_status_history")
    op.drop_table("patient_transfer_requests")
