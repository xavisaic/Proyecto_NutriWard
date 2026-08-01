"""Idempotent seed data for local NutriWard development environments."""

from datetime import datetime, timezone

from sqlalchemy import or_
from sqlmodel import Session, select

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import engine
from app.models.care_unit import CareUnit
from app.models.care_unit_layout_position import CareUnitLayoutPosition
from app.models.admission import Admission
from app.models.admission_status_history import AdmissionStatusHistory
from app.models.common import utc_now
from app.models.hospital_service import HospitalService
from app.models.nutritionist_service_assignment import NutritionistServiceAssignment
from app.models.patient import Patient
from app.models.patient_location_history import PatientLocationHistory
from app.models.role import Role
from app.models.room import Room
from app.models.user import User
from app.models.user_role import UserRole
from app.services.user_service import normalize_email

ROLE_DEFINITIONS = {
    "nutricionista": "Atención nutricional clínica.",
    "jefatura": "Supervisión y coordinación clínica.",
    "alimentacion": "Operación del servicio de alimentación.",
    "administrador": "Administración técnica de NutriWard.",
}

DEMO_USERS = {
    "nutricionista": ("nutricionista@nutriward.local", "Nutricionista Demo"),
    "jefatura": ("jefatura@nutriward.local", "Jefatura Demo"),
    "alimentacion": ("alimentacion@nutriward.local", "Alimentación Demo"),
    "administrador": ("administrador@nutriward.local", "Administrador Demo"),
}

SERVICE_DEFINITIONS = {
    "MED": ("Medicina", "Hospitalización médico-quirúrgica."),
    "UCI": ("Unidad de Cuidados Intensivos", "Atención de pacientes críticos."),
    "UTI": ("Unidad de Tratamiento Intermedio", "Atención intermedia y monitorización."),
    "CIR": ("Cirugía", "Hospitalización quirúrgica."),
}

ROOM_DEFINITIONS = {
    "MED": (
        ("A101", "Sala A101", "Piso 1"),
        ("A102", "Sala A102", "Piso 1"),
    ),
    "UCI": (("UCI-A", "UCI Sector A", "Piso 2"),),
    "UTI": (("UTI-A", "UTI Sector A", "Piso 2"),),
    "CIR": (("C201", "Sala C201", "Piso 2"),),
}

CARE_UNIT_DEFINITIONS = {
    ("MED", "A101"): ("01", "02"),
    ("MED", "A102"): ("01", "02"),
    ("UCI", "UCI-A"): ("01", "02"),
    ("UTI", "UTI-A"): ("01", "02"),
    ("CIR", "C201"): ("01", "02"),
}

PATIENT_DEFINITIONS = (
    {
        "key": "identified_one",
        "identity_status": "identified",
        "rut": "11111111-1",
        "given_names": "Paciente",
        "first_surname": "Demostración Uno",
        "date_of_birth": datetime(1980, 1, 15, tzinfo=timezone.utc).date(),
        "sex": "female",
        "hospital_identifier": "DEMO-PAC-001",
    },
    {
        "key": "identified_two",
        "identity_status": "identified",
        "rut": "22222222-2",
        "given_names": "Paciente",
        "first_surname": "Demostración Dos",
        "date_of_birth": datetime(1972, 6, 20, tzinfo=timezone.utc).date(),
        "sex": "male",
        "hospital_identifier": "DEMO-PAC-002",
    },
    {
        "key": "nn_one",
        "identity_status": "unidentified",
        "temporary_identifier": "NN-20260731-A001",
        "provisional_description": "Persona adulta de identidad desconocida, caso demostrativo A.",
        "sex": "unknown",
    },
    {
        "key": "nn_two",
        "identity_status": "unidentified",
        "temporary_identifier": "NN-20260731-A002",
        "provisional_description": "Persona adulta de identidad desconocida, caso demostrativo B.",
        "sex": "unknown",
    },
)

ADMISSION_DEFINITIONS = (
    {
        "identifier": "ADM-DEMO-ACT-001",
        "patient_key": "identified_one",
        "status": "active",
        "admitted_at": datetime(2026, 7, 29, 13, 0, tzinfo=timezone.utc),
        "bed": ("MED", "A101", "01"),
    },
    {
        "identifier": "ADM-DEMO-ACT-002",
        "patient_key": "nn_one",
        "status": "active",
        "admitted_at": datetime(2026, 7, 30, 17, 30, tzinfo=timezone.utc),
        "bed": ("UCI", "UCI-A", "01"),
    },
    {
        "identifier": "ADM-DEMO-ACT-003",
        "patient_key": "nn_two",
        "status": "active",
        "admitted_at": datetime(2026, 7, 31, 8, 15, tzinfo=timezone.utc),
        "bed": None,
    },
    {
        "identifier": "ADM-DEMO-HIST-001",
        "patient_key": "identified_two",
        "status": "discharged",
        "admitted_at": datetime(2026, 7, 10, 12, 0, tzinfo=timezone.utc),
        "ended_at": datetime(2026, 7, 15, 16, 0, tzinfo=timezone.utc),
        "end_reason": "Alta médica demostrativa.",
        "bed": ("MED", "A102", "01"),
    },
)


def seed_database(session: Session) -> None:
    roles: dict[str, Role] = {}
    users: dict[str, User] = {}
    for name, description in ROLE_DEFINITIONS.items():
        role = session.exec(select(Role).where(Role.name == name)).first()
        if role is None:
            role = Role(name=name, description=description)
            session.add(role)
            session.flush()
        roles[name] = role

    for role_name, (email, full_name) in DEMO_USERS.items():
        normalized_email = normalize_email(email)
        user = session.exec(select(User).where(User.email == normalized_email)).first()
        if user is None:
            user = User(
                email=normalized_email,
                full_name=full_name,
                password_hash=hash_password(settings.demo_user_password),
            )
            session.add(user)
            session.flush()

        assignment = session.exec(
            select(UserRole).where(
                UserRole.user_id == user.id,
                UserRole.role_id == roles[role_name].id,
            )
        ).first()
        if assignment is None:
            session.add(UserRole(user_id=user.id, role_id=roles[role_name].id))
        elif not assignment.is_active:
            assignment.is_active = True
            assignment.updated_at = utc_now()
            session.add(assignment)
        users[role_name] = user

    services: dict[str, HospitalService] = {}
    for code, (name, description) in SERVICE_DEFINITIONS.items():
        service = session.exec(
            select(HospitalService).where(
                or_(HospitalService.code == code, HospitalService.name == name)
            )
        ).first()
        if service is None:
            service = HospitalService(code=code, name=name, description=description)
            session.add(service)
            session.flush()
        services[code] = service

    rooms: dict[tuple[str, str], Room] = {}
    for service_code, definitions in ROOM_DEFINITIONS.items():
        for room_code, room_name, floor in definitions:
            room = session.exec(
                select(Room).where(
                    Room.service_id == services[service_code].id,
                    Room.code == room_code,
                )
            ).first()
            if room is None:
                room = Room(
                    service_id=services[service_code].id,
                    code=room_code,
                    name=room_name,
                    floor=floor,
                )
                session.add(room)
                session.flush()
            rooms[(service_code, room_code)] = room

    for room_key, care_unit_codes in CARE_UNIT_DEFINITIONS.items():
        for position, care_unit_code in enumerate(care_unit_codes):
            room = rooms[room_key]
            care_unit = session.exec(
                select(CareUnit).where(CareUnit.room_id == room.id, CareUnit.code == care_unit_code)
            ).first()
            if care_unit is None:
                care_unit = CareUnit(room_id=room.id, code=care_unit_code, label=f"Cama {care_unit_code}")
                session.add(care_unit)
                session.flush()
            layout = session.exec(
                select(CareUnitLayoutPosition).where(CareUnitLayoutPosition.care_unit_id == care_unit.id)
            ).first()
            if layout is None:
                session.add(
                    CareUnitLayoutPosition(
                        care_unit_id=care_unit.id,
                        grid_x=position * 2,
                        grid_y=0,
                    )
                )

    for service_code in ("MED", "UCI"):
        nutritionist_assignment = session.exec(
            select(NutritionistServiceAssignment).where(
                NutritionistServiceAssignment.nutritionist_user_id
                == users["nutricionista"].id,
                NutritionistServiceAssignment.service_id == services[service_code].id,
            )
        ).first()
        if nutritionist_assignment is None:
            session.add(
                NutritionistServiceAssignment(
                    nutritionist_user_id=users["nutricionista"].id,
                    service_id=services[service_code].id,
                )
            )
        elif not nutritionist_assignment.is_active:
            nutritionist_assignment.is_active = True
            nutritionist_assignment.updated_at = utc_now()
            session.add(nutritionist_assignment)

    patients: dict[str, Patient] = {}
    seed_actor = users["administrador"]
    for definition in PATIENT_DEFINITIONS:
        lookup = (
            Patient.rut == definition["rut"]
            if definition.get("rut")
            else Patient.temporary_identifier == definition["temporary_identifier"]
        )
        patient = session.exec(select(Patient).where(lookup)).first()
        if patient is None:
            data = {key: value for key, value in definition.items() if key != "key"}
            patient = Patient(
                **data,
                identified_at=utc_now() if data["identity_status"] == "identified" else None,
                identified_by_user_id=seed_actor.id
                if data["identity_status"] == "identified"
                else None,
                created_by_user_id=seed_actor.id,
                updated_by_user_id=seed_actor.id,
            )
            session.add(patient)
            session.flush()
        patients[definition["key"]] = patient

    care_units_by_key: dict[tuple[str, str, str], CareUnit] = {}
    for service_code, room_code, care_unit_code in {
        definition["bed"] for definition in ADMISSION_DEFINITIONS if definition["bed"]
    }:
        room = rooms[(service_code, room_code)]
        care_units_by_key[(service_code, room_code, care_unit_code)] = session.exec(
            select(CareUnit).where(
                CareUnit.room_id == room.id,
                CareUnit.code == care_unit_code,
            )
        ).one()

    for definition in ADMISSION_DEFINITIONS:
        admission = session.exec(
            select(Admission).where(
                Admission.admission_identifier == definition["identifier"]
            )
        ).first()
        if admission is None:
            admission = Admission(
                patient_id=patients[definition["patient_key"]].id,
                admission_identifier=definition["identifier"],
                status=definition["status"],
                admitted_at=definition["admitted_at"],
                ended_at=definition.get("ended_at"),
                end_reason=definition.get("end_reason"),
                created_by_user_id=seed_actor.id,
                updated_by_user_id=seed_actor.id,
            )
            session.add(admission)
            session.flush()
        initial_history = session.exec(
            select(AdmissionStatusHistory).where(
                AdmissionStatusHistory.admission_id == admission.id,
                AdmissionStatusHistory.to_status == "active",
            )
        ).first()
        if initial_history is None:
            session.add(
                AdmissionStatusHistory(
                    admission_id=admission.id,
                    from_status=None,
                    to_status="active",
                    reason="Creación de hospitalización demo.",
                    changed_at=definition["admitted_at"],
                    changed_by_user_id=seed_actor.id,
                )
            )
        if definition["status"] != "active":
            terminal_history = session.exec(
                select(AdmissionStatusHistory).where(
                    AdmissionStatusHistory.admission_id == admission.id,
                    AdmissionStatusHistory.to_status == definition["status"],
                )
            ).first()
            if terminal_history is None:
                session.add(
                    AdmissionStatusHistory(
                        admission_id=admission.id,
                        from_status="active",
                        to_status=definition["status"],
                        reason=definition["end_reason"],
                        changed_at=definition["ended_at"],
                        changed_by_user_id=seed_actor.id,
                    )
                )
        if definition["bed"]:
            care_unit = care_units_by_key[definition["bed"]]
            location = session.exec(
                select(PatientLocationHistory).where(
                    PatientLocationHistory.admission_id == admission.id,
                    PatientLocationHistory.care_unit_id == care_unit.id,
                )
            ).first()
            if location is None:
                session.add(
                    PatientLocationHistory(
                        admission_id=admission.id,
                        care_unit_id=care_unit.id,
                        started_at=definition["admitted_at"],
                        ended_at=definition.get("ended_at"),
                        reason="Asignación demo.",
                        assigned_by_user_id=seed_actor.id,
                        ended_by_user_id=seed_actor.id
                        if definition.get("ended_at")
                        else None,
                    )
                )
    session.commit()

def main() -> None:
    with Session(engine) as session:
        seed_database(session)
    print("Phase 5 demo identity, hospital structure, patients, and admissions are ready.")


if __name__ == "__main__":
    main()
