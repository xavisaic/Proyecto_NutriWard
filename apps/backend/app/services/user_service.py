import uuid

from sqlalchemy import func
from sqlmodel import Session, select

from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.schemas.user import UserListResponse, UserRead


def normalize_email(email: str) -> str:
    return email.strip().lower()


def get_user_by_email(session: Session, email: str) -> User | None:
    statement = select(User).where(User.email == normalize_email(email))
    return session.exec(statement).first()


def get_user_by_id(session: Session, user_id: uuid.UUID) -> User | None:
    return session.get(User, user_id)


def get_role_names(session: Session, user_id: uuid.UUID) -> list[str]:
    statement = (
        select(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user_id)
        .order_by(Role.name)
    )
    return list(session.exec(statement).all())


def to_user_read(session: Session, user: User) -> UserRead:
    return UserRead(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        roles=get_role_names(session, user.id),
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def list_users(session: Session, offset: int, limit: int) -> UserListResponse:
    users = session.exec(select(User).order_by(User.full_name).offset(offset).limit(limit)).all()
    total = session.exec(select(func.count()).select_from(User)).one()
    return UserListResponse(
        items=[to_user_read(session, user) for user in users],
        total=total,
    )
