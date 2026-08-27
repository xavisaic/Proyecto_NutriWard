import os
import subprocess

from sqlalchemy import create_engine, inspect, text

from app.db.base import get_metadata


PHASE9_7_TABLES = {
    "admission_treatments",
    "admission_treatment_versions",
    "admission_treatment_reviews",
    "medication_catalog_items",
}
PHASE9_8_TABLES = {
    "enteral_formula_catalog_items",
    "nutrition_prescription_settings",
    "nutrition_prescription_orders",
    "nutrition_prescription_order_meals",
    "nutrition_prescription_supplements",
    "nutrition_prescription_progressions",
    "nutrition_prescription_monitoring",
    "nutrition_prescription_electrolytes",
    "nutrition_prescription_non_nutritional_contributions",
    "nutrition_prescription_dispatches",
}


def run_alembic(database_url: str, *arguments: str) -> None:
    environment = os.environ.copy()
    environment["DATABASE_URL"] = database_url
    subprocess.run(
        ["alembic", *arguments],
        check=True,
        cwd=os.path.dirname(os.path.dirname(__file__)),
        env=environment,
        capture_output=True,
        text=True,
    )


def test_phase9_7_migration_upgrade_downgrade_and_reupgrade(tmp_path) -> None:
    database_path = tmp_path / "phase9-7-migration.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    engine = create_engine(database_url)
    metadata = get_metadata()
    previous_tables = [
        table for name, table in metadata.tables.items() if name not in PHASE9_7_TABLES | PHASE9_8_TABLES
    ]
    metadata.create_all(engine, tables=previous_tables)
    with engine.begin() as connection:
        connection.execute(
            text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)")
        )
        connection.execute(
            text("INSERT INTO alembic_version(version_num) VALUES ('20260817_0014')")
        )

    run_alembic(database_url, "upgrade", "head")
    inspector = inspect(engine)
    assert PHASE9_7_TABLES <= set(inspector.get_table_names())
    assert PHASE9_8_TABLES <= set(inspector.get_table_names())
    prescription_columns = {row["name"] for row in inspector.get_columns("nutrition_prescription_orders")}
    assert {
        "parenteral_enabled", "parenteral_gir_mg_kg_min", "non_nutritional_energy_kcal",
        "total_real_energy_kcal", "signature_content_hash", "signed_by_user_id",
    } <= prescription_columns
    dispatch_checks = {row["name"] for row in inspector.get_check_constraints("nutrition_prescription_dispatches")}
    assert {"ck_prescription_dispatch_target", "ck_prescription_dispatch_status"} <= dispatch_checks
    checks = {
        row["name"]
        for row in inspector.get_check_constraints("admission_treatment_versions")
    }
    assert {
        "ck_treatment_version_order_status",
        "ck_treatment_version_verification_status",
        "ck_treatment_version_energy_non_negative",
    } <= checks
    indexes = {
        row["name"] for row in inspector.get_indexes("admission_treatment_versions")
    }
    assert "ix_treatment_versions_treatment_version" in indexes
    foreign_keys = inspector.get_foreign_keys("admission_treatment_versions")
    assert any(row["referred_table"] == "admission_treatments" for row in foreign_keys)

    run_alembic(database_url, "downgrade", "20260817_0014")
    assert not ((PHASE9_7_TABLES | PHASE9_8_TABLES) & set(inspect(engine).get_table_names()))
    run_alembic(database_url, "upgrade", "head")
    assert PHASE9_7_TABLES <= set(inspect(engine).get_table_names())
    assert PHASE9_8_TABLES <= set(inspect(engine).get_table_names())


def test_single_alembic_head_is_phase9_7() -> None:
    result = subprocess.run(
        ["alembic", "heads"],
        check=True,
        cwd=os.path.dirname(os.path.dirname(__file__)),
        capture_output=True,
        text=True,
    )
    heads = [line for line in result.stdout.splitlines() if line.strip()]
    assert len(heads) == 1
    assert "20260826_0018" in heads[0]
