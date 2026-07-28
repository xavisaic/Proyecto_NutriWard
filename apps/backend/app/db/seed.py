"""Idempotent seed data for local NutriWard development environments."""

from sqlmodel import Session, select

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import engine
from app.models.care_unit import CareUnit
from app.models.care_unit_layout_position import CareUnitLayoutPosition
from app.models.hospital_service import HospitalService
from app.models.nutritionist_service_assignment import NutritionistServiceAssignment
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
        users[role_name] = user

    services: dict[str, HospitalService] = {}
    for code, (name, description) in SERVICE_DEFINITIONS.items():
        service = session.exec(
            select(HospitalService).where(HospitalService.code == code)
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

    nutritionist_assignment = session.exec(
        select(NutritionistServiceAssignment).where(
            NutritionistServiceAssignment.nutritionist_user_id
            == users["nutricionista"].id,
            NutritionistServiceAssignment.service_id == services["MED"].id,
        )
    ).first()
    if nutritionist_assignment is None:
        session.add(
            NutritionistServiceAssignment(
                nutritionist_user_id=users["nutricionista"].id,
                service_id=services["MED"].id,
            )
        )

    session.commit()

def main() -> None:
    with Session(engine) as session:
        seed_database(session)
    print("Phase 3 demo identity and hospital structure are ready.")


if __name__ == "__main__":
    main()
