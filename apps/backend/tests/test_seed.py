from sqlmodel import Session, func, select

from app.db.seed import seed_database
from app.models.care_unit import CareUnit
from app.models.care_unit_layout_position import CareUnitLayoutPosition
from app.models.admission import Admission
from app.models.admission_status_history import AdmissionStatusHistory
from app.models.hospital_service import HospitalService
from app.models.nutritionist_service_assignment import NutritionistServiceAssignment
from app.models.patient import Patient
from app.models.patient_location_history import PatientLocationHistory
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
        assert session.exec(select(func.count()).select_from(HospitalService)).one() == 4
        assert session.exec(select(func.count()).select_from(Room)).one() == 5
        assert session.exec(select(func.count()).select_from(CareUnit)).one() == 10
        assert session.exec(select(func.count()).select_from(CareUnitLayoutPosition)).one() == 10
        assert set(session.exec(select(HospitalService.code)).all()) == {
            "MED",
            "UCI",
            "UTI",
            "CIR",
        }
        assert {
            unit_type for unit_type in session.exec(select(CareUnit.unit_type)).all()
        } == {"bed"}
        assert (
            session.exec(
                select(func.count()).select_from(NutritionistServiceAssignment)
            ).one()
            == 2
        )
        assigned_service_ids = set(
            session.exec(
                select(NutritionistServiceAssignment.service_id).where(
                    NutritionistServiceAssignment.is_active.is_(True)
                )
            ).all()
        )
        assigned_codes = set(
            session.exec(
                select(HospitalService.code).where(
                    HospitalService.id.in_(assigned_service_ids)
                )
            ).all()
        )
        assert assigned_codes == {"MED", "UCI"}
        assert session.exec(select(func.count()).select_from(Patient)).one() == 4
        assert session.exec(select(func.count()).select_from(Admission)).one() == 4
        assert (
            session.exec(
                select(func.count())
                .select_from(Admission)
                .where(Admission.status == "active")
            ).one()
            == 3
        )
        assert (
            session.exec(
                select(func.count())
                .select_from(PatientLocationHistory)
                .where(PatientLocationHistory.ended_at.is_(None))
            ).one()
            == 2
        )
        assert (
            session.exec(select(func.count()).select_from(AdmissionStatusHistory)).one()
            == 5
        )


def test_seed_reuses_an_existing_service_with_the_same_name(database_engine) -> None:
    with Session(database_engine) as session:
        surgery = session.exec(
            select(HospitalService).where(HospitalService.name == "Cirugía")
        ).one()
        original_id = surgery.id
        surgery.code = "CIR-LEGACY"
        session.add(surgery)
        session.commit()

        seed_database(session)
        seed_database(session)

        assert session.exec(select(func.count()).select_from(HospitalService)).one() == 4
        preserved = session.exec(
            select(HospitalService).where(HospitalService.name == "Cirugía")
        ).one()
        assert preserved.id == original_id
        assert preserved.code == "CIR-LEGACY"
