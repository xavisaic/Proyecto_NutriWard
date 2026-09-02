import os
import subprocess

from sqlalchemy import create_engine, inspect, text

from app.db.base import get_metadata


PHASE9_1_TABLES = {
    "patient_conditions",
    "patient_condition_status_history",
    "admission_diagnoses",
    "admission_diagnosis_status_history",
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


def test_phase9_1_migration_upgrade_downgrade_and_reupgrade(tmp_path) -> None:
    database_path = tmp_path / "phase9-1-migration.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    engine = create_engine(database_url)
    metadata = get_metadata()
    previous_tables = [
        table for name, table in metadata.tables.items() if name not in PHASE9_1_TABLES
    ]
    metadata.create_all(engine, tables=previous_tables)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)"))
        connection.execute(text("INSERT INTO alembic_version(version_num) VALUES ('20260813_0010')"))

    run_alembic(database_url, "upgrade", "20260813_0011")
    inspector = inspect(engine)
    assert PHASE9_1_TABLES <= set(inspector.get_table_names())
    diagnosis_checks = {row["name"] for row in inspector.get_check_constraints("admission_diagnoses")}
    assert "ck_admission_diagnosis_clinical_status" in diagnosis_checks
    history_uniques = {row["name"] for row in inspector.get_unique_constraints("admission_diagnosis_status_history")}
    assert "uq_admission_diagnosis_history_sequence" in history_uniques

    run_alembic(database_url, "downgrade", "20260813_0010")
    assert not (PHASE9_1_TABLES & set(inspect(engine).get_table_names()))
    run_alembic(database_url, "upgrade", "20260813_0011")
    assert PHASE9_1_TABLES <= set(inspect(engine).get_table_names())


def test_single_alembic_head_continues_after_phase9_1() -> None:
    result = subprocess.run(
        ["alembic", "heads"], check=True,
        cwd=os.path.dirname(os.path.dirname(__file__)), capture_output=True, text=True,
    )
    heads = [line for line in result.stdout.splitlines() if line.strip()]
    assert len(heads) == 1
    assert "20260831_0018" in heads[0]
