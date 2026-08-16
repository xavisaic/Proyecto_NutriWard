import os
import subprocess

from sqlalchemy import create_engine, inspect, text

from app.db.base import get_metadata

CLINICAL_TABLES = {
    "nutritional_care_encounters",
    "nutritional_assessments",
    "nutritional_clinical_context_items",
    "nutritional_anthropometric_measurements",
    "nutritional_screenings",
    "nutritional_screening_answers",
    "nutritional_requirement_calculations",
    "nutritional_diagnoses",
    "nutritional_prescriptions",
    "nutritional_prescription_meal_times",
    "nutritional_monitoring_records",
    "nutritional_intake_records",
    "nutritional_lab_observations",
    "nutritional_alerts",
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


def test_phase9_migration_upgrade_downgrade_and_constraints(tmp_path) -> None:
    database_path = tmp_path / "phase9-migration.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    engine = create_engine(database_url)
    metadata = get_metadata()
    previous_tables = [
        table for name, table in metadata.tables.items() if name not in CLINICAL_TABLES
    ]
    metadata.create_all(engine, tables=previous_tables)
    with engine.begin() as connection:
        connection.execute(
            text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)")
        )
        connection.execute(
            text("INSERT INTO alembic_version(version_num) VALUES ('20260812_0009')")
        )

    run_alembic(database_url, "upgrade", "20260813_0010")
    inspector = inspect(engine)
    assert CLINICAL_TABLES <= set(inspector.get_table_names())
    encounter_indexes = {row["name"] for row in inspector.get_indexes("nutritional_care_encounters")}
    assert "ix_nutrition_encounter_admission_datetime_status" in encounter_indexes
    intake_checks = {row["name"] for row in inspector.get_check_constraints("nutritional_intake_records")}
    assert "ck_nutrition_intake_percentage" in intake_checks

    run_alembic(database_url, "downgrade", "20260812_0009")
    assert not (CLINICAL_TABLES & set(inspect(engine).get_table_names()))
    run_alembic(database_url, "upgrade", "20260813_0010")
    assert CLINICAL_TABLES <= set(inspect(engine).get_table_names())


def test_single_alembic_head_continues_after_phase9() -> None:
    result = subprocess.run(
        ["alembic", "heads"],
        check=True,
        cwd=os.path.dirname(os.path.dirname(__file__)),
        capture_output=True,
        text=True,
    )
    heads = [line for line in result.stdout.splitlines() if line.strip()]
    assert len(heads) == 1
    assert "20260817_0014" in heads[0]
