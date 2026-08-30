import os
import subprocess

from sqlalchemy import create_engine, inspect, text

from app.db.base import get_metadata


PHASE9_5_TABLES = {
    "nutritional_measurement_sessions",
    "nutritional_measurement_values",
}
PHASE9_7_TABLES = {
    "admission_treatments",
    "admission_treatment_versions",
    "admission_treatment_reviews",
    "medication_catalog_items",
    "food_regimen_catalog_items",
    "nutritional_meal_plans",
    "nutritional_meal_plan_slots",
    "nutritional_meal_plan_items",
    "nutritional_modular_preparations",
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


def test_phase9_5_migration_upgrade_downgrade_and_reupgrade(tmp_path) -> None:
    database_path = tmp_path / "phase9-5-migration.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    engine = create_engine(database_url)
    metadata = get_metadata()
    previous_tables = [
        table
        for name, table in metadata.tables.items()
        if name not in PHASE9_5_TABLES | PHASE9_7_TABLES
    ]
    metadata.create_all(engine, tables=previous_tables)
    with engine.begin() as connection:
        connection.execute(
            text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)")
        )
        connection.execute(
            text("INSERT INTO alembic_version(version_num) VALUES ('20260816_0013')")
        )

    run_alembic(database_url, "upgrade", "head")
    inspector = inspect(engine)
    assert PHASE9_5_TABLES <= set(inspector.get_table_names())
    session_checks = {
        row["name"]
        for row in inspector.get_check_constraints("nutritional_measurement_sessions")
    }
    assert "ck_nutrition_measurement_session_type" in session_checks
    value_checks = {
        row["name"]
        for row in inspector.get_check_constraints("nutritional_measurement_values")
    }
    assert "ck_nutrition_measurement_value_nature" in value_checks
    indexes = {
        row["name"]
        for row in inspector.get_indexes("nutritional_measurement_values")
    }
    assert "ix_nutrition_measurement_value_session_code" in indexes
    foreign_keys = inspector.get_foreign_keys("nutritional_measurement_values")
    assert any(row["referred_table"] == "nutritional_measurement_sessions" for row in foreign_keys)

    run_alembic(database_url, "downgrade", "20260816_0013")
    assert not (PHASE9_5_TABLES & set(inspect(engine).get_table_names()))
    run_alembic(database_url, "upgrade", "head")
    assert PHASE9_5_TABLES <= set(inspect(engine).get_table_names())


def test_single_alembic_head_continues_after_phase9_5() -> None:
    result = subprocess.run(
        ["alembic", "heads"],
        check=True,
        cwd=os.path.dirname(os.path.dirname(__file__)),
        capture_output=True,
        text=True,
    )
    heads = [line for line in result.stdout.splitlines() if line.strip()]
    assert len(heads) == 1
    assert "20260829_0017" in heads[0]
