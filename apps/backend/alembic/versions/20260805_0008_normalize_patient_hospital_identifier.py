"""Normalize patient hospital identifiers to uppercase.

Revision ID: 20260805_0008
Revises: 20260805_0007
Create Date: 2026-08-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op

revision: str = "20260805_0008"
down_revision: str | None = "20260805_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if not context.is_offline_mode():
        duplicates = op.get_bind().execute(
            sa.text(
                """
                SELECT upper(hospital_identifier)
                FROM patients
                WHERE hospital_identifier IS NOT NULL
                GROUP BY upper(hospital_identifier)
                HAVING COUNT(*) > 1
                ORDER BY upper(hospital_identifier)
                """
            )
        ).scalars().all()
        if duplicates:
            preview = ", ".join(str(value) for value in duplicates[:5])
            raise RuntimeError(
                "No se pueden normalizar los números de ficha porque existen duplicados "
                f"que sólo difieren por mayúsculas/minúsculas: {preview}"
            )

    op.execute(
        sa.text(
            "UPDATE patients SET hospital_identifier = upper(hospital_identifier) "
            "WHERE hospital_identifier IS NOT NULL"
        )
    )
    op.create_check_constraint(
        "ck_patients_hospital_identifier_uppercase",
        "patients",
        "hospital_identifier IS NULL OR hospital_identifier = upper(hospital_identifier)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_patients_hospital_identifier_uppercase",
        "patients",
        type_="check",
    )
