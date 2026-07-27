"""Idempotent seed data for local Phase 2 environments."""

from sqlmodel import Session, select

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import engine
from app.models.role import Role
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


def seed_database(session: Session) -> None:
    roles: dict[str, Role] = {}
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

    session.commit()

def main() -> None:
    with Session(engine) as session:
        seed_database(session)
    print("Phase 2 demo roles and users are ready.")


if __name__ == "__main__":
    main()
