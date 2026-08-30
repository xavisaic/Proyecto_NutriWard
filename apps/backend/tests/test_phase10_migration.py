import os
import subprocess

from sqlalchemy import create_engine, inspect, text

from app.db.base import get_metadata


PHASE10_TABLES = {
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


def test_phase10_migration_upgrade_downgrade_and_reupgrade(tmp_path) -> None:
    database_path = tmp_path / "phase10-migration.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    engine = create_engine(database_url)
    metadata = get_metadata()
    previous_tables = [
        table for name, table in metadata.tables.items() if name not in PHASE10_TABLES
    ]
    metadata.create_all(engine, tables=previous_tables)
    with engine.begin() as connection:
        connection.execute(
            text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)")
        )
        connection.execute(
            text("INSERT INTO alembic_version(version_num) VALUES ('20260826_0016')")
        )

    run_alembic(database_url, "upgrade", "head")
    inspector = inspect(engine)
    assert PHASE10_TABLES <= set(inspector.get_table_names())
    assert "ck_meal_plan_has_route" in {
        row["name"] for row in inspector.get_check_constraints("nutritional_meal_plans")
    }
    assert "ck_meal_plan_item_source" in {
        row["name"]
        for row in inspector.get_check_constraints("nutritional_meal_plan_items")
    }
    assert "ck_modular_preparation_schedule" in {
        row["name"]
        for row in inspector.get_check_constraints("nutritional_modular_preparations")
    }
    assert any(
        row["referred_table"] == "admissions"
        for row in inspector.get_foreign_keys("nutritional_meal_plans")
    )

    run_alembic(database_url, "downgrade", "20260826_0016")
    assert not (PHASE10_TABLES & set(inspect(engine).get_table_names()))
    run_alembic(database_url, "upgrade", "head")
    assert PHASE10_TABLES <= set(inspect(engine).get_table_names())


def test_single_alembic_head_is_phase10() -> None:
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
