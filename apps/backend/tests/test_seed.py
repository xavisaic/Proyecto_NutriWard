from sqlmodel import Session, func, select

from app.db.seed import seed_database
from app.models.care_unit import CareUnit
from app.models.care_unit_layout_position import CareUnitLayoutPosition
from app.models.hospital_service import HospitalService
from app.models.nutritionist_service_assignment import NutritionistServiceAssignment
from app.models.role import Role
from app.models.room import Room
from app.models.user import User
from app.models.user_role import UserRole


def test_seed_is_idempotent(database_engine) -> None:
    with Session(database_engine) as session:
        seed_database(session)
        seed_database(session)

        assert session.exec(select(func.count()).select_from(Role)).one() == 4
        assert session.exec(select(func.count()).select_from(User)).one() == 4
        assert session.exec(select(func.count()).select_from(UserRole)).one() == 4
        assert session.exec(select(func.count()).select_from(HospitalService)).one() == 2
        assert session.exec(select(func.count()).select_from(Room)).one() == 3
        assert session.exec(select(func.count()).select_from(CareUnit)).one() == 6
        assert session.exec(select(func.count()).select_from(CareUnitLayoutPosition)).one() == 6
        assert {
            unit_type for unit_type in session.exec(select(CareUnit.unit_type)).all()
        } == {"bed"}
        assert (
            session.exec(
                select(func.count()).select_from(NutritionistServiceAssignment)
            ).one()
            == 1
        )
