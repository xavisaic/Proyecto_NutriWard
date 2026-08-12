import uuid
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import and_
from sqlalchemy.orm import aliased
from sqlmodel import Session, select

from app.models.admission import Admission
from app.models.care_unit import CareUnit
from app.models.care_unit_layout_position import CareUnitLayoutPosition
from app.models.common import utc_now
from app.models.hospital_service import HospitalService
from app.models.patient import Patient
from app.models.patient_location_history import PatientLocationHistory
from app.models.patient_transfer_request import PatientTransferRequest
from app.models.room import Room
from app.schemas.bed_map import (
    BedMapAdmission,
    BedMapBed,
    BedMapLayout,
    BedMapOccupancy,
    BedMapPendingTransfer,
    BedMapPatient,
    BedMapResponse,
    BedMapRoom,
    BedMapService,
)


def _display_name(patient: Patient) -> str:
    if patient.identity_status == "unidentified":
        available_name = " ".join(
            value
            for value in (patient.given_names, patient.first_surname, patient.second_surname)
            if value
        )
        if available_name:
            return f"{available_name} · {patient.temporary_identifier}"
        return f"Paciente NN · {patient.temporary_identifier}"

    available_name = " ".join(
        value
        for value in (patient.given_names, patient.first_surname, patient.second_surname)
        if value
    )
    if available_name:
        return available_name
    if patient.identity_status == "identified":
        return available_name
    return f"Paciente provisorio · {patient.temporary_identifier}"


def _age_years(date_of_birth: date | None, today: date) -> int | None:
    if date_of_birth is None:
        return None
    birthday_has_passed = (today.month, today.day) >= (
        date_of_birth.month,
        date_of_birth.day,
    )
    return today.year - date_of_birth.year - (0 if birthday_has_passed else 1)


def get_bed_map(session: Session, service_id: uuid.UUID) -> BedMapResponse:
    """Return the operational bed map using a fixed three-query read-only plan."""
    service = session.exec(
        select(HospitalService).where(
            HospitalService.id == service_id,
            HospitalService.is_active.is_(True),
        )
    ).first()
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El servicio no existe o está inactivo.",
        )

    rooms = list(
        session.exec(
            select(Room)
            .where(Room.service_id == service.id, Room.is_active.is_(True))
            .order_by(Room.code, Room.name, Room.id)
        ).all()
    )
    rooms_by_id = {room.id: room for room in rooms}
    beds_by_room: dict[uuid.UUID, list[BedMapBed]] = {room.id: [] for room in rooms}
    generated_at = utc_now()

    if rooms:
        destination_service = aliased(HospitalService)
        rows = session.exec(
            select(
                CareUnit,
                CareUnitLayoutPosition,
                Admission,
                Patient,
                PatientTransferRequest,
                destination_service,
            )
            .outerjoin(
                CareUnitLayoutPosition,
                CareUnitLayoutPosition.care_unit_id == CareUnit.id,
            )
            .outerjoin(
                PatientLocationHistory,
                and_(
                    PatientLocationHistory.care_unit_id == CareUnit.id,
                    PatientLocationHistory.ended_at.is_(None),
                ),
            )
            .outerjoin(
                Admission,
                and_(
                    Admission.id == PatientLocationHistory.admission_id,
                    Admission.status == "active",
                ),
            )
            .outerjoin(Patient, Patient.id == Admission.patient_id)
            .outerjoin(
                PatientTransferRequest,
                and_(
                    PatientTransferRequest.admission_id == Admission.id,
                    PatientTransferRequest.status.in_(("pending_reception", "pending_bed")),
                ),
            )
            .outerjoin(
                destination_service,
                destination_service.id == PatientTransferRequest.destination_service_id,
            )
            .where(
                CareUnit.room_id.in_(list(rooms_by_id)),
                CareUnit.is_active.is_(True),
                CareUnit.unit_type == "bed",
            )
        ).all()

        for care_unit, layout, admission, patient, pending_transfer, destination in rows:
            occupancy = None
            if admission is not None and patient is not None:
                occupancy = BedMapOccupancy(
                    patient=BedMapPatient(
                        id=patient.id,
                        display_name=_display_name(patient),
                        identity_status=patient.identity_status,
                        age_years=_age_years(patient.date_of_birth, generated_at.date()),
                        age_is_estimated=patient.date_of_birth_is_estimated,
                    ),
                    admission=BedMapAdmission(
                        id=admission.id,
                        admission_identifier=admission.admission_identifier,
                        status="active",
                        admitted_at=admission.admitted_at,
                    ),
                    pending_transfer=(
                        BedMapPendingTransfer(
                            id=pending_transfer.id,
                            status=pending_transfer.status,
                            destination_service_id=destination.id,
                            destination_service_code=destination.code,
                            destination_service_name=destination.name,
                            requested_at=pending_transfer.requested_at,
                        )
                        if pending_transfer is not None and destination is not None
                        else None
                    ),
                )
            beds_by_room[care_unit.room_id].append(
                BedMapBed(
                    id=care_unit.id,
                    code=care_unit.code,
                    label=care_unit.label,
                    status="occupied" if occupancy else "free",
                    layout=(
                        BedMapLayout(
                            grid_x=layout.grid_x,
                            grid_y=layout.grid_y,
                            width=layout.width,
                            height=layout.height,
                        )
                        if layout
                        else None
                    ),
                    occupancy=occupancy,
                )
            )

    for beds in beds_by_room.values():
        beds.sort(
            key=lambda bed: (
                bed.layout is None,
                bed.layout.grid_y if bed.layout else 0,
                bed.layout.grid_x if bed.layout else 0,
                bed.code,
                str(bed.id),
            )
        )

    return BedMapResponse(
        generated_at=generated_at,
        service=BedMapService.model_validate(service),
        rooms=[
            BedMapRoom(
                id=room.id,
                code=room.code,
                name=room.name,
                floor=room.floor,
                beds=beds_by_room[room.id],
            )
            for room in rooms
        ],
    )
