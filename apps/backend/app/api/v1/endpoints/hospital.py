import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import (
    AuthenticatedSession,
    CurrentSession,
    DatabaseSession,
    require_roles_with_csrf,
)
from app.schemas.hospital import (
    CareUnitCreate,
    CareUnitRead,
    CareUnitUpdate,
    HospitalStructureResponse,
    LayoutUpsert,
    PurgeRequest,
    RoomCreate,
    RoomRead,
    RoomUpdate,
    ServiceCreate,
    ServiceRead,
    ServiceUpdate,
)
from app.services.hospital_structure_service import (
    create_care_unit,
    create_room,
    create_service,
    list_structure,
    purge_care_unit,
    purge_room,
    purge_service,
    update_care_unit,
    update_room,
    update_service,
    upsert_care_unit_layout,
)

router = APIRouter(prefix="/hospital", tags=["hospital"])
HospitalEditor = Annotated[
    CurrentSession,
    Depends(require_roles_with_csrf("jefatura", "administrador")),
]
HospitalAdministrator = Annotated[
    CurrentSession,
    Depends(require_roles_with_csrf("administrador")),
]


@router.get("/structure", response_model=HospitalStructureResponse)
def read_structure(
    _: AuthenticatedSession,
    session: DatabaseSession,
    include_inactive: bool = Query(default=False),
) -> HospitalStructureResponse:
    return list_structure(session, include_inactive)


@router.post("/services", response_model=ServiceRead, status_code=status.HTTP_201_CREATED)
def add_service(
    payload: ServiceCreate,
    current: HospitalEditor,
    session: DatabaseSession,
) -> ServiceRead:
    return create_service(session, payload, current.user.id)


@router.patch("/services/{service_id}", response_model=ServiceRead)
def edit_service(
    service_id: uuid.UUID,
    payload: ServiceUpdate,
    current: HospitalEditor,
    session: DatabaseSession,
) -> ServiceRead:
    return update_service(session, service_id, payload, current.user.id)


@router.post("/rooms", response_model=RoomRead, status_code=status.HTTP_201_CREATED)
def add_room(
    payload: RoomCreate,
    current: HospitalEditor,
    session: DatabaseSession,
) -> RoomRead:
    return create_room(session, payload, current.user.id)


@router.patch("/rooms/{room_id}", response_model=RoomRead)
def edit_room(
    room_id: uuid.UUID,
    payload: RoomUpdate,
    current: HospitalEditor,
    session: DatabaseSession,
) -> RoomRead:
    return update_room(session, room_id, payload, current.user.id)


@router.post("/care-units", response_model=CareUnitRead, status_code=status.HTTP_201_CREATED)
def add_care_unit(
    payload: CareUnitCreate,
    current: HospitalEditor,
    session: DatabaseSession,
) -> CareUnitRead:
    return create_care_unit(session, payload, current.user.id)


@router.patch("/care-units/{care_unit_id}", response_model=CareUnitRead)
def edit_care_unit(
    care_unit_id: uuid.UUID,
    payload: CareUnitUpdate,
    current: HospitalEditor,
    session: DatabaseSession,
) -> CareUnitRead:
    return update_care_unit(session, care_unit_id, payload, current.user.id)


@router.put("/care-units/{care_unit_id}/layout", response_model=CareUnitRead)
def place_care_unit(
    care_unit_id: uuid.UUID,
    payload: LayoutUpsert,
    current: HospitalEditor,
    session: DatabaseSession,
) -> CareUnitRead:
    return upsert_care_unit_layout(session, care_unit_id, payload, current.user.id)


@router.delete("/services/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_service(
    service_id: uuid.UUID,
    payload: PurgeRequest,
    current: HospitalAdministrator,
    session: DatabaseSession,
) -> None:
    purge_service(session, service_id, payload, current.user.id)


@router.delete("/rooms/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_room(
    room_id: uuid.UUID,
    payload: PurgeRequest,
    current: HospitalAdministrator,
    session: DatabaseSession,
) -> None:
    purge_room(session, room_id, payload, current.user.id)


@router.delete("/care-units/{care_unit_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_care_unit(
    care_unit_id: uuid.UUID,
    payload: PurgeRequest,
    current: HospitalAdministrator,
    session: DatabaseSession,
) -> None:
    purge_care_unit(session, care_unit_id, payload, current.user.id)
