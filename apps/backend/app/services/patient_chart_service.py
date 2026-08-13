import uuid
from datetime import date, datetime, timezone

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models.admission import Admission
from app.models.admission_status_history import AdmissionStatusHistory
from app.models.care_unit import CareUnit
from app.models.common import utc_now
from app.models.hospital_service import HospitalService
from app.models.patient import Patient
from app.models.patient_location_history import PatientLocationHistory
from app.models.patient_transfer_request import OPEN_TRANSFER_STATUSES, PatientTransferRequest
from app.models.patient_transfer_request_status_history import (
    PatientTransferRequestStatusHistory,
)
from app.models.room import Room
from app.schemas.patient import (
    OperationalTimelineEvent,
    OperationalTimelineLocation,
    OperationalTimelineResponse,
    PatientChartAdmission,
    PatientChartAge,
    PatientChartIdentity,
    PatientChartLocation,
    PatientChartSummary,
    PatientChartTransfer,
)


def _not_found(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _age(birth_date: date | None, reference_date: date, estimated: bool) -> PatientChartAge:
    if birth_date is None:
        return PatientChartAge(
            value=None,
            unit=None,
            is_estimated=estimated,
            reference_date=reference_date,
            display="Edad desconocida",
        )
    days = max((reference_date - birth_date).days, 0)
    if days < 28:
        value, unit, noun = days, "days", "día" if days == 1 else "días"
    elif days < 730:
        value = max(1, int(days / 30.4375))
        unit, noun = "months", "mes" if value == 1 else "meses"
    else:
        value = reference_date.year - birth_date.year
        if (reference_date.month, reference_date.day) < (birth_date.month, birth_date.day):
            value -= 1
        value = max(value, 0)
        unit, noun = "years", "año" if value == 1 else "años"
    suffix = " · estimada" if estimated else ""
    return PatientChartAge(
        value=value,
        unit=unit,
        is_estimated=estimated,
        reference_date=reference_date,
        display=f"{value} {noun}{suffix}",
    )


def _display_name(patient: Patient) -> str:
    name = " ".join(
        value
        for value in (patient.given_names, patient.first_surname, patient.second_surname)
        if value
    )
    if name:
        return name
    if patient.identity_status == "unidentified":
        return f"Paciente NN · {patient.temporary_identifier}"
    return f"Ficha provisoria · {patient.temporary_identifier}"


def _location_rows(
    session: Session, admission_id: uuid.UUID
) -> list[tuple[PatientLocationHistory, CareUnit, Room, HospitalService]]:
    return list(
        session.exec(
            select(PatientLocationHistory, CareUnit, Room, HospitalService)
            .join(CareUnit, CareUnit.id == PatientLocationHistory.care_unit_id)
            .join(Room, Room.id == CareUnit.room_id)
            .join(HospitalService, HospitalService.id == Room.service_id)
            .where(PatientLocationHistory.admission_id == admission_id)
            .order_by(PatientLocationHistory.started_at, PatientLocationHistory.id)
        ).all()
    )


def _chart_location(
    row: tuple[PatientLocationHistory, CareUnit, Room, HospitalService] | None,
    *,
    admission_active: bool,
) -> PatientChartLocation | None:
    if row is None:
        return None
    location, care_unit, room, service = row
    return PatientChartLocation(
        id=location.id,
        care_unit_id=care_unit.id,
        care_unit_code=care_unit.code,
        care_unit_label=care_unit.label,
        room_id=room.id,
        room_code=room.code,
        room_name=room.name,
        service_id=service.id,
        service_code=service.code,
        service_name=service.name,
        started_at=location.started_at,
        ended_at=location.ended_at,
        reason=location.reason,
        is_current=admission_active and location.ended_at is None,
    )


def _timeline_location(
    row: tuple[CareUnit, Room, HospitalService] | None,
) -> OperationalTimelineLocation | None:
    if row is None:
        return None
    care_unit, room, service = row
    return OperationalTimelineLocation(
        care_unit_id=care_unit.id,
        care_unit_code=care_unit.code,
        care_unit_label=care_unit.label,
        room_id=room.id,
        room_code=room.code,
        room_name=room.name,
        service_id=service.id,
        service_code=service.code,
        service_name=service.name,
    )


def _service_location(service: HospitalService) -> OperationalTimelineLocation:
    return OperationalTimelineLocation(
        service_id=service.id,
        service_code=service.code,
        service_name=service.name,
    )


def _bed_location(
    session: Session, care_unit_id: uuid.UUID | None
) -> OperationalTimelineLocation | None:
    if care_unit_id is None:
        return None
    row = session.exec(
        select(CareUnit, Room, HospitalService)
        .join(Room, Room.id == CareUnit.room_id)
        .join(HospitalService, HospitalService.id == Room.service_id)
        .where(CareUnit.id == care_unit_id)
    ).first()
    return _timeline_location(row)


def _open_transfer(
    session: Session, admission_id: uuid.UUID
) -> PatientChartTransfer | None:
    row = session.exec(
        select(PatientTransferRequest, HospitalService)
        .join(HospitalService, HospitalService.id == PatientTransferRequest.destination_service_id)
        .where(
            PatientTransferRequest.admission_id == admission_id,
            PatientTransferRequest.status.in_(OPEN_TRANSFER_STATUSES),
        )
    ).first()
    if row is None:
        return None
    transfer, destination = row
    origin = session.get(HospitalService, transfer.origin_service_id)
    if origin is None:
        return None
    return PatientChartTransfer(
        id=transfer.id,
        status=transfer.status,
        transfer_mode=transfer.transfer_mode,
        requested_at=transfer.requested_at,
        request_reason=transfer.request_reason,
        origin_service_id=origin.id,
        origin_service_code=origin.code,
        origin_service_name=origin.name,
        destination_service_id=destination.id,
        destination_service_code=destination.code,
        destination_service_name=destination.name,
    )


def _admission_projection(
    session: Session, admission: Admission, patient: Patient
) -> PatientChartAdmission:
    rows = _location_rows(session, admission.id)
    active = admission.status == "active"
    selected_row = next((row for row in reversed(rows) if row[0].ended_at is None), None)
    if selected_row is None and rows:
        selected_row = rows[-1]
    location = _chart_location(selected_row, admission_active=active)
    end = _as_utc(admission.ended_at) if admission.ended_at else utc_now()
    start = _as_utc(admission.admitted_at)
    duration_days = max((end.date() - start.date()).days, 0)
    bed_status = "occupied" if location and location.is_current else "released" if location else "unassigned"
    return PatientChartAdmission(
        id=admission.id,
        admission_identifier=admission.admission_identifier,
        status=admission.status,
        admitted_at=admission.admitted_at,
        ended_at=admission.ended_at,
        end_reason=admission.end_reason,
        duration_days=duration_days,
        is_historical=not active,
        location=location,
        bed_status=bed_status,
        open_transfer=_open_transfer(session, admission.id) if active else None,
        age_at_admission=_age(
            patient.date_of_birth,
            start.date(),
            patient.date_of_birth_is_estimated,
        ),
    )


TRANSFER_TITLES = {
    "requested": "Traslado solicitado",
    "pending_reception": "Pendiente de recepción",
    "accepted": "Traslado aceptado",
    "pending_bed": "Pendiente de cama destino",
    "assigned_to_bed": "Cama destino asignada",
    "rejected": "Traslado rechazado",
    "returned": "Traslado devuelto",
    "cancelled": "Traslado cancelado",
}


def _timeline_events(session: Session, admission: Admission) -> list[OperationalTimelineEvent]:
    events: list[OperationalTimelineEvent] = []
    status_rows = list(
        session.exec(
            select(AdmissionStatusHistory)
            .where(AdmissionStatusHistory.admission_id == admission.id)
            .order_by(AdmissionStatusHistory.changed_at, AdmissionStatusHistory.id)
        ).all()
    )
    for history in status_rows:
        initial = history.from_status is None and history.to_status == "active"
        title = "Inicio de hospitalización" if initial else "Término de hospitalización"
        description = (
            f"Se inició el episodio {admission.admission_identifier}."
            if initial
            else f"El episodio quedó en estado {history.to_status}."
        )
        events.append(
            OperationalTimelineEvent(
                id=f"admission-status:{history.id}",
                event_type="admission_started" if initial else "admission_ended",
                occurred_at=history.changed_at,
                title=title,
                description=description,
                reason=history.reason,
                status=history.to_status,
            )
        )

    previous: OperationalTimelineLocation | None = None
    for index, (location, care_unit, room, service) in enumerate(_location_rows(session, admission.id)):
        destination = _timeline_location((care_unit, room, service))
        label = care_unit.label or care_unit.code
        events.append(
            OperationalTimelineEvent(
                id=f"location:{location.id}",
                event_type="initial_bed_assignment" if index == 0 else "bed_changed",
                occurred_at=location.started_at,
                title="Asignación inicial de cama" if index == 0 else "Cambio de ubicación",
                description=f"Ubicación asignada: {service.name} · {room.name} · {label}.",
                reason=location.reason,
                origin=previous,
                destination=destination,
            )
        )
        previous = destination

    transfers = list(
        session.exec(
            select(PatientTransferRequest)
            .where(PatientTransferRequest.admission_id == admission.id)
            .order_by(PatientTransferRequest.requested_at, PatientTransferRequest.id)
        ).all()
    )
    for transfer in transfers:
        origin_service = session.get(HospitalService, transfer.origin_service_id)
        destination_service = session.get(HospitalService, transfer.destination_service_id)
        origin = _bed_location(session, transfer.origin_care_unit_id)
        destination = _bed_location(session, transfer.destination_care_unit_id)
        if origin is None and origin_service is not None:
            origin = _service_location(origin_service)
        if destination is None and destination_service is not None:
            destination = _service_location(destination_service)
        histories = list(
            session.exec(
                select(PatientTransferRequestStatusHistory)
                .where(
                    PatientTransferRequestStatusHistory.transfer_request_id == transfer.id
                )
                .order_by(
                    PatientTransferRequestStatusHistory.sequence_number,
                    PatientTransferRequestStatusHistory.id,
                )
            ).all()
        )
        if not histories:
            events.append(
                OperationalTimelineEvent(
                    id=f"transfer:{transfer.id}",
                    event_type="transfer_requested",
                    occurred_at=transfer.requested_at,
                    title="Traslado solicitado",
                    description=(
                        f"Se solicitó traslado hacia {destination_service.name}."
                        if destination_service
                        else "Se solicitó un traslado."
                    ),
                    reason=transfer.request_reason,
                    status=transfer.status,
                    origin=origin,
                    destination=destination,
                )
            )
        for history in histories:
            title = TRANSFER_TITLES.get(history.to_status, "Estado de traslado actualizado")
            events.append(
                OperationalTimelineEvent(
                    id=f"transfer-status:{history.id}",
                    event_type=f"transfer_{history.to_status}",
                    occurred_at=history.changed_at,
                    title=title,
                    description=(
                        f"{title} hacia {destination_service.name}."
                        if destination_service
                        else f"{title}."
                    ),
                    reason=history.reason or (
                        transfer.request_reason if history.from_status is None else None
                    ),
                    status=history.to_status,
                    origin=origin,
                    destination=destination,
                )
            )

    events.sort(key=lambda event: (_as_utc(event.occurred_at), event.id), reverse=True)
    return events


def get_patient_chart_summary(
    session: Session,
    patient_id: uuid.UUID,
    admission_id: uuid.UUID | None = None,
) -> PatientChartSummary:
    patient = session.get(Patient, patient_id)
    if patient is None:
        raise _not_found("Paciente no encontrado.")
    admissions = list(
        session.exec(
            select(Admission)
            .where(Admission.patient_id == patient.id)
            .order_by(Admission.admitted_at.desc(), Admission.id)
        ).all()
    )
    selected: Admission | None = None
    if admission_id is not None:
        selected = session.get(Admission, admission_id)
        if selected is None or selected.patient_id != patient.id:
            raise _not_found("La hospitalización no pertenece al paciente.")
    elif admissions:
        selected = next((item for item in admissions if item.status == "active"), admissions[0])
    ordered = sorted(
        admissions,
        key=lambda item: (item.status == "active", _as_utc(item.admitted_at), str(item.id)),
        reverse=True,
    )
    projections = [_admission_projection(session, item, patient) for item in ordered]
    selected_projection = next(
        (item for item in projections if selected and item.id == selected.id), None
    )
    return PatientChartSummary(
        patient=PatientChartIdentity(
            id=patient.id,
            identity_status=patient.identity_status,
            display_name=_display_name(patient),
            temporary_identifier=patient.temporary_identifier,
            rut=patient.rut,
            hospital_identifier=patient.hospital_identifier,
            date_of_birth=patient.date_of_birth,
            date_of_birth_is_estimated=patient.date_of_birth_is_estimated,
            sex=patient.sex,
            phone=patient.phone,
            provisional_description=patient.provisional_description,
            merged_into_patient_id=patient.merged_into_patient_id,
            is_active=patient.is_active,
            current_age=_age(
                patient.date_of_birth,
                utc_now().date(),
                patient.date_of_birth_is_estimated,
            ),
        ),
        selected_admission=selected_projection,
        admissions=projections,
        total_admissions=len(projections),
        recent_operational_events=(
            _timeline_events(session, selected)[:5] if selected is not None else []
        ),
    )


def get_operational_timeline(
    session: Session,
    admission_id: uuid.UUID,
    *,
    page: int,
    page_size: int,
) -> OperationalTimelineResponse:
    admission = session.get(Admission, admission_id)
    if admission is None:
        raise _not_found("Hospitalización no encontrada.")
    events = _timeline_events(session, admission)
    start = (page - 1) * page_size
    return OperationalTimelineResponse(
        admission_id=admission.id,
        items=events[start : start + page_size],
        total=len(events),
        page=page,
        page_size=page_size,
    )
