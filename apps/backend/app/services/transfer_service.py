import uuid
from datetime import date
from typing import Iterable

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import aliased
from sqlmodel import Session, select

from app.models.admission import Admission
from app.models.care_unit import CareUnit
from app.models.common import utc_now
from app.models.hospital_service import HospitalService
from app.models.nutritionist_service_assignment import NutritionistServiceAssignment
from app.models.patient import Patient
from app.models.patient_location_history import PatientLocationHistory
from app.models.patient_transfer_request import (
    OPEN_TRANSFER_STATUSES,
    PatientTransferRequest,
)
from app.models.patient_transfer_request_status_history import (
    PatientTransferRequestStatusHistory,
)
from app.models.room import Room
from app.schemas.transfer import (
    TransferAccept,
    TransferAdmissionSummary,
    TransferAssignBed,
    TransferLocationSummary,
    TransferPatientSummary,
    TransferRequestCreate,
    TransferRequestListResponse,
    TransferRequestRead,
    TransferServiceSummary,
    TransferStatus,
    TransferStatusHistoryRead,
)
from app.services.audit_service import record_audit

TERMINAL_TRANSFER_STATUSES = {
    "assigned_to_bed", "rejected", "returned", "cancelled"
}


def _not_found(name: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"{name} no encontrado.")


def _conflict(detail: str) -> HTTPException:
    return HTTPException(status_code=409, detail=detail)


def _commit_or_conflict(session: Session) -> None:
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise _conflict(
            "La solicitud, su estado o la disponibilidad de la cama cambió concurrentemente; refresque los datos."
        ) from exc


def _flush_or_conflict(session: Session) -> None:
    try:
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise _conflict(
            "La solicitud, su secuencia o la ocupación cambió concurrentemente; refresque los datos."
        ) from exc


def _display_name(patient: Patient) -> str:
    parts = [patient.given_names, patient.first_surname, patient.second_surname]
    available = " ".join(part.strip() for part in parts if part and part.strip())
    if patient.identity_status == "unidentified":
        return f"{available} · {patient.temporary_identifier}" if available else f"Paciente NN · {patient.temporary_identifier}"
    if patient.identity_status == "provisional" and not available:
        return f"Paciente provisorio · {patient.temporary_identifier}"
    return available or "Paciente sin nombre registrado"


def _age_years(birth_date: date | None) -> int | None:
    if birth_date is None:
        return None
    today = date.today()
    return today.year - birth_date.year - (
        (today.month, today.day) < (birth_date.month, birth_date.day)
    )


def _is_coverage(
    session: Session,
    actor_user_id: uuid.UUID,
    actor_roles: Iterable[str],
    service_id: uuid.UUID,
) -> bool:
    roles = set(actor_roles)
    if "jefatura" in roles or "nutricionista" not in roles:
        return False
    assignment = session.exec(
        select(NutritionistServiceAssignment.id).where(
            NutritionistServiceAssignment.nutritionist_user_id == actor_user_id,
            NutritionistServiceAssignment.service_id == service_id,
            NutritionistServiceAssignment.is_active.is_(True),
        )
    ).first()
    return assignment is None


def _get_admission(session: Session, admission_id: uuid.UUID) -> tuple[Admission, Patient]:
    row = session.exec(
        select(Admission, Patient)
        .join(Patient, Patient.id == Admission.patient_id)
        .where(Admission.id == admission_id)
        .with_for_update()
    ).first()
    if row is None:
        raise _not_found("Hospitalización")
    admission, patient = row
    if admission.status != "active":
        raise _conflict("La hospitalización debe estar activa para solicitar un traslado.")
    if not patient.is_active or patient.merged_into_patient_id is not None:
        raise _conflict("La ficha del paciente está inactiva o fusionada.")
    return admission, patient


def _current_location_row(
    session: Session, admission_id: uuid.UUID
) -> tuple[PatientLocationHistory, CareUnit, Room, HospitalService]:
    row = session.exec(
        select(PatientLocationHistory, CareUnit, Room, HospitalService)
        .join(CareUnit, CareUnit.id == PatientLocationHistory.care_unit_id)
        .join(Room, Room.id == CareUnit.room_id)
        .join(HospitalService, HospitalService.id == Room.service_id)
        .where(
            PatientLocationHistory.admission_id == admission_id,
            PatientLocationHistory.ended_at.is_(None),
        )
        .with_for_update()
    ).first()
    if row is None:
        raise _conflict(
            "La hospitalización no tiene una cama vigente; asigne una ubicación inicial primero."
        )
    _, bed, room, service = row
    if (
        not bed.is_active
        or bed.unit_type != "bed"
        or not room.is_active
        or not service.is_active
    ):
        raise _conflict("La ubicación vigente debe ser una cama activa en una estructura activa.")
    return row


def _get_destination_service(session: Session, service_id: uuid.UUID) -> HospitalService:
    service = session.exec(
        select(HospitalService).where(HospitalService.id == service_id).with_for_update()
    ).first()
    if service is None:
        raise _not_found("Servicio destino")
    if not service.is_active:
        raise _conflict("El servicio destino se encuentra inactivo.")
    return service


def _get_destination_bed(
    session: Session,
    care_unit_id: uuid.UUID,
    destination_service_id: uuid.UUID,
    admission_id: uuid.UUID,
) -> tuple[CareUnit, Room]:
    row = session.exec(
        select(CareUnit, Room)
        .join(Room, Room.id == CareUnit.room_id)
        .where(CareUnit.id == care_unit_id)
        .with_for_update()
    ).first()
    if row is None:
        raise _not_found("Cama destino")
    bed, room = row
    if room.service_id != destination_service_id:
        raise _conflict("La cama seleccionada no pertenece al servicio destino.")
    if not bed.is_active or bed.unit_type != "bed" or not room.is_active:
        raise _conflict("La cama destino debe estar activa, pertenecer a una sala activa y ser de tipo cama.")
    occupancy = session.exec(
        select(PatientLocationHistory).where(
            PatientLocationHistory.care_unit_id == bed.id,
            PatientLocationHistory.ended_at.is_(None),
        ).with_for_update()
    ).first()
    if occupancy is not None and occupancy.admission_id != admission_id:
        raise _conflict("La cama destino fue ocupada; refresque la disponibilidad.")
    return bed, room


def _get_transfer(
    session: Session, transfer_request_id: uuid.UUID, *, for_update: bool = True
) -> PatientTransferRequest:
    statement = select(PatientTransferRequest).where(
        PatientTransferRequest.id == transfer_request_id
    )
    if for_update:
        statement = statement.with_for_update()
    transfer = session.exec(statement).first()
    if transfer is None:
        raise _not_found("Solicitud de traslado")
    return transfer


def _lock_transfer_and_admission(
    session: Session, transfer_request_id: uuid.UUID
) -> tuple[PatientTransferRequest, Admission, Patient]:
    snapshot = _get_transfer(session, transfer_request_id, for_update=False)
    admission, patient = _get_admission(session, snapshot.admission_id)
    transfer = _get_transfer(session, transfer_request_id, for_update=True)
    if transfer.admission_id != admission.id:
        raise _conflict("La solicitud cambió concurrentemente; refresque los datos.")
    return transfer, admission, patient


def _record_transition(
    session: Session,
    transfer: PatientTransferRequest,
    *,
    to_status: str,
    actor_user_id: uuid.UUID,
    reason: str | None,
    is_coverage: bool,
    changed_at=None,
) -> None:
    from_status = None if to_status == "requested" and transfer.status == "requested" else transfer.status
    last_sequence = session.exec(
        select(func.max(PatientTransferRequestStatusHistory.sequence_number)).where(
            PatientTransferRequestStatusHistory.transfer_request_id == transfer.id
        )
    ).one()
    sequence = (last_sequence or 0) + 1
    moment = changed_at or utc_now()
    session.add(
        PatientTransferRequestStatusHistory(
            transfer_request_id=transfer.id,
            sequence_number=sequence,
            from_status=from_status,
            to_status=to_status,
            reason=reason,
            changed_by_user_id=actor_user_id,
            changed_at=moment,
            is_coverage=is_coverage,
        )
    )
    before = {"status": transfer.status, "destination_care_unit_id": str(transfer.destination_care_unit_id) if transfer.destination_care_unit_id else None}
    transfer.status = to_status
    transfer.updated_at = moment
    if to_status in TERMINAL_TRANSFER_STATUSES:
        transfer.completed_at = moment
    session.add(transfer)
    record_audit(
        session,
        action=f"transfer_{to_status}",
        actor_user_id=actor_user_id,
        entity_type="patient_transfer_request",
        entity_id=transfer.id,
        before_state=before,
        after_state={
            "status": to_status,
            "reason": reason,
            "is_coverage": is_coverage,
            "destination_care_unit_id": str(transfer.destination_care_unit_id) if transfer.destination_care_unit_id else None,
        },
        admission_id=transfer.admission_id,
    )
    _flush_or_conflict(session)


def _move_to_destination(
    session: Session,
    transfer: PatientTransferRequest,
    destination_care_unit_id: uuid.UUID,
    actor_user_id: uuid.UUID,
    reason: str | None,
) -> None:
    admission, _ = _get_admission(session, transfer.admission_id)
    current, _, _, current_service = _current_location_row(session, admission.id)
    if current_service.id != transfer.origin_service_id:
        raise _conflict("La ubicación vigente ya no pertenece al servicio de origen de la solicitud.")
    bed, _ = _get_destination_bed(
        session, destination_care_unit_id, transfer.destination_service_id, admission.id
    )
    if current.care_unit_id == bed.id:
        raise _conflict("La cama destino coincide con la ubicación vigente.")
    now = utc_now()
    before = {
        "id": str(current.id),
        "care_unit_id": str(current.care_unit_id),
        "ended_at": None,
    }
    current.ended_at = now
    current.ended_by_user_id = actor_user_id
    session.add(current)
    _flush_or_conflict(session)
    record_audit(
        session,
        action="location_closed_for_transfer_request",
        actor_user_id=actor_user_id,
        entity_type="patient_location",
        entity_id=current.id,
        before_state=before,
        after_state={**before, "ended_at": now.isoformat()},
        admission_id=admission.id,
    )
    new_location = PatientLocationHistory(
        admission_id=admission.id,
        care_unit_id=bed.id,
        started_at=now,
        reason=reason or f"Traslado {transfer.id} completado.",
        assigned_by_user_id=actor_user_id,
    )
    session.add(new_location)
    _flush_or_conflict(session)
    record_audit(
        session,
        action="location_assigned_from_transfer_request",
        actor_user_id=actor_user_id,
        entity_type="patient_location",
        entity_id=new_location.id,
        before_state=before,
        after_state={
            "id": str(new_location.id),
            "care_unit_id": str(bed.id),
            "started_at": now.isoformat(),
        },
        admission_id=admission.id,
    )
    transfer.destination_care_unit_id = bed.id
    session.add(transfer)


def create_transfer_request(
    session: Session,
    payload: TransferRequestCreate,
    actor_user_id: uuid.UUID,
    actor_roles: Iterable[str],
) -> TransferRequestRead:
    admission, _ = _get_admission(session, payload.admission_id)
    current, _, _, origin_service = _current_location_row(session, admission.id)
    destination = _get_destination_service(session, payload.destination_service_id)
    if origin_service.id == destination.id:
        raise _conflict(
            "Los cambios dentro del mismo servicio deben usar la operación de ubicación existente."
        )
    existing = session.exec(
        select(PatientTransferRequest.id).where(
            PatientTransferRequest.admission_id == admission.id,
            PatientTransferRequest.status.in_(OPEN_TRANSFER_STATUSES),
        ).with_for_update()
    ).first()
    if existing is not None:
        raise _conflict("La hospitalización ya tiene un traslado abierto.")
    now = utc_now()
    coverage = _is_coverage(session, actor_user_id, actor_roles, origin_service.id)
    transfer = PatientTransferRequest(
        admission_id=admission.id,
        origin_service_id=origin_service.id,
        destination_service_id=destination.id,
        origin_care_unit_id=current.care_unit_id,
        transfer_mode=payload.transfer_mode.value,
        request_reason=payload.reason,
        requested_by_user_id=actor_user_id,
        requested_at=now,
        created_at=now,
        updated_at=now,
    )
    session.add(transfer)
    try:
        _flush_or_conflict(session)
        _record_transition(
            session, transfer, to_status="requested", actor_user_id=actor_user_id,
            reason=payload.reason, is_coverage=coverage, changed_at=now,
        )
        _record_transition(
            session, transfer, to_status="pending_reception", actor_user_id=actor_user_id,
            reason="Envío automático a recepción.", is_coverage=coverage, changed_at=now,
        )
        if payload.transfer_mode.value == "direct":
            _record_transition(
                session, transfer, to_status="accepted", actor_user_id=actor_user_id,
                reason="Aceptación automática de traslado directo.", is_coverage=coverage, changed_at=now,
            )
            _move_to_destination(
                session, transfer, payload.destination_care_unit_id, actor_user_id, payload.reason
            )
            _record_transition(
                session, transfer, to_status="assigned_to_bed", actor_user_id=actor_user_id,
                reason="Cama destino coordinada y asignada.", is_coverage=coverage, changed_at=now,
            )
        _commit_or_conflict(session)
    except HTTPException:
        session.rollback()
        raise
    return get_transfer_request(session, transfer.id)


def _ensure_status(transfer: PatientTransferRequest, expected: str) -> None:
    if transfer.status != expected:
        raise _conflict(
            f"La solicitud ya no está en {expected}; su estado vigente es {transfer.status}."
        )


def accept_transfer_request(
    session: Session,
    transfer_request_id: uuid.UUID,
    payload: TransferAccept,
    actor_user_id: uuid.UUID,
    actor_roles: Iterable[str],
) -> TransferRequestRead:
    transfer, _, _ = _lock_transfer_and_admission(session, transfer_request_id)
    _ensure_status(transfer, "pending_reception")
    coverage = _is_coverage(session, actor_user_id, actor_roles, transfer.destination_service_id)
    _record_transition(
        session, transfer, to_status="accepted", actor_user_id=actor_user_id,
        reason=payload.observation or "Solicitud aceptada.", is_coverage=coverage,
    )
    if payload.destination_care_unit_id is None:
        _record_transition(
            session, transfer, to_status="pending_bed", actor_user_id=actor_user_id,
            reason=payload.observation or "Aceptada, pendiente de cama.", is_coverage=coverage,
        )
    else:
        _move_to_destination(
            session, transfer, payload.destination_care_unit_id, actor_user_id, payload.observation
        )
        _record_transition(
            session, transfer, to_status="assigned_to_bed", actor_user_id=actor_user_id,
            reason=payload.observation or "Aceptada y asignada a cama.", is_coverage=coverage,
        )
    _commit_or_conflict(session)
    return get_transfer_request(session, transfer.id)


def assign_transfer_bed(
    session: Session,
    transfer_request_id: uuid.UUID,
    payload: TransferAssignBed,
    actor_user_id: uuid.UUID,
    actor_roles: Iterable[str],
) -> TransferRequestRead:
    transfer, _, _ = _lock_transfer_and_admission(session, transfer_request_id)
    _ensure_status(transfer, "pending_bed")
    coverage = _is_coverage(session, actor_user_id, actor_roles, transfer.destination_service_id)
    _move_to_destination(
        session, transfer, payload.destination_care_unit_id, actor_user_id, payload.observation
    )
    _record_transition(
        session, transfer, to_status="assigned_to_bed", actor_user_id=actor_user_id,
        reason=payload.observation or "Cama destino asignada.", is_coverage=coverage,
    )
    _commit_or_conflict(session)
    return get_transfer_request(session, transfer.id)


def terminal_transition(
    session: Session,
    transfer_request_id: uuid.UUID,
    *,
    expected_status: str,
    next_status: str,
    reason: str,
    actor_user_id: uuid.UUID,
    actor_roles: Iterable[str],
    action_service: str,
) -> TransferRequestRead:
    transfer, _, _ = _lock_transfer_and_admission(session, transfer_request_id)
    _ensure_status(transfer, expected_status)
    service_id = (
        transfer.destination_service_id if action_service == "destination" else transfer.origin_service_id
    )
    coverage = _is_coverage(session, actor_user_id, actor_roles, service_id)
    _record_transition(
        session, transfer, to_status=next_status, actor_user_id=actor_user_id,
        reason=reason, is_coverage=coverage,
    )
    _commit_or_conflict(session)
    return get_transfer_request(session, transfer.id)


def cancel_transfer_request(
    session: Session,
    transfer_request_id: uuid.UUID,
    reason: str,
    actor_user_id: uuid.UUID,
    actor_roles: Iterable[str],
) -> TransferRequestRead:
    transfer, _, _ = _lock_transfer_and_admission(session, transfer_request_id)
    if transfer.status not in {"pending_reception", "pending_bed"}:
        raise _conflict("Sólo se puede cancelar una solicitud pendiente de recepción o de cama.")
    coverage = _is_coverage(session, actor_user_id, actor_roles, transfer.origin_service_id)
    _record_transition(
        session, transfer, to_status="cancelled", actor_user_id=actor_user_id,
        reason=reason, is_coverage=coverage,
    )
    _commit_or_conflict(session)
    return get_transfer_request(session, transfer.id)


def cancel_open_transfer_on_admission_end(
    session: Session,
    admission_id: uuid.UUID,
    *,
    reason: str,
    actor_user_id: uuid.UUID,
) -> None:
    transfer = session.exec(
        select(PatientTransferRequest).where(
            PatientTransferRequest.admission_id == admission_id,
            PatientTransferRequest.status.in_(OPEN_TRANSFER_STATUSES),
        ).with_for_update()
    ).first()
    if transfer is not None:
        _record_transition(
            session, transfer, to_status="cancelled", actor_user_id=actor_user_id,
            reason=f"Término de hospitalización: {reason}", is_coverage=False,
        )


def _location_summary(
    location: PatientLocationHistory, bed: CareUnit, room: Room, service: HospitalService
) -> TransferLocationSummary:
    return TransferLocationSummary(
        care_unit_id=bed.id,
        care_unit_code=bed.code,
        care_unit_label=bed.label,
        room_id=room.id,
        room_code=room.code,
        room_name=room.name,
        service_id=service.id,
        service_code=service.code,
        service_name=service.name,
    )


def _read_many(
    session: Session,
    transfers: list[PatientTransferRequest],
    *,
    include_history: bool,
) -> list[TransferRequestRead]:
    if not transfers:
        return []
    result: list[TransferRequestRead] = []
    OriginService = aliased(HospitalService)
    DestinationService = aliased(HospitalService)
    for transfer in transfers:
        core = session.exec(
            select(Admission, Patient, OriginService, DestinationService)
            .join(Patient, Patient.id == Admission.patient_id)
            .join(OriginService, OriginService.id == transfer.origin_service_id)
            .join(DestinationService, DestinationService.id == transfer.destination_service_id)
            .where(Admission.id == transfer.admission_id)
        ).first()
        admission, patient, origin, destination = core
        current_row = session.exec(
            select(PatientLocationHistory, CareUnit, Room, HospitalService)
            .join(CareUnit, CareUnit.id == PatientLocationHistory.care_unit_id)
            .join(Room, Room.id == CareUnit.room_id)
            .join(HospitalService, HospitalService.id == Room.service_id)
            .where(
                PatientLocationHistory.admission_id == admission.id,
                PatientLocationHistory.ended_at.is_(None),
            )
        ).first()
        histories = list(session.exec(
            select(PatientTransferRequestStatusHistory)
            .where(PatientTransferRequestStatusHistory.transfer_request_id == transfer.id)
            .order_by(PatientTransferRequestStatusHistory.sequence_number)
        ).all())
        result.append(
            TransferRequestRead(
                id=transfer.id,
                admission_id=transfer.admission_id,
                transfer_mode=transfer.transfer_mode,
                status=transfer.status,
                request_reason=transfer.request_reason,
                requested_by_user_id=transfer.requested_by_user_id,
                requested_at=transfer.requested_at,
                completed_at=transfer.completed_at,
                created_at=transfer.created_at,
                updated_at=transfer.updated_at,
                origin_service=TransferServiceSummary(id=origin.id, code=origin.code, name=origin.name),
                destination_service=TransferServiceSummary(id=destination.id, code=destination.code, name=destination.name),
                origin_care_unit_id=transfer.origin_care_unit_id,
                destination_care_unit_id=transfer.destination_care_unit_id,
                current_origin_location=_location_summary(*current_row) if current_row else None,
                patient=TransferPatientSummary(
                    id=patient.id,
                    display_name=_display_name(patient),
                    identity_status=patient.identity_status,
                    age_years=_age_years(patient.date_of_birth),
                    age_is_estimated=patient.date_of_birth_is_estimated,
                ),
                admission=TransferAdmissionSummary(
                    id=admission.id,
                    admission_identifier=admission.admission_identifier,
                    status=admission.status,
                    admitted_at=admission.admitted_at,
                ),
                has_coverage_support=any(history.is_coverage for history in histories),
                status_history=(
                    [TransferStatusHistoryRead.model_validate(history) for history in histories]
                    if include_history else []
                ),
            )
        )
    return result


def get_transfer_request(session: Session, transfer_request_id: uuid.UUID) -> TransferRequestRead:
    transfer = _get_transfer(session, transfer_request_id, for_update=False)
    return _read_many(session, [transfer], include_history=True)[0]


def list_reception_tray(
    session: Session,
    *,
    service_id: uuid.UUID,
    statuses: list[TransferStatus] | None,
    page: int,
    page_size: int,
) -> TransferRequestListResponse:
    _get_destination_service(session, service_id)
    selected = [item.value for item in statuses] if statuses else ["pending_reception", "pending_bed"]
    filters = [
        PatientTransferRequest.destination_service_id == service_id,
        PatientTransferRequest.status.in_(selected),
    ]
    total = session.exec(
        select(func.count()).select_from(PatientTransferRequest).where(*filters)
    ).one()
    transfers = list(session.exec(
        select(PatientTransferRequest)
        .where(*filters)
        .order_by(PatientTransferRequest.requested_at, PatientTransferRequest.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all())
    return TransferRequestListResponse(
        items=_read_many(session, transfers, include_history=False),
        total=total,
        page=page,
        page_size=page_size,
    )


def list_admission_transfers(
    session: Session,
    *,
    admission_id: uuid.UUID,
    page: int,
    page_size: int,
) -> TransferRequestListResponse:
    if session.get(Admission, admission_id) is None:
        raise _not_found("Hospitalización")
    total = session.exec(
        select(func.count()).select_from(PatientTransferRequest).where(
            PatientTransferRequest.admission_id == admission_id
        )
    ).one()
    transfers = list(session.exec(
        select(PatientTransferRequest)
        .where(PatientTransferRequest.admission_id == admission_id)
        .order_by(PatientTransferRequest.requested_at.desc(), PatientTransferRequest.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all())
    return TransferRequestListResponse(
        items=_read_many(session, transfers, include_history=False),
        total=total,
        page=page,
        page_size=page_size,
    )
