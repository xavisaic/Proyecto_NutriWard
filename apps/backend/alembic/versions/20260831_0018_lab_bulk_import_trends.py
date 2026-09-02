"""Add laboratory catalog, bulk imports and numeric trends.

Revision ID: 20260831_0018
Revises: 20260829_0017
Create Date: 2026-08-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260831_0018"
down_revision: str | None = "20260829_0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    existing_tables = set(inspector.get_table_names())
    expected_tables = {
        "laboratory_test_catalog",
        "laboratory_test_aliases",
        "nutritional_lab_import_batches",
    }
    expected_columns = {
        "import_batch_id",
        "laboratory_test_id",
        "numeric_value",
        "comparator",
        "normalized_unit",
        "reference_low",
        "reference_high",
    }
    existing_lab_columns = {
        column["name"]
        for column in inspector.get_columns("nutritional_lab_observations")
    }
    # Migration tests construct current metadata while stamping an older revision.
    # In that valid bootstrap scenario the target schema is already present.
    if expected_tables <= existing_tables and expected_columns <= existing_lab_columns:
        return

    op.create_table(
        "laboratory_test_catalog",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("canonical_name", sa.String(200), nullable=False),
        sa.Column("normalized_name", sa.String(220), nullable=False),
        sa.Column("category", sa.String(80), nullable=True),
        sa.Column("default_unit", sa.String(40), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("normalized_name"),
    )
    op.create_index("ix_laboratory_test_catalog_canonical_name", "laboratory_test_catalog", ["canonical_name"])
    op.create_index("ix_laboratory_test_catalog_normalized_name", "laboratory_test_catalog", ["normalized_name"])

    op.create_table(
        "laboratory_test_aliases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("laboratory_test_id", sa.Uuid(), nullable=False),
        sa.Column("alias", sa.String(200), nullable=False),
        sa.Column("normalized_alias", sa.String(220), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["laboratory_test_id"], ["laboratory_test_catalog.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("normalized_alias"),
    )
    op.create_index("ix_laboratory_test_aliases_laboratory_test_id", "laboratory_test_aliases", ["laboratory_test_id"])
    op.create_index("ix_laboratory_test_aliases_normalized_alias", "laboratory_test_aliases", ["normalized_alias"])

    op.create_table(
        "nutritional_lab_import_batches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("admission_id", sa.Uuid(), nullable=False),
        sa.Column("encounter_id", sa.Uuid(), nullable=False),
        sa.Column("sampled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(80), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["admission_id"], ["admissions.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["encounter_id"], ["nutritional_care_encounters.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("encounter_id"),
    )
    for column in ("admission_id", "encounter_id", "sampled_at"):
        op.create_index(f"ix_nutritional_lab_import_batches_{column}", "nutritional_lab_import_batches", [column])

    with op.batch_alter_table("nutritional_lab_observations") as batch:
        batch.add_column(sa.Column("import_batch_id", sa.Uuid(), nullable=True))
        batch.add_column(sa.Column("laboratory_test_id", sa.Uuid(), nullable=True))
        batch.add_column(sa.Column("numeric_value", sa.Numeric(18, 6), nullable=True))
        batch.add_column(sa.Column("comparator", sa.String(2), nullable=True))
        batch.add_column(sa.Column("normalized_unit", sa.String(40), nullable=True))
        batch.add_column(sa.Column("reference_low", sa.Numeric(18, 6), nullable=True))
        batch.add_column(sa.Column("reference_high", sa.Numeric(18, 6), nullable=True))
        batch.create_foreign_key("fk_lab_observation_import_batch", "nutritional_lab_import_batches", ["import_batch_id"], ["id"])
        batch.create_foreign_key("fk_lab_observation_catalog_test", "laboratory_test_catalog", ["laboratory_test_id"], ["id"])
        batch.create_index("ix_nutritional_lab_observations_import_batch_id", ["import_batch_id"])
        batch.create_index("ix_nutritional_lab_observations_laboratory_test_id", ["laboratory_test_id"])


def downgrade() -> None:
    with op.batch_alter_table("nutritional_lab_observations") as batch:
        batch.drop_index("ix_nutritional_lab_observations_laboratory_test_id")
        batch.drop_index("ix_nutritional_lab_observations_import_batch_id")
        for column in ("reference_high", "reference_low", "normalized_unit", "comparator", "numeric_value", "laboratory_test_id", "import_batch_id"):
            batch.drop_column(column)
    for column in ("sampled_at", "encounter_id", "admission_id"):
        op.drop_index(f"ix_nutritional_lab_import_batches_{column}", table_name="nutritional_lab_import_batches")
    op.drop_table("nutritional_lab_import_batches")
    op.drop_index("ix_laboratory_test_aliases_normalized_alias", table_name="laboratory_test_aliases")
    op.drop_index("ix_laboratory_test_aliases_laboratory_test_id", table_name="laboratory_test_aliases")
    op.drop_table("laboratory_test_aliases")
    op.drop_index("ix_laboratory_test_catalog_normalized_name", table_name="laboratory_test_catalog")
    op.drop_index("ix_laboratory_test_catalog_canonical_name", table_name="laboratory_test_catalog")
    op.drop_table("laboratory_test_catalog")
