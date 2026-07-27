from sqlmodel import Session, func, select

from app.db.seed import seed_database
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole


def test_seed_is_idempotent(database_engine) -> None:
    with Session(database_engine) as session:
        seed_database(session)
        seed_database(session)

        assert session.exec(select(func.count()).select_from(Role)).one() == 4
        assert session.exec(select(func.count()).select_from(User)).one() == 4
        assert session.exec(select(func.count()).select_from(UserRole)).one() == 4
