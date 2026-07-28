import uuid
from datetime import datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlmodel import Session, select

from app.core.security import hash_password
from app.models.common import utc_now
from app.models.hospital_service import HospitalService
from app.models.nutritionist_service_assignment import NutritionistServiceAssignment
from app.models.role import Role
from app.models.user import User
from app.models.user_role import UserRole
from app.schemas.user import (
    NutritionistServiceAssignmentCreate,
    NutritionistServiceAssignmentListResponse,
    NutritionistServiceAssignmentRead,
    NutritionistServiceAssignmentUpdate,
    RoleListResponse,
    RoleRead,
    UserCreate,
    UserListResponse,
    UserRead,
    UserRoleRead,
    UserUpdate,
)
from app.services.audit_service import record_audit
from app.services.user_service import get_role_names, normalize_email, to_user_read


def _not_found(entity_name: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"{entity_name} no encontrado.",
    )


def _conflict(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


def _json_value(value: Any) -> Any:
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _snapshot(instance: Any, fields: tuple[str, ...]) -> dict[str, Any]:
    return {field: _json_value(getattr(instance, field)) for field in fields}


USER_FIELDS = ("id", "email", "full_name", "is_active", "created_at", "updated_at")
USER_ROLE_FIELDS = (
    "id",
    "user_id",
    "role_id",
    "is_active",
    "created_at",
    "updated_at",
)
ASSIGNMENT_FIELDS = (
    "id",
    "nutritionist_user_id",
    "service_id",
    "is_active",
    "created_at",
    "updated_at",
)


def _get_user(session: Session, user_id: uuid.UUID) -> User:
    user = session.get(User, user_id)
    if user is None:
        raise _not_found("Usuario")
    return user


def _get_role(session: Session, role_id: uuid.UUID) -> Role:
    role = session.get(Role, role_id)
    if role is None:
        raise _not_found("Rol")
    return role


def _get_service(session: Session, service_id: uuid.UUID) -> HospitalService:
    service = session.get(HospitalService, service_id)
    if service is None:
        raise _not_found("Servicio")
    return service


def _get_assignment(
    session: Session,
    assignment_id: uuid.UUID,
) -> NutritionistServiceAssignment:
    assignment = session.get(NutritionistServiceAssignment, assignment_id)
    if assignment is None:
        raise _not_found("Asignación")
    return assignment


def _ensure_email_available(
    session: Session,
    email: str,
    excluding_id: uuid.UUID | None = None,
) -> None:
    statement = select(User).where(func.lower(User.email) == normalize_email(email))
    if excluding_id is not None:
        statement = statement.where(User.id != excluding_id)
    if session.exec(statement).first() is not None:
        raise _conflict("Ya existe un usuario con ese correo.")


def _get_active_user_role(
    session: Session,
    user_id: uuid.UUID,
    role_id: uuid.UUID,
) -> UserRole | None:
    return session.exec(
        select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.role_id == role_id,
            UserRole.is_active.is_(True),
        )
    ).first()


def _has_active_role(session: Session, user_id: uuid.UUID, role_name: str) -> bool:
    statement = (
        select(UserRole.id)
        .join(Role, Role.id == UserRole.role_id)
        .where(
            UserRole.user_id == user_id,
            UserRole.is_active.is_(True),
            Role.name == role_name,
        )
    )
    return session.exec(statement).first() is not None


def _to_user_role_read(link: UserRole, role: Role) -> UserRoleRead:
    return UserRoleRead(
        id=link.id,
        user_id=link.user_id,
        role_id=link.role_id,
        role_name=role.name,
        is_active=link.is_active,
        created_at=link.created_at,
        updated_at=link.updated_at,
    )


def _to_assignment_read(
    assignment: NutritionistServiceAssignment,
    user: User,
    service: HospitalService,
) -> NutritionistServiceAssignmentRead:
    return NutritionistServiceAssignmentRead(
        id=assignment.id,
        nutritionist_user_id=user.id,
        nutritionist_name=user.full_name,
        nutritionist_email=user.email,
        service_id=service.id,
        service_code=service.code,
        service_name=service.name,
        is_active=assignment.is_active,
        created_at=assignment.created_at,
        updated_at=assignment.updated_at,
    )


def _read_assignment(
    session: Session,
    assignment: NutritionistServiceAssignment,
) -> NutritionistServiceAssignmentRead:
    user = _get_user(session, assignment.nutritionist_user_id)
    service = _get_service(session, assignment.service_id)
    return _to_assignment_read(assignment, user, service)


def read_user(session: Session, user_id: uuid.UUID) -> UserRead:
    return to_user_read(session, _get_user(session, user_id))


def create_user(
    session: Session,
    payload: UserCreate,
    actor_user_id: uuid.UUID,
) -> UserRead:
    _ensure_email_available(session, payload.email)
    user = User(
        email=normalize_email(payload.email),
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        is_active=payload.is_active,
    )
    session.add(user)
    session.flush()
    record_audit(
        session,
        action="create",
        actor_user_id=actor_user_id,
        entity_type="user",
        entity_id=user.id,
        after_state=_snapshot(user, USER_FIELDS),
    )
    session.commit()
    session.refresh(user)
    return to_user_read(session, user)


def _deactivate_assignments_for_user(
    session: Session,
    user_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    reason: str,
) -> None:
    assignments = session.exec(
        select(NutritionistServiceAssignment).where(
            NutritionistServiceAssignment.nutritionist_user_id == user_id,
            NutritionistServiceAssignment.is_active.is_(True),
        )
    ).all()
    for assignment in assignments:
        before_state = _snapshot(assignment, ASSIGNMENT_FIELDS)
        assignment.is_active = False
        assignment.updated_at = utc_now()
        session.add(assignment)
        after_state = _snapshot(assignment, ASSIGNMENT_FIELDS)
        after_state["reason"] = reason
        record_audit(
            session,
            action="inactivate",
            actor_user_id=actor_user_id,
            entity_type="nutritionist_service_assignment",
            entity_id=assignment.id,
            before_state=before_state,
            after_state=after_state,
        )


def update_user(
    session: Session,
    user_id: uuid.UUID,
    payload: UserUpdate,
    actor_user_id: uuid.UUID,
) -> UserRead:
    user = _get_user(session, user_id)
    changes = payload.model_dump(exclude_unset=True)
    if "email" in changes:
        _ensure_email_available(session, changes["email"], excluding_id=user.id)

    before_state = _snapshot(user, USER_FIELDS)
    was_active = user.is_active
    for field, value in changes.items():
        setattr(user, field, value)
    user.updated_at = utc_now()
    session.add(user)
    if was_active and not user.is_active:
        _deactivate_assignments_for_user(
            session,
            user.id,
            actor_user_id,
            "usuario_inactivo",
        )
    action = "inactivate" if was_active and not user.is_active else "update"
    record_audit(
        session,
        action=action,
        actor_user_id=actor_user_id,
        entity_type="user",
        entity_id=user.id,
        before_state=before_state,
        after_state=_snapshot(user, USER_FIELDS),
    )
    session.commit()
    session.refresh(user)
    return to_user_read(session, user)


def inactivate_user(
    session: Session,
    user_id: uuid.UUID,
    actor_user_id: uuid.UUID,
) -> None:
    user = _get_user(session, user_id)
    if not user.is_active:
        return
    update_user(
        session,
        user_id,
        UserUpdate(is_active=False),
        actor_user_id,
    )


def list_roles(session: Session) -> RoleListResponse:
    roles = session.exec(select(Role).order_by(Role.name)).all()
    return RoleListResponse(
        items=[RoleRead.model_validate(role) for role in roles],
        total=len(roles),
    )


def list_user_roles(session: Session, user_id: uuid.UUID) -> RoleListResponse:
    _get_user(session, user_id)
    roles = session.exec(
        select(Role)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(
            UserRole.user_id == user_id,
            UserRole.is_active.is_(True),
        )
        .order_by(Role.name)
    ).all()
    return RoleListResponse(
        items=[RoleRead.model_validate(role) for role in roles],
        total=len(roles),
    )


def list_role_users(session: Session, role_id: uuid.UUID) -> UserListResponse:
    _get_role(session, role_id)
    users = session.exec(
        select(User)
        .join(UserRole, UserRole.user_id == User.id)
        .where(
            UserRole.role_id == role_id,
            UserRole.is_active.is_(True),
        )
        .order_by(User.full_name)
    ).all()
    return UserListResponse(
        items=[to_user_read(session, user) for user in users],
        total=len(users),
    )


def assign_role(
    session: Session,
    user_id: uuid.UUID,
    role_id: uuid.UUID,
    actor_user_id: uuid.UUID,
) -> UserRoleRead:
    user = _get_user(session, user_id)
    role = _get_role(session, role_id)
    if not user.is_active:
        raise _conflict("Solo los usuarios activos pueden recibir roles.")

    link = session.exec(
        select(UserRole).where(
            UserRole.user_id == user.id,
            UserRole.role_id == role.id,
        )
    ).first()
    if link is not None and link.is_active:
        raise _conflict("El usuario ya tiene asignado ese rol.")

    before_state = _snapshot(link, USER_ROLE_FIELDS) if link is not None else None
    if link is None:
        link = UserRole(user_id=user.id, role_id=role.id)
    else:
        link.is_active = True
        link.updated_at = utc_now()
    session.add(link)
    session.flush()
    record_audit(
        session,
        action="assign_role",
        actor_user_id=actor_user_id,
        entity_type="user_role",
        entity_id=link.id,
        before_state=before_state,
        after_state=_snapshot(link, USER_ROLE_FIELDS),
    )
    session.commit()
    session.refresh(link)
    return _to_user_role_read(link, role)


def remove_role(
    session: Session,
    user_id: uuid.UUID,
    role_id: uuid.UUID,
    actor_user_id: uuid.UUID,
) -> None:
    _get_user(session, user_id)
    role = _get_role(session, role_id)
    link = _get_active_user_role(session, user_id, role_id)
    if link is None:
        raise _not_found("Asignación de rol")

    before_state = _snapshot(link, USER_ROLE_FIELDS)
    link.is_active = False
    link.updated_at = utc_now()
    session.add(link)
    if role.name == "nutricionista":
        _deactivate_assignments_for_user(
            session,
            user_id,
            actor_user_id,
            "rol_nutricionista_retirado",
        )
    record_audit(
        session,
        action="remove_role",
        actor_user_id=actor_user_id,
        entity_type="user_role",
        entity_id=link.id,
        before_state=before_state,
        after_state=_snapshot(link, USER_ROLE_FIELDS),
    )
    session.commit()


def _ensure_assignment_eligibility(
    session: Session,
    user_id: uuid.UUID,
    service_id: uuid.UUID,
) -> tuple[User, HospitalService]:
    user = _get_user(session, user_id)
    if not user.is_active:
        raise _conflict("No se pueden asignar servicios a usuarios inactivos.")
    if not _has_active_role(session, user.id, "nutricionista"):
        raise _conflict("El usuario debe tener el rol nutricionista.")
    service = _get_service(session, service_id)
    if not service.is_active:
        raise _conflict("El servicio asignado debe estar activo.")
    return user, service


def list_assignments(
    session: Session,
    *,
    nutritionist_user_id: uuid.UUID | None = None,
    include_inactive: bool = False,
) -> NutritionistServiceAssignmentListResponse:
    statement = (
        select(NutritionistServiceAssignment, User, HospitalService)
        .join(
            User,
            User.id == NutritionistServiceAssignment.nutritionist_user_id,
        )
        .join(
            HospitalService,
            HospitalService.id == NutritionistServiceAssignment.service_id,
        )
        .order_by(User.full_name, HospitalService.name)
    )
    if nutritionist_user_id is not None:
        _get_user(session, nutritionist_user_id)
        statement = statement.where(
            NutritionistServiceAssignment.nutritionist_user_id
            == nutritionist_user_id
        )
    if not include_inactive:
        statement = statement.where(
            NutritionistServiceAssignment.is_active.is_(True)
        )
    rows = session.exec(statement).all()
    items = [
        _to_assignment_read(assignment, user, service)
        for assignment, user, service in rows
    ]
    return NutritionistServiceAssignmentListResponse(items=items, total=len(items))


def create_assignment(
    session: Session,
    payload: NutritionistServiceAssignmentCreate,
    actor_user_id: uuid.UUID,
) -> NutritionistServiceAssignmentRead:
    user, service = _ensure_assignment_eligibility(
        session,
        payload.nutritionist_user_id,
        payload.service_id,
    )
    assignment = session.exec(
        select(NutritionistServiceAssignment).where(
            NutritionistServiceAssignment.nutritionist_user_id == user.id,
            NutritionistServiceAssignment.service_id == service.id,
        )
    ).first()
    if assignment is not None and assignment.is_active:
        raise _conflict("El nutricionista ya tiene asignado ese servicio.")

    before_state = (
        _snapshot(assignment, ASSIGNMENT_FIELDS) if assignment is not None else None
    )
    action = "create"
    if assignment is None:
        assignment = NutritionistServiceAssignment(
            nutritionist_user_id=user.id,
            service_id=service.id,
        )
    else:
        assignment.is_active = True
        assignment.updated_at = utc_now()
        action = "reactivate"
    session.add(assignment)
    session.flush()
    record_audit(
        session,
        action=action,
        actor_user_id=actor_user_id,
        entity_type="nutritionist_service_assignment",
        entity_id=assignment.id,
        before_state=before_state,
        after_state=_snapshot(assignment, ASSIGNMENT_FIELDS),
    )
    session.commit()
    session.refresh(assignment)
    return _to_assignment_read(assignment, user, service)


def update_assignment(
    session: Session,
    assignment_id: uuid.UUID,
    payload: NutritionistServiceAssignmentUpdate,
    actor_user_id: uuid.UUID,
) -> NutritionistServiceAssignmentRead:
    assignment = _get_assignment(session, assignment_id)
    changes = payload.model_dump(exclude_unset=True)
    next_service_id = changes.get("service_id", assignment.service_id)
    next_active = changes.get("is_active", assignment.is_active)

    if next_active:
        user, service = _ensure_assignment_eligibility(
            session,
            assignment.nutritionist_user_id,
            next_service_id,
        )
    else:
        user = _get_user(session, assignment.nutritionist_user_id)
        service = _get_service(session, next_service_id)
        if "service_id" in changes and not service.is_active:
            raise _conflict("El servicio asignado debe estar activo.")

    if next_service_id != assignment.service_id:
        duplicate = session.exec(
            select(NutritionistServiceAssignment).where(
                NutritionistServiceAssignment.id != assignment.id,
                NutritionistServiceAssignment.nutritionist_user_id
                == assignment.nutritionist_user_id,
                NutritionistServiceAssignment.service_id == next_service_id,
            )
        ).first()
        if duplicate is not None:
            raise _conflict("El nutricionista ya tiene un registro para ese servicio.")

    before_state = _snapshot(assignment, ASSIGNMENT_FIELDS)
    was_active = assignment.is_active
    for field, value in changes.items():
        setattr(assignment, field, value)
    assignment.updated_at = utc_now()
    session.add(assignment)
    if was_active and not assignment.is_active:
        action = "inactivate"
    elif not was_active and assignment.is_active:
        action = "reactivate"
    else:
        action = "update"
    record_audit(
        session,
        action=action,
        actor_user_id=actor_user_id,
        entity_type="nutritionist_service_assignment",
        entity_id=assignment.id,
        before_state=before_state,
        after_state=_snapshot(assignment, ASSIGNMENT_FIELDS),
    )
    session.commit()
    session.refresh(assignment)
    return _to_assignment_read(assignment, user, service)


def inactivate_assignment(
    session: Session,
    assignment_id: uuid.UUID,
    actor_user_id: uuid.UUID,
) -> None:
    assignment = _get_assignment(session, assignment_id)
    if not assignment.is_active:
        return
    update_assignment(
        session,
        assignment_id,
        NutritionistServiceAssignmentUpdate(is_active=False),
        actor_user_id,
    )
