"""Complete Phase 4 role assignment lifecycle support.

Revision ID: 20260728_0005
Revises: 20260728_0004
Create Date: 2026-07-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260728_0005"
down_revision: str | None = "20260728_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user_roles",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "user_roles",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_user_roles_is_active", "user_roles", ["is_active"])
    op.create_index("ix_users_is_active", "users", ["is_active"])
    op.create_index(
        "ix_nutritionist_service_assignments_is_active",
        "nutritionist_service_assignments",
        ["is_active"],
    )
    op.alter_column("user_roles", "is_active", server_default=None)
    op.alter_column("user_roles", "updated_at", server_default=None)


def downgrade() -> None:
    op.drop_index(
        "ix_nutritionist_service_assignments_is_active",
        table_name="nutritionist_service_assignments",
    )
    op.drop_index("ix_users_is_active", table_name="users")
    op.drop_index("ix_user_roles_is_active", table_name="user_roles")
    op.drop_column("user_roles", "updated_at")
    op.drop_column("user_roles", "is_active")
