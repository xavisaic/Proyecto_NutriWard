import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import CurrentSession, DatabaseSession, require_roles, require_roles_with_csrf
from app.schemas.transfer import (
    TransferAccept,
    TransferAssignBed,
    TransferRequestCreate,
    TransferRequestListResponse,
    TransferRequestRead,
    TransferRequiredReason,
    TransferStatus,
)
from app.services.transfer_service import (
    accept_transfer_request,
    assign_transfer_bed,
    cancel_transfer_request,
    create_transfer_request,
    get_transfer_request,
    list_admission_transfers,
    list_reception_tray,
    terminal_transition,
)

router = APIRouter(tags=["transfer-requests"])
TransferReader = Annotated[
    CurrentSession,
    Depends(require_roles("administrador", "jefatura", "nutricionista", "alimentacion")),
]
TransferEditor = Annotated[
    CurrentSession,
    Depends(require_roles_with_csrf("jefatura", "nutricionista")),
]


@router.post(
    "/transfer-requests",
    response_model=TransferRequestRead,
    status_code=status.HTTP_201_CREATED,
)
def create_transfer(
    payload: TransferRequestCreate,
    current: TransferEditor,
    session: DatabaseSession,
) -> TransferRequestRead:
    return create_transfer_request(session, payload, current.user.id, current.roles)


@router.get("/transfer-requests/reception-tray", response_model=TransferRequestListResponse)
def reception_tray(
    _: TransferReader,
    session: DatabaseSession,
    service_id: uuid.UUID,
    status_filter: list[TransferStatus] | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> TransferRequestListResponse:
    return list_reception_tray(
        session,
        service_id=service_id,
        statuses=status_filter,
        page=page,
        page_size=page_size,
    )


@router.get("/transfer-requests/{transfer_request_id}", response_model=TransferRequestRead)
def transfer_detail(
    transfer_request_id: uuid.UUID,
    _: TransferReader,
    session: DatabaseSession,
) -> TransferRequestRead:
    return get_transfer_request(session, transfer_request_id)


@router.get(
    "/admissions/{admission_id}/transfer-requests",
    response_model=TransferRequestListResponse,
)
def admission_transfer_history(
    admission_id: uuid.UUID,
    _: TransferReader,
    session: DatabaseSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> TransferRequestListResponse:
    return list_admission_transfers(
        session, admission_id=admission_id, page=page, page_size=page_size
    )


@router.post("/transfer-requests/{transfer_request_id}/accept", response_model=TransferRequestRead)
def accept_transfer(
    transfer_request_id: uuid.UUID,
    payload: TransferAccept,
    current: TransferEditor,
    session: DatabaseSession,
) -> TransferRequestRead:
    return accept_transfer_request(
        session, transfer_request_id, payload, current.user.id, current.roles
    )


@router.post("/transfer-requests/{transfer_request_id}/assign-bed", response_model=TransferRequestRead)
def assign_bed(
    transfer_request_id: uuid.UUID,
    payload: TransferAssignBed,
    current: TransferEditor,
    session: DatabaseSession,
) -> TransferRequestRead:
    return assign_transfer_bed(
        session, transfer_request_id, payload, current.user.id, current.roles
    )


@router.post("/transfer-requests/{transfer_request_id}/reject", response_model=TransferRequestRead)
def reject_transfer(
    transfer_request_id: uuid.UUID,
    payload: TransferRequiredReason,
    current: TransferEditor,
    session: DatabaseSession,
) -> TransferRequestRead:
    return terminal_transition(
        session,
        transfer_request_id,
        expected_status="pending_reception",
        next_status="rejected",
        reason=payload.reason,
        actor_user_id=current.user.id,
        actor_roles=current.roles,
        action_service="destination",
    )


@router.post("/transfer-requests/{transfer_request_id}/return", response_model=TransferRequestRead)
def return_transfer(
    transfer_request_id: uuid.UUID,
    payload: TransferRequiredReason,
    current: TransferEditor,
    session: DatabaseSession,
) -> TransferRequestRead:
    return terminal_transition(
        session,
        transfer_request_id,
        expected_status="pending_bed",
        next_status="returned",
        reason=payload.reason,
        actor_user_id=current.user.id,
        actor_roles=current.roles,
        action_service="destination",
    )


@router.post("/transfer-requests/{transfer_request_id}/cancel", response_model=TransferRequestRead)
def cancel_transfer(
    transfer_request_id: uuid.UUID,
    payload: TransferRequiredReason,
    current: TransferEditor,
    session: DatabaseSession,
) -> TransferRequestRead:
    return cancel_transfer_request(
        session, transfer_request_id, payload.reason, current.user.id, current.roles
    )
