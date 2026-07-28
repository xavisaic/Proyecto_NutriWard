import uuid
import re
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlmodel import Session, select

from app.models.care_unit import CareUnit
from app.models.care_unit_layout_position import CareUnitLayoutPosition
from app.models.common import utc_now
from app.models.hospital_service import HospitalService
from app.models.nutritionist_service_assignment import NutritionistServiceAssignment
from app.models.room import Room
from app.schemas.hospital import (
    CareUnitCreate,
    CareUnitRead,
    CareUnitUpdate,
    HospitalStructureResponse,
    LayoutRead,
    LayoutUpsert,
    RoomCreate,
    RoomRead,
    RoomUpdate,
    ServiceCreate,
    ServiceRead,
    ServiceUpdate,
    PurgeRequest,
)
from app.services.audit_service import record_audit


def _not_found(entity_name: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"{entity_name} no encontrado.",
    )


def _conflict(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


def _snapshot(instance: Any, fields: tuple[str, ...]) -> dict[str, Any]:
    snapshot: dict[str, Any] = {}
    for field in fields:
        value = getattr(instance, field)
        snapshot[field] = str(value) if isinstance(value, uuid.UUID) else value
    return snapshot


SERVICE_FIELDS = ("id", "code", "name", "description", "is_active")
ROOM_FIELDS = ("id", "service_id", "code", "name", "floor", "notes", "is_active")
CARE_UNIT_FIELDS = ("id", "room_id", "code", "label", "unit_type", "is_active")
LAYOUT_FIELDS = ("id", "care_unit_id", "grid_x", "grid_y", "width", "height")


def _get_service(session: Session, service_id: uuid.UUID) -> HospitalService:
    service = session.get(HospitalService, service_id)
    if service is None:
        raise _not_found("Servicio")
    return service


def _get_room(session: Session, room_id: uuid.UUID) -> Room:
    room = session.get(Room, room_id)
    if room is None:
        raise _not_found("Sala")
    return room


def _get_care_unit(session: Session, care_unit_id: uuid.UUID) -> CareUnit:
    care_unit = session.get(CareUnit, care_unit_id)
    if care_unit is None:
        raise _not_found("Ubicación asistencial")
    return care_unit


def _ensure_service_identity_available(
    session: Session,
    *,
    code: str,
    name: str,
    excluding_id: uuid.UUID | None = None,
) -> None:
    statement = select(HospitalService).where(
        (func.lower(HospitalService.code) == code.lower())
        | (func.lower(HospitalService.name) == name.lower())
    )
    if excluding_id is not None:
        statement = statement.where(HospitalService.id != excluding_id)
    if session.exec(statement).first() is not None:
        raise _conflict("Ya existe un servicio con ese código o nombre.")


def _ensure_room_code_available(
    session: Session,
    *,
    service_id: uuid.UUID,
    code: str,
    excluding_id: uuid.UUID | None = None,
) -> None:
    statement = select(Room).where(
        Room.service_id == service_id,
        func.lower(Room.code) == code.lower(),
    )
    if excluding_id is not None:
        statement = statement.where(Room.id != excluding_id)
    if session.exec(statement).first() is not None:
        raise _conflict("Ya existe una sala con ese código en el servicio.")


def _ensure_care_unit_code_available(
    session: Session,
    *,
    room_id: uuid.UUID,
    code: str,
    excluding_id: uuid.UUID | None = None,
) -> None:
    statement = select(CareUnit).where(
        CareUnit.room_id == room_id,
        func.lower(CareUnit.code) == code.lower(),
    )
    if excluding_id is not None:
        statement = statement.where(CareUnit.id != excluding_id)
    if session.exec(statement).first() is not None:
        raise _conflict("Ya existe una ubicación con ese código en la sala.")


def _suggest_care_unit_code(session: Session, room_id: uuid.UUID) -> str:
    existing_codes = session.exec(
        select(CareUnit.code).where(CareUnit.room_id == room_id)
    ).all()
    numeric_values: list[int] = []
    numeric_width = 2
    prefixed_values: list[int] = []
    prefixed_width = 2
    for code in existing_codes:
        if code.isdigit():
            numeric_values.append(int(code))
            numeric_width = max(numeric_width, len(code))
            continue
        match = re.fullmatch(r"C(\d+)", code, flags=re.IGNORECASE)
        if match:
            prefixed_values.append(int(match.group(1)))
            prefixed_width = max(prefixed_width, len(match.group(1)))
    if numeric_values:
        return str(max(numeric_values) + 1).zfill(numeric_width)
    if prefixed_values:
        return f"C{str(max(prefixed_values) + 1).zfill(prefixed_width)}"
    return "C01"


def _to_care_unit_read(care_unit: CareUnit, layout: CareUnitLayoutPosition | None) -> CareUnitRead:
    return CareUnitRead(
        id=care_unit.id,
        room_id=care_unit.room_id,
        code=care_unit.code,
        label=care_unit.label,
        unit_type=care_unit.unit_type,
        is_active=care_unit.is_active,
        layout=LayoutRead.model_validate(layout) if layout else None,
        created_at=care_unit.created_at,
        updated_at=care_unit.updated_at,
    )


def _read_care_unit(session: Session, care_unit: CareUnit) -> CareUnitRead:
    layout = session.exec(
        select(CareUnitLayoutPosition).where(CareUnitLayoutPosition.care_unit_id == care_unit.id)
    ).first()
    return _to_care_unit_read(care_unit, layout)


def list_structure(session: Session, include_inactive: bool) -> HospitalStructureResponse:
    services_statement = select(HospitalService).order_by(
        HospitalService.name,
        HospitalService.code,
    )
    if not include_inactive:
        services_statement = services_statement.where(HospitalService.is_active.is_(True))
    services = session.exec(services_statement).all()
    if not services:
        return HospitalStructureResponse(items=[], total=0)

    service_ids = [service.id for service in services]
    rooms_statement = (
        select(Room)
        .where(Room.service_id.in_(service_ids))
        .order_by(Room.service_id, Room.code)
    )
    if not include_inactive:
        rooms_statement = rooms_statement.where(Room.is_active.is_(True))
    rooms = session.exec(rooms_statement).all()

    room_ids = [room.id for room in rooms]
    care_units: list[CareUnit] = []
    if room_ids:
        care_units_statement = (
            select(CareUnit)
            .where(CareUnit.room_id.in_(room_ids))
            .order_by(CareUnit.room_id, CareUnit.code)
        )
        if not include_inactive:
            care_units_statement = care_units_statement.where(CareUnit.is_active.is_(True))
        care_units = list(session.exec(care_units_statement).all())

    layouts_by_care_unit: dict[uuid.UUID, CareUnitLayoutPosition] = {}
    if care_units:
        layouts = session.exec(
            select(CareUnitLayoutPosition).where(
                CareUnitLayoutPosition.care_unit_id.in_([care_unit.id for care_unit in care_units])
            )
        ).all()
        layouts_by_care_unit = {layout.care_unit_id: layout for layout in layouts}

    care_units_by_room: dict[uuid.UUID, list[CareUnitRead]] = {}
    for care_unit in care_units:
        care_units_by_room.setdefault(care_unit.room_id, []).append(
            _to_care_unit_read(care_unit, layouts_by_care_unit.get(care_unit.id))
        )

    rooms_by_service: dict[uuid.UUID, list[RoomRead]] = {}
    for room in rooms:
        rooms_by_service.setdefault(room.service_id, []).append(
            RoomRead(
                id=room.id,
                service_id=room.service_id,
                code=room.code,
                name=room.name,
                floor=room.floor,
                notes=room.notes,
                is_active=room.is_active,
                care_units=care_units_by_room.get(room.id, []),
                created_at=room.created_at,
                updated_at=room.updated_at,
            )
        )

    items = [
        ServiceRead(
            id=service.id,
            code=service.code,
            name=service.name,
            description=service.description,
            is_active=service.is_active,
            rooms=rooms_by_service.get(service.id, []),
            created_at=service.created_at,
            updated_at=service.updated_at,
        )
        for service in services
    ]
    return HospitalStructureResponse(items=items, total=len(items))


def create_service(
    session: Session,
    payload: ServiceCreate,
    actor_user_id: uuid.UUID,
) -> ServiceRead:
    _ensure_service_identity_available(session, code=payload.code, name=payload.name)
    service = HospitalService(**payload.model_dump())
    session.add(service)
    session.flush()
    record_audit(
        session,
        action="create",
        actor_user_id=actor_user_id,
        entity_type="service",
        entity_id=service.id,
        after_state=_snapshot(service, SERVICE_FIELDS),
    )
    session.commit()
    session.refresh(service)
    return ServiceRead.model_validate(service)


def update_service(
    session: Session,
    service_id: uuid.UUID,
    payload: ServiceUpdate,
    actor_user_id: uuid.UUID,
) -> ServiceRead:
    service = _get_service(session, service_id)
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=422, detail="Debe indicar al menos un cambio.")
    next_code = changes.get("code", service.code)
    next_name = changes.get("name", service.name)
    _ensure_service_identity_available(
        session,
        code=next_code,
        name=next_name,
        excluding_id=service.id,
    )
    if changes.get("is_active") is False and service.is_active:
        active_room = session.exec(
            select(Room).where(Room.service_id == service.id, Room.is_active.is_(True))
        ).first()
        if active_room is not None:
            raise _conflict("No se puede inactivar un servicio que contiene salas activas.")

    before_state = _snapshot(service, SERVICE_FIELDS)
    for field, value in changes.items():
        setattr(service, field, value)
    service.updated_at = utc_now()
    session.add(service)
    record_audit(
        session,
        action="update",
        actor_user_id=actor_user_id,
        entity_type="service",
        entity_id=service.id,
        before_state=before_state,
        after_state=_snapshot(service, SERVICE_FIELDS),
    )
    session.commit()
    session.refresh(service)
    return ServiceRead.model_validate(service)


def create_room(
    session: Session,
    payload: RoomCreate,
    actor_user_id: uuid.UUID,
) -> RoomRead:
    service = _get_service(session, payload.service_id)
    if not service.is_active:
        raise _conflict("No se puede crear una sala en un servicio inactivo.")
    _ensure_room_code_available(
        session,
        service_id=payload.service_id,
        code=payload.code,
    )
    room = Room(**payload.model_dump())
    session.add(room)
    session.flush()
    record_audit(
        session,
        action="create",
        actor_user_id=actor_user_id,
        entity_type="room",
        entity_id=room.id,
        after_state=_snapshot(room, ROOM_FIELDS),
    )
    session.commit()
    session.refresh(room)
    return RoomRead.model_validate(room)


def update_room(
    session: Session,
    room_id: uuid.UUID,
    payload: RoomUpdate,
    actor_user_id: uuid.UUID,
) -> RoomRead:
    room = _get_room(session, room_id)
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=422, detail="Debe indicar al menos un cambio.")
    next_service_id = changes.get("service_id", room.service_id)
    next_code = changes.get("code", room.code)
    parent = _get_service(session, next_service_id)
    next_active = changes.get("is_active", room.is_active)
    if next_active and not parent.is_active:
        raise _conflict("Una sala activa debe pertenecer a un servicio activo.")
    _ensure_room_code_available(
        session,
        service_id=next_service_id,
        code=next_code,
        excluding_id=room.id,
    )
    if changes.get("is_active") is False and room.is_active:
        active_care_unit = session.exec(
            select(CareUnit).where(CareUnit.room_id == room.id, CareUnit.is_active.is_(True))
        ).first()
        if active_care_unit is not None:
            raise _conflict(
                "No se puede inactivar una sala que contiene ubicaciones activas."
            )

    before_state = _snapshot(room, ROOM_FIELDS)
    for field, value in changes.items():
        setattr(room, field, value)
    room.updated_at = utc_now()
    session.add(room)
    record_audit(
        session,
        action="update",
        actor_user_id=actor_user_id,
        entity_type="room",
        entity_id=room.id,
        before_state=before_state,
        after_state=_snapshot(room, ROOM_FIELDS),
    )
    session.commit()
    session.refresh(room)
    return RoomRead.model_validate(room)


def create_care_unit(
    session: Session,
    payload: CareUnitCreate,
    actor_user_id: uuid.UUID,
) -> CareUnitRead:
    room = _get_room(session, payload.room_id)
    if not room.is_active:
        raise _conflict("No se puede crear una ubicación en una sala inactiva.")
    code = payload.code or _suggest_care_unit_code(session, payload.room_id)
    _ensure_care_unit_code_available(session, room_id=payload.room_id, code=code)
    care_unit = CareUnit(**payload.model_dump(exclude={"code"}), code=code)
    session.add(care_unit)
    session.flush()
    record_audit(
        session,
        action="create",
        actor_user_id=actor_user_id,
        entity_type="care_unit",
        entity_id=care_unit.id,
        after_state=_snapshot(care_unit, CARE_UNIT_FIELDS),
    )
    session.commit()
    session.refresh(care_unit)
    return _read_care_unit(session, care_unit)


def update_care_unit(
    session: Session,
    care_unit_id: uuid.UUID,
    payload: CareUnitUpdate,
    actor_user_id: uuid.UUID,
) -> CareUnitRead:
    care_unit = _get_care_unit(session, care_unit_id)
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=422, detail="Debe indicar al menos un cambio.")
    next_room_id = changes.get("room_id", care_unit.room_id)
    next_code = changes.get("code", care_unit.code)
    parent = _get_room(session, next_room_id)
    next_active = changes.get("is_active", care_unit.is_active)
    if next_active and not parent.is_active:
        raise _conflict("Una ubicación activa debe pertenecer a una sala activa.")
    _ensure_care_unit_code_available(
        session,
        room_id=next_room_id,
        code=next_code,
        excluding_id=care_unit.id,
    )

    before_state = _snapshot(care_unit, CARE_UNIT_FIELDS)
    for field, value in changes.items():
        setattr(care_unit, field, value)
    care_unit.updated_at = utc_now()
    session.add(care_unit)
    record_audit(
        session,
        action="update",
        actor_user_id=actor_user_id,
        entity_type="care_unit",
        entity_id=care_unit.id,
        before_state=before_state,
        after_state=_snapshot(care_unit, CARE_UNIT_FIELDS),
    )
    session.commit()
    session.refresh(care_unit)
    return _read_care_unit(session, care_unit)


def upsert_care_unit_layout(
    session: Session,
    care_unit_id: uuid.UUID,
    payload: LayoutUpsert,
    actor_user_id: uuid.UUID,
) -> CareUnitRead:
    care_unit = _get_care_unit(session, care_unit_id)
    layout = session.exec(
        select(CareUnitLayoutPosition).where(CareUnitLayoutPosition.care_unit_id == care_unit.id)
    ).first()
    before_state = _snapshot(layout, LAYOUT_FIELDS) if layout else None
    if layout is None:
        layout = CareUnitLayoutPosition(care_unit_id=care_unit.id, **payload.model_dump())
        action = "create"
    else:
        for field, value in payload.model_dump().items():
            setattr(layout, field, value)
        layout.updated_at = utc_now()
        action = "update"
    session.add(layout)
    session.flush()
    record_audit(
        session,
        action=action,
        actor_user_id=actor_user_id,
        entity_type="care_unit_layout_position",
        entity_id=layout.id,
        before_state=before_state,
        after_state=_snapshot(layout, LAYOUT_FIELDS),
    )
    session.commit()
    session.refresh(care_unit)
    return _read_care_unit(session, care_unit)


def _record_purge(
    session: Session,
    *,
    entity_type: str,
    entity_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    before_state: dict[str, Any],
    reason: str,
) -> None:
    record_audit(
        session,
        action="delete",
        actor_user_id=actor_user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        before_state=before_state,
        after_state={"deleted": True, "reason": reason},
    )


def purge_care_unit(
    session: Session,
    care_unit_id: uuid.UUID,
    payload: PurgeRequest,
    actor_user_id: uuid.UUID,
) -> None:
    care_unit = _get_care_unit(session, care_unit_id)
    if care_unit.is_active:
        raise _conflict(
            "La ubicación debe estar inactiva antes de eliminarla definitivamente."
        )
    before_state = _snapshot(care_unit, CARE_UNIT_FIELDS)
    layout = session.exec(
        select(CareUnitLayoutPosition).where(CareUnitLayoutPosition.care_unit_id == care_unit.id)
    ).first()
    if layout is not None:
        session.delete(layout)
    session.delete(care_unit)
    _record_purge(
        session,
        entity_type="care_unit",
        entity_id=care_unit.id,
        actor_user_id=actor_user_id,
        before_state=before_state,
        reason=payload.reason,
    )
    session.commit()


def purge_room(
    session: Session,
    room_id: uuid.UUID,
    payload: PurgeRequest,
    actor_user_id: uuid.UUID,
) -> None:
    room = _get_room(session, room_id)
    if room.is_active:
        raise _conflict("La sala debe estar inactiva antes de eliminarla definitivamente.")
    if session.exec(select(CareUnit).where(CareUnit.room_id == room.id)).first() is not None:
        raise _conflict(
            "No se puede eliminar una sala que todavía contiene ubicaciones."
        )
    before_state = _snapshot(room, ROOM_FIELDS)
    session.delete(room)
    _record_purge(
        session,
        entity_type="room",
        entity_id=room.id,
        actor_user_id=actor_user_id,
        before_state=before_state,
        reason=payload.reason,
    )
    session.commit()


def purge_service(
    session: Session,
    service_id: uuid.UUID,
    payload: PurgeRequest,
    actor_user_id: uuid.UUID,
) -> None:
    service = _get_service(session, service_id)
    if service.is_active:
        raise _conflict("El servicio debe estar inactivo antes de eliminarlo definitivamente.")
    if session.exec(select(Room).where(Room.service_id == service.id)).first() is not None:
        raise _conflict("No se puede eliminar un servicio que todavía contiene salas.")
    if session.exec(
        select(NutritionistServiceAssignment).where(
            NutritionistServiceAssignment.service_id == service.id
        )
    ).first() is not None:
        raise _conflict(
            "No se puede eliminar un servicio con asignaciones de nutricionistas."
        )
    before_state = _snapshot(service, SERVICE_FIELDS)
    session.delete(service)
    _record_purge(
        session,
        entity_type="service",
        entity_id=service.id,
        actor_user_id=actor_user_id,
        before_state=before_state,
        reason=payload.reason,
    )
    session.commit()
