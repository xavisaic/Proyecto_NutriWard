import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

os.environ["APP_ENV"] = "test"

from app.db.base import get_metadata  # noqa: E402
from app.db.seed import seed_database  # noqa: E402
from app.db.session import get_session  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
def database_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    get_metadata().create_all(engine)
    with Session(engine) as session:
        seed_database(session)
    yield engine
    SQLModel.metadata.drop_all(engine)


@pytest.fixture
def db_session(database_engine) -> Generator[Session, None, None]:
    with Session(database_engine) as session:
        yield session


@pytest.fixture
def client(database_engine) -> Generator[TestClient, None, None]:
    def override_session():
        with Session(database_engine) as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
