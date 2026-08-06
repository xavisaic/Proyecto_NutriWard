"""Require unique non-null patient hospital identifiers.

Revision ID: 20260805_0007
Revises: 20260731_0006
Create Date: 2026-08-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op

revision: str = "20260805_0007"
down_revision: str | None = "20260731_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if not context.is_offline_mode():
        connection = op.get_bind()
        duplicates = connection.execute(
            sa.text(
                """
                SELECT hospital_identifier
                FROM patients
                WHERE hospital_identifier IS NOT NULL
                GROUP BY hospital_identifier
                HAVING COUNT(*) > 1
                ORDER BY hospital_identifier
                """
            )
        ).scalars().all()
        if duplicates:
            preview = ", ".join(str(value) for value in duplicates[:5])
            raise RuntimeError(
                "No se puede aplicar la unicidad: existen números de ficha duplicados: "
                f"{preview}"
            )

    op.drop_index("ix_patients_hospital_identifier", table_name="patients")
    op.create_index(
        "uq_patients_hospital_identifier_not_null",
        "patients",
        ["hospital_identifier"],
        unique=True,
        postgresql_where=sa.text("hospital_identifier IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_patients_hospital_identifier_not_null",
        table_name="patients",
    )
    op.create_index(
        "ix_patients_hospital_identifier",
        "patients",
        ["hospital_identifier"],
        unique=False,
    )
