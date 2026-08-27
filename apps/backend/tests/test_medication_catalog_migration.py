import os
import subprocess

from sqlalchemy import create_engine, inspect, text

from app.db.base import get_metadata


PHASE9_7_AND_CATALOG_TABLES = {
    "admission_treatments",
    "admission_treatment_versions",
    "admission_treatment_reviews",
    "medication_catalog_items",
}
PHASE9_8_TABLES = {
    "enteral_formula_catalog_items", "nutrition_prescription_settings",
    "nutrition_prescription_orders", "nutrition_prescription_order_meals",
    "nutrition_prescription_supplements", "nutrition_prescription_progressions",
    "nutrition_prescription_monitoring",
    "nutrition_prescription_electrolytes", "nutrition_prescription_non_nutritional_contributions",
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


def test_medication_catalog_migration_upgrade_downgrade_and_reupgrade(tmp_path) -> None:
    database_path = tmp_path / "medication-catalog-migration.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    engine = create_engine(database_url)
    metadata = get_metadata()
    previous_tables = [
        table
        for name, table in metadata.tables.items()
        if name not in PHASE9_7_AND_CATALOG_TABLES | PHASE9_8_TABLES
    ]
    metadata.create_all(engine, tables=previous_tables)
    with engine.begin() as connection:
        connection.execute(
            text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)")
        )
        connection.execute(
            text("INSERT INTO alembic_version(version_num) VALUES ('20260817_0014')")
        )

    run_alembic(database_url, "upgrade", "20260819_0015")
    before = inspect(engine)
    assert "medication_catalog_items" not in before.get_table_names()
    assert "medication_catalog_code" not in {
        column["name"]
        for column in before.get_columns("admission_treatment_versions")
    }

    run_alembic(database_url, "upgrade", "head")
    inspector = inspect(engine)
    assert "medication_catalog_items" in inspector.get_table_names()
    assert {
        "medication_catalog_code",
        "raw_medication_text",
        "infusion_duration_hours",
        "administered_volume_ml",
    } <= {
        column["name"]
        for column in inspector.get_columns("admission_treatment_versions")
    }
    catalog_checks = {
        row["name"]
        for row in inspector.get_check_constraints("medication_catalog_items")
    }
    assert "ck_medication_catalog_clinical_profile" in catalog_checks
    version_checks = {
        row["name"]
        for row in inspector.get_check_constraints("admission_treatment_versions")
    }
    assert {
        "ck_treatment_version_infusion_duration_non_negative",
        "ck_treatment_version_administered_volume_non_negative",
    } <= version_checks

    run_alembic(database_url, "downgrade", "20260819_0015")
    downgraded = inspect(engine)
    assert "medication_catalog_items" not in downgraded.get_table_names()
    run_alembic(database_url, "upgrade", "head")
    assert "medication_catalog_items" in inspect(engine).get_table_names()


def test_single_alembic_head_is_medication_catalog() -> None:
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
