import secrets
import uuid
from datetime import date, datetime, timezone
from enum import Enum
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models.admission import Admission
from app.models.admission_status_history import AdmissionStatusHistory
from app.models.care_unit import CareUnit
from app.models.common import utc_now
from app.models.hospital_service import HospitalService
from app.models.patient import Patient
from app.models.patient_location_history import PatientLocationHistory
from app.models.room import Room
from app.schemas.patient import (
    ActiveAdmissionReconciliation,
    AdmissionCreate,
    AdmissionListResponse,
    AdmissionRead,
    AdmissionStatusHistoryRead,
    AdmissionStatusUpdate,
    IdentityStatus,
    LocationAssignment,
    LocationRead,
    PatientCreate,
    PatientDetail,
    PatientIdentityUpdate,
    PatientListResponse,
    PatientReconcile,
    PatientSummary,
    PotentialPatientMatchesResponse,
    UnidentifiedPatientCreate,
    normalize_hospital_identifier,
    normalize_rut,
)
from app.services.audit_service import record_audit


def _not_found(name: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{name} no encontrado.")


def _conflict(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


def _json_value(value: Any) -> Any:
    if isinstance(value, (uuid.UUID, date, datetime, Enum)):
        return value.value if isinstance(value, Enum) else value.isoformat() if isinstance(value, (date, datetime)) else str(value)
    return value


def _snapshot(instance: Any, fields: tuple[str, ...]) -> dict[str, Any]:
    return {field: _json_value(getattr(instance, field)) for field in fields}


PATIENT_AUDIT_FIELDS = (
    "id",
    "identity_status",
    "temporary_identifier",
    "rut",
    "given_names",
    "first_surname",
    "second_surname",
    "date_of_birth",
    "date_of_birth_is_estimated",
    "sex",
    "hospital_identifier",
    "phone",
    "provisional_description",
    "identified_at",
    "identified_by_user_id",
    "merged_into_patient_id",
    "merged_at",
    "merged_by_user_id",
    "merge_reason",
    "is_active",
)
ADMISSION_AUDIT_FIELDS = (
    "id",
    "patient_id",
    "admission_identifier",
    "status",
    "admitted_at",
    "ended_at",
    "end_reason",
)
LOCATION_AUDIT_FIELDS = (
    "id",
    "admission_id",
    "care_unit_id",
    "started_at",
    "ended_at",
    "reason",
    "assigned_by_user_id",
    "ended_by_user_id",
)


def _get_patient(session: Session, patient_id: uuid.UUID, *, for_update: bool = False) -> Patient:
    statement = select(Patient).where(Patient.id == patient_id)
    if for_update:
        statement = statement.with_for_update()
    patient = session.exec(statement).first()
    if patient is None:
        raise _not_found("Paciente")
    return patient


def _get_admission(
    session: Session,
    admission_id: uuid.UUID,
    *,
    for_update: bool = False,
) -> Admission:
    statement = select(Admission).where(Admission.id == admission_id)
    if for_update:
        statement = statement.with_for_update()
    admission = session.exec(statement).first()
    if admission is None:
        raise _not_found("Hospitalización")
    return admission


def _generate_unique_identifier(
    session: Session,
    *,
    prefix: str,
    model: type[Patient] | type[Admission],
    field: Any,
    random_bytes: int,
) -> str:
    day = utc_now().strftime("%Y%m%d")
    for _ in range(30):
        suffix = secrets.token_hex(random_bytes).upper()
        candidate = f"{prefix}-{day}-{suffix}"
        if session.exec(select(model).where(field == candidate)).first() is None:
            return candidate
    raise HTTPException(status_code=503, detail="No fue posible generar un identificador único.")


def _temporary_identifier(session: Session) -> str:
    return _generate_unique_identifier(
        session,
        prefix="NN",
        model=Patient,
        field=Patient.temporary_identifier,
        random_bytes=2,
    )


def _admission_identifier(session: Session) -> str:
    return _generate_unique_identifier(
        session,
        prefix="ADM",
        model=Admission,
        field=Admission.admission_identifier,
        random_bytes=3,
    )


def _ensure_rut_available(
    session: Session,
    rut: str,
    *,
    excluding_patient_id: uuid.UUID | None = None,
) -> Patient | None:
    statement = select(Patient).where(Patient.rut == rut)
    if excluding_patient_id is not None:
        statement = statement.where(Patient.id != excluding_patient_id)
    return session.exec(statement).first()


def _ensure_hospital_identifier_available(
    session: Session,
    hospital_identifier: str,
    *,
    excluding_patient_id: uuid.UUID | None = None,
) -> Patient | None:
    statement = select(Patient).where(Patient.hospital_identifier == hospital_identifier)
    if excluding_patient_id is not None:
        statement = statement.where(Patient.id != excluding_patient_id)
    return session.exec(statement).first()


def _estimated_date_of_birth(age_years: int, reference_date: date) -> date:
    try:
        return reference_date.replace(year=reference_date.year - age_years)
    except ValueError:
        # A creation date on February 29 maps to February 28 in a non-leap birth year.
        return reference_date.replace(year=reference_date.year - age_years, day=28)


def _commit_or_conflict(session: Session, detail: str) -> None:
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise _conflict(detail) from exc


def create_patient(
    session: Session,
    payload: PatientCreate,
    actor_user_id: uuid.UUID,
) -> PatientDetail:
    if payload.rut and _ensure_rut_available(session, payload.rut):
        raise _conflict("Ya existe un paciente con ese RUT.")
    if payload.hospital_identifier and _ensure_hospital_identifier_available(
        session, payload.hospital_identifier
    ):
        raise _conflict("El número de ficha ya pertenece a otro paciente.")
    now = utc_now()
    data = payload.model_dump(mode="python")
    patient = Patient(
        **data,
        temporary_identifier=_temporary_identifier(session)
        if payload.identity_status == IdentityStatus.PROVISIONAL
        else None,
        identified_at=now if payload.identity_status == IdentityStatus.IDENTIFIED else None,
        identified_by_user_id=actor_user_id
        if payload.identity_status == IdentityStatus.IDENTIFIED
        else None,
        created_by_user_id=actor_user_id,
        updated_by_user_id=actor_user_id,
    )
    session.add(patient)
    session.flush()
    record_audit(
        session,
        action="patient_created",
        actor_user_id=actor_user_id,
        entity_type="patient",
        entity_id=patient.id,
        after_state=_snapshot(patient, PATIENT_AUDIT_FIELDS),
    )
    _commit_or_conflict(
        session,
        "Ya existe un paciente con ese RUT, número de ficha o identificador temporal.",
    )
    return get_patient_detail(session, patient.id)


def create_unidentified_patient(
    session: Session,
    payload: UnidentifiedPatientCreate,
    actor_user_id: uuid.UUID,
) -> PatientDetail:
    if payload.hospital_identifier and _ensure_hospital_identifier_available(
        session, payload.hospital_identifier
    ):
        raise _conflict("El número de ficha ya pertenece a otro paciente.")
    data = payload.model_dump(mode="python", exclude={"age_years"})
    if payload.age_years is not None:
        data["date_of_birth"] = _estimated_date_of_birth(
            payload.age_years,
            utc_now().date(),
        )
        data["date_of_birth_is_estimated"] = True
    patient = Patient(
        identity_status=IdentityStatus.UNIDENTIFIED.value,
        temporary_identifier=_temporary_identifier(session),
        created_by_user_id=actor_user_id,
        updated_by_user_id=actor_user_id,
        **data,
    )
    session.add(patient)
    session.flush()
    record_audit(
        session,
        action="patient_unidentified_created",
        actor_user_id=actor_user_id,
        entity_type="patient",
        entity_id=patient.id,
        after_state=_snapshot(patient, PATIENT_AUDIT_FIELDS),
    )
    _commit_or_conflict(
        session,
        "No fue posible reservar el identificador temporal o el número de ficha.",
    )
    return get_patient_detail(session, patient.id)


def _location_rows(
    session: Session,
    admission_ids: list[uuid.UUID],
    *,
    current_only: bool = False,
) -> list[tuple[PatientLocationHistory, CareUnit, Room, HospitalService]]:
    if not admission_ids:
        return []
    statement = (
        select(PatientLocationHistory, CareUnit, Room, HospitalService)
        .join(CareUnit, CareUnit.id == PatientLocationHistory.care_unit_id)
        .join(Room, Room.id == CareUnit.room_id)
        .join(HospitalService, HospitalService.id == Room.service_id)
        .where(PatientLocationHistory.admission_id.in_(admission_ids))
        .order_by(PatientLocationHistory.started_at, PatientLocationHistory.id)
    )
    if current_only:
        statement = statement.where(PatientLocationHistory.ended_at.is_(None))
    return list(session.exec(statement).all())


def _to_location_read(
    location: PatientLocationHistory,
    care_unit: CareUnit,
    room: Room,
    service: HospitalService,
) -> LocationRead:
    return LocationRead(
        **LocationRead.model_validate(location).model_dump(
            exclude={
                "care_unit_code",
                "care_unit_label",
                "room_id",
                "room_code",
                "room_name",
                "service_id",
                "service_code",
                "service_name",
            }
        ),
        care_unit_code=care_unit.code,
        care_unit_label=care_unit.label,
        room_id=room.id,
        room_code=room.code,
        room_name=room.name,
        service_id=service.id,
        service_code=service.code,
        service_name=service.name,
    )


def _admissions_to_reads(
    session: Session,
    admissions: list[Admission],
    *,
    include_history: bool,
) -> list[AdmissionRead]:
    if not admissions:
        return []
    admission_ids = [admission.id for admission in admissions]
    locations_by_admission: dict[uuid.UUID, list[LocationRead]] = {}
    for location, care_unit, room, service in _location_rows(session, admission_ids):
        locations_by_admission.setdefault(location.admission_id, []).append(
            _to_location_read(location, care_unit, room, service)
        )

    status_by_admission: dict[uuid.UUID, list[AdmissionStatusHistoryRead]] = {}
    if include_history:
        status_rows = session.exec(
            select(AdmissionStatusHistory)
            .where(AdmissionStatusHistory.admission_id.in_(admission_ids))
            .order_by(AdmissionStatusHistory.changed_at, AdmissionStatusHistory.id)
        ).all()
        for history in status_rows:
            status_by_admission.setdefault(history.admission_id, []).append(
                AdmissionStatusHistoryRead.model_validate(history)
            )

    result: list[AdmissionRead] = []
    for admission in admissions:
        location_history = locations_by_admission.get(admission.id, [])
        current_location = next(
            (location for location in reversed(location_history) if location.ended_at is None),
            None,
        )
        result.append(
            AdmissionRead(
                **AdmissionRead.model_validate(admission).model_dump(
                    exclude={"current_location", "status_history", "location_history"}
                ),
                current_location=current_location,
                status_history=status_by_admission.get(admission.id, []) if include_history else [],
                location_history=location_history if include_history else [],
            )
        )
    return result


def _patient_summary(patient: Patient, active_admission: AdmissionRead | None) -> PatientSummary:
    return PatientSummary(
        **PatientSummary.model_validate(patient).model_dump(exclude={"active_admission"}),
        active_admission=active_admission,
    )


def list_patients(
    session: Session,
    *,
    query: str | None,
    identity_status: IdentityStatus | None,
    page: int,
    page_size: int,
) -> PatientListResponse:
    filters = [Patient.is_active.is_(True), Patient.merged_into_patient_id.is_(None)]
    if identity_status is not None:
        filters.append(Patient.identity_status == identity_status.value)
    if query and query.strip():
        raw = " ".join(query.split())
        lowered = f"%{raw.lower()}%"
        search_filters = [
            func.lower(func.coalesce(Patient.temporary_identifier, "")).like(lowered),
            func.lower(func.coalesce(Patient.hospital_identifier, "")).like(lowered),
            func.lower(func.coalesce(Patient.given_names, "")).like(lowered),
            func.lower(func.coalesce(Patient.first_surname, "")).like(lowered),
            func.lower(func.coalesce(Patient.second_surname, "")).like(lowered),
        ]
        try:
            normalized_rut = normalize_rut(raw)
        except ValueError:
            normalized_rut = raw.upper().replace(".", "").replace(" ", "")
        search_filters.append(Patient.rut == normalized_rut)
        filters.append(or_(*search_filters))

    total = session.exec(select(func.count()).select_from(Patient).where(*filters)).one()
    patients = list(
        session.exec(
            select(Patient)
            .where(*filters)
            .order_by(Patient.created_at.desc(), Patient.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    patient_ids = [patient.id for patient in patients]
    active_admissions = list(
        session.exec(
            select(Admission)
            .where(Admission.patient_id.in_(patient_ids), Admission.status == "active")
            .order_by(Admission.admitted_at.desc(), Admission.id)
        ).all()
    ) if patient_ids else []
    admission_reads = _admissions_to_reads(session, active_admissions, include_history=False)
    active_by_patient = {admission.patient_id: admission for admission in admission_reads}
    return PatientListResponse(
        items=[_patient_summary(patient, active_by_patient.get(patient.id)) for patient in patients],
        total=total,
        page=page,
        page_size=page_size,
    )


def find_potential_patient_matches(
    session: Session,
    *,
    rut: str | None,
    hospital_identifier: str | None,
    given_names: str | None,
    first_surname: str | None,
) -> PotentialPatientMatchesResponse:
    match_filters = []
    if rut and rut.strip():
        try:
            match_filters.append(Patient.rut == normalize_rut(rut))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    normalized_hospital_identifier = normalize_hospital_identifier(hospital_identifier)
    if normalized_hospital_identifier:
        match_filters.append(
            Patient.hospital_identifier == normalized_hospital_identifier
        )
    normalized_names = " ".join((given_names or "").split())
    if normalized_names:
        match_filters.append(
            func.lower(func.coalesce(Patient.given_names, "")).like(
                f"%{normalized_names.lower()}%"
            )
        )
    normalized_surname = " ".join((first_surname or "").split())
    if normalized_surname:
        lowered_surname = f"%{normalized_surname.lower()}%"
        match_filters.append(
            or_(
                func.lower(func.coalesce(Patient.first_surname, "")).like(
                    lowered_surname
                ),
                func.lower(func.coalesce(Patient.second_surname, "")).like(
                    lowered_surname
                ),
            )
        )
    if not match_filters:
        return PotentialPatientMatchesResponse(items=[], total=0)

    patients = list(
        session.exec(
            select(Patient)
            .where(
                Patient.is_active.is_(True),
                Patient.merged_into_patient_id.is_(None),
                or_(*match_filters),
            )
            .order_by(Patient.created_at.desc(), Patient.id)
            .limit(10)
        ).all()
    )
    patient_ids = [patient.id for patient in patients]
    active_admissions = list(
        session.exec(
            select(Admission)
            .where(
                Admission.patient_id.in_(patient_ids),
                Admission.status == "active",
            )
            .order_by(Admission.admitted_at.desc(), Admission.id)
        ).all()
    ) if patient_ids else []
    reads = _admissions_to_reads(session, active_admissions, include_history=False)
    active_by_patient = {admission.patient_id: admission for admission in reads}
    items = [
        _patient_summary(patient, active_by_patient.get(patient.id))
        for patient in patients
    ]
    return PotentialPatientMatchesResponse(items=items, total=len(items))


def get_patient_detail(session: Session, patient_id: uuid.UUID) -> PatientDetail:
    patient = _get_patient(session, patient_id)
    admissions = list(
        session.exec(
            select(Admission)
            .where(Admission.patient_id == patient.id)
            .order_by(Admission.admitted_at.desc(), Admission.id)
        ).all()
    )
    reads = _admissions_to_reads(session, admissions, include_history=True)
    active = next((admission for admission in reads if admission.status == "active"), None)
    summary = _patient_summary(patient, active)
    return PatientDetail(**summary.model_dump(), admissions=reads)


def identify_patient(
    session: Session,
    patient_id: uuid.UUID,
    payload: PatientIdentityUpdate,
    actor_user_id: uuid.UUID,
) -> PatientDetail:
    patient = _get_patient(session, patient_id, for_update=True)
    if not patient.is_active or patient.merged_into_patient_id is not None:
        raise _conflict("La ficha fusionada o inactiva no puede modificarse.")
    existing = _ensure_rut_available(session, payload.rut, excluding_patient_id=patient.id)
    if existing is not None:
        raise _conflict(
            "El RUT ya pertenece a otro paciente; debe realizar una conciliación explícita."
        )
    if payload.hospital_identifier and _ensure_hospital_identifier_available(
        session,
        payload.hospital_identifier,
        excluding_patient_id=patient.id,
    ):
        raise _conflict("El número de ficha ya pertenece a otro paciente.")
    before = _snapshot(patient, PATIENT_AUDIT_FIELDS)
    for field, value in payload.model_dump(mode="python", exclude_unset=True).items():
        setattr(patient, field, value)
    patient.identity_status = IdentityStatus.IDENTIFIED.value
    patient.identified_at = utc_now()
    patient.identified_by_user_id = actor_user_id
    patient.updated_at = utc_now()
    patient.updated_by_user_id = actor_user_id
    session.add(patient)
    record_audit(
        session,
        action="patient_identified",
        actor_user_id=actor_user_id,
        entity_type="patient",
        entity_id=patient.id,
        before_state=before,
        after_state=_snapshot(patient, PATIENT_AUDIT_FIELDS),
    )
    _commit_or_conflict(
        session,
        "El RUT o número de ficha ya fue asignado por otra solicitud.",
    )
    return get_patient_detail(session, patient.id)


def reconcile_patient(
    session: Session,
    patient_id: uuid.UUID,
    payload: PatientReconcile,
    actor_user_id: uuid.UUID,
) -> PatientDetail:
    source = _get_patient(session, patient_id, for_update=True)
    if not source.is_active or source.merged_into_patient_id is not None:
        raise _conflict("La ficha provisoria ya está inactiva o fusionada.")
    if source.identity_status == IdentityStatus.IDENTIFIED.value:
        raise _conflict("Sólo una ficha NN o provisoria puede conciliarse.")
    canonical = _ensure_rut_available(session, payload.rut, excluding_patient_id=source.id)
    if canonical is None or canonical.identity_status != IdentityStatus.IDENTIFIED.value:
        raise _not_found("Paciente canónico identificado")
    canonical = _get_patient(session, canonical.id, for_update=True)
    if not canonical.is_active or canonical.merged_into_patient_id is not None:
        raise _conflict("La ficha identificada existente está inactiva o fusionada.")
    active_source = session.exec(
        select(Admission).where(
            Admission.patient_id == source.id,
            Admission.status == "active",
        ).with_for_update()
    ).first()
    active_canonical = session.exec(
        select(Admission).where(
            Admission.patient_id == canonical.id,
            Admission.status == "active",
        ).with_for_update()
    ).first()
    if active_source is not None and active_canonical is not None:
        raise _conflict(
            "Ambas fichas tienen hospitalizaciones activas; la conciliación no puede continuar."
        )

    _merge_patient_records(
        session,
        source=source,
        canonical=canonical,
        reason=payload.reason,
        actor_user_id=actor_user_id,
    )
    _commit_or_conflict(session, "La conciliación entró en conflicto con otro cambio concurrente.")
    return get_patient_detail(session, canonical.id)


def _merge_patient_records(
    session: Session,
    *,
    source: Patient,
    canonical: Patient,
    reason: str,
    actor_user_id: uuid.UUID,
    audit_context: dict[str, Any] | None = None,
) -> None:
    """Move admissions and retire the duplicate patient without committing."""

    source_before = _snapshot(source, PATIENT_AUDIT_FIELDS)
    admissions = list(
        session.exec(
            select(Admission).where(Admission.patient_id == source.id).with_for_update()
        ).all()
    )
    now = utc_now()
    for admission in admissions:
        admission.patient_id = canonical.id
        admission.updated_at = now
        admission.updated_by_user_id = actor_user_id
        session.add(admission)
    source.merged_into_patient_id = canonical.id
    source.merged_at = now
    source.merged_by_user_id = actor_user_id
    source.merge_reason = reason
    source.is_active = False
    source.updated_at = now
    source.updated_by_user_id = actor_user_id
    session.add(source)
    record_audit(
        session,
        action="patient_reconciled",
        actor_user_id=actor_user_id,
        entity_type="patient",
        entity_id=source.id,
        before_state=source_before,
        after_state={
            **_snapshot(source, PATIENT_AUDIT_FIELDS),
            "canonical_patient_id": str(canonical.id),
            "moved_admission_ids": [str(admission.id) for admission in admissions],
            **(audit_context or {}),
        },
    )


def resolve_active_admission_reconciliation(
    session: Session,
    patient_id: uuid.UUID,
    payload: ActiveAdmissionReconciliation,
    actor_user_id: uuid.UUID,
) -> PatientDetail:
    """Close one duplicated active admission administratively and merge atomically."""
    source = _get_patient(session, patient_id, for_update=True)
    if not source.is_active or source.merged_into_patient_id is not None:
        raise _conflict("La ficha provisoria ya está inactiva o fusionada.")
    if source.identity_status == IdentityStatus.IDENTIFIED.value:
        raise _conflict("Sólo una ficha NN o provisoria puede conciliarse.")

    canonical_match = _ensure_rut_available(
        session,
        payload.rut,
        excluding_patient_id=source.id,
    )
    if (
        canonical_match is None
        or canonical_match.identity_status != IdentityStatus.IDENTIFIED.value
    ):
        raise _not_found("Paciente canónico identificado")
    canonical = _get_patient(session, canonical_match.id, for_update=True)
    if not canonical.is_active or canonical.merged_into_patient_id is not None:
        raise _conflict("La ficha identificada existente está inactiva o fusionada.")

    active_admissions = list(
        session.exec(
            select(Admission).where(
                Admission.patient_id.in_([source.id, canonical.id]),
                Admission.status == "active",
            ).with_for_update()
        ).all()
    )
    active_by_patient = {admission.patient_id: admission for admission in active_admissions}
    active_source = active_by_patient.get(source.id)
    active_canonical = active_by_patient.get(canonical.id)
    if active_source is None or active_canonical is None:
        raise _conflict(
            "Este flujo requiere que ambas fichas mantengan una hospitalización activa."
        )
    admission_to_close = next(
        (
            admission
            for admission in (active_source, active_canonical)
            if admission.id == payload.admission_to_close_id
        ),
        None,
    )
    if admission_to_close is None:
        raise _conflict(
            "La hospitalización seleccionada no corresponde a uno de los ingresos activos."
        )

    _end_admission_without_commit(
        session,
        admission_to_close,
        next_status="closed",
        reason=f"Duplicidad administrativa: {payload.reason}",
        actor_user_id=actor_user_id,
        admission_audit_action="duplicate_admission_closed_for_reconciliation",
        location_audit_action="location_closed_on_duplicate_resolution",
    )
    try:
        # Persist the administrative close before moving the other active episode
        # to the canonical patient, so the partial unique index is never violated.
        session.flush()
    except IntegrityError as exc:
        session.rollback()
        raise _conflict(
            "La hospitalización seleccionada cambió durante la resolución."
        ) from exc
    _merge_patient_records(
        session,
        source=source,
        canonical=canonical,
        reason=payload.reason,
        actor_user_id=actor_user_id,
        audit_context={
            "resolved_active_admission_conflict": True,
            "administratively_closed_admission_id": str(admission_to_close.id),
        },
    )
    _commit_or_conflict(
        session,
        "La resolución entró en conflicto con otro cambio concurrente.",
    )
    return get_patient_detail(session, canonical.id)


def _assign_location_without_commit(
    session: Session,
    admission: Admission,
    payload: LocationAssignment,
    actor_user_id: uuid.UUID,
) -> PatientLocationHistory:
    if admission.status != "active":
        raise _conflict("No se puede modificar la ubicación de una hospitalización terminada.")
    destination_row = session.exec(
        select(CareUnit, Room, HospitalService)
        .join(Room, Room.id == CareUnit.room_id)
        .join(HospitalService, HospitalService.id == Room.service_id)
        .where(CareUnit.id == payload.care_unit_id)
        .with_for_update()
    ).first()
    if destination_row is None:
        raise _not_found("Cama")
    care_unit, destination_room, destination_service = destination_row
    if (
        not care_unit.is_active
        or care_unit.unit_type != "bed"
        or not destination_room.is_active
        or not destination_service.is_active
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La ubicación debe ser una cama activa de una sala y servicio activos.",
        )
    occupied = session.exec(
        select(PatientLocationHistory).where(
            PatientLocationHistory.care_unit_id == care_unit.id,
            PatientLocationHistory.ended_at.is_(None),
        ).with_for_update()
    ).first()
    if occupied is not None and occupied.admission_id != admission.id:
        raise _conflict("La cama se encuentra ocupada por otra hospitalización.")

    current = session.exec(
        select(PatientLocationHistory).where(
            PatientLocationHistory.admission_id == admission.id,
            PatientLocationHistory.ended_at.is_(None),
        ).with_for_update()
    ).first()
    if current is not None and current.care_unit_id == care_unit.id:
        raise _conflict("La hospitalización ya se encuentra en esa cama.")
    if current is not None:
        current_structure = session.exec(
            select(CareUnit, Room)
            .join(Room, Room.id == CareUnit.room_id)
            .where(CareUnit.id == current.care_unit_id)
        ).one()
        current_bed, current_room = current_structure
        if not current_bed.is_active or current_bed.unit_type != "bed":
            raise _conflict("La ubicación vigente debe ser una cama activa.")
        if current_room.service_id != destination_service.id:
            raise _conflict(
                "Los cambios entre servicios deben usar el flujo de traslados."
            )

    now = utc_now()
    action = "location_assigned"
    previous_state = None
    if current is not None:
        previous_state = _snapshot(current, LOCATION_AUDIT_FIELDS)
        current.ended_at = now
        current.ended_by_user_id = actor_user_id
        session.add(current)
        record_audit(
            session,
            action="location_closed_for_transfer",
            actor_user_id=actor_user_id,
            entity_type="patient_location",
            entity_id=current.id,
            before_state=previous_state,
            after_state=_snapshot(current, LOCATION_AUDIT_FIELDS),
            admission_id=admission.id,
        )
        action = "location_transferred"

    location = PatientLocationHistory(
        admission_id=admission.id,
        care_unit_id=care_unit.id,
        started_at=now,
        reason=payload.reason,
        assigned_by_user_id=actor_user_id,
    )
    session.add(location)
    session.flush()
    record_audit(
        session,
        action=action,
        actor_user_id=actor_user_id,
        entity_type="patient_location",
        entity_id=location.id,
        before_state=previous_state,
        after_state=_snapshot(location, LOCATION_AUDIT_FIELDS),
        admission_id=admission.id,
    )
    return location


def create_admission(
    session: Session,
    payload: AdmissionCreate,
    actor_user_id: uuid.UUID,
) -> AdmissionRead:
    patient = _get_patient(session, payload.patient_id, for_update=True)
    if not patient.is_active or patient.merged_into_patient_id is not None:
        raise _conflict("No se puede hospitalizar una ficha inactiva o fusionada.")
    if session.exec(
        select(Admission).where(
            Admission.patient_id == patient.id,
            Admission.status == "active",
        )
    ).first() is not None:
        raise _conflict("El paciente ya tiene una hospitalización activa.")
    identifier = payload.admission_identifier or _admission_identifier(session)
    admitted_at = payload.admitted_at or utc_now()
    if admitted_at.tzinfo is None:
        admitted_at = admitted_at.replace(tzinfo=timezone.utc)
    admission = Admission(
        patient_id=patient.id,
        admission_identifier=identifier,
        admitted_at=admitted_at.astimezone(timezone.utc),
        created_by_user_id=actor_user_id,
        updated_by_user_id=actor_user_id,
    )
    session.add(admission)
    session.flush()
    session.add(
        AdmissionStatusHistory(
            admission_id=admission.id,
            from_status=None,
            to_status="active",
            reason="Creación de hospitalización.",
            changed_by_user_id=actor_user_id,
        )
    )
    record_audit(
        session,
        action="admission_created",
        actor_user_id=actor_user_id,
        entity_type="admission",
        entity_id=admission.id,
        after_state=_snapshot(admission, ADMISSION_AUDIT_FIELDS),
        admission_id=admission.id,
    )
    if payload.care_unit_id is not None:
        _assign_location_without_commit(
            session,
            admission,
            LocationAssignment(
                care_unit_id=payload.care_unit_id,
                reason=payload.location_reason or "Cama inicial.",
            ),
            actor_user_id,
        )
    _commit_or_conflict(
        session,
        "El paciente ya tiene una hospitalización activa, la cama está ocupada o el identificador ya existe.",
    )
    return get_admission_detail(session, admission.id)


def list_active_admissions(session: Session) -> AdmissionListResponse:
    admissions = list(
        session.exec(
            select(Admission)
            .where(Admission.status == "active")
            .order_by(Admission.admitted_at, Admission.id)
        ).all()
    )
    return AdmissionListResponse(
        items=_admissions_to_reads(session, admissions, include_history=False),
        total=len(admissions),
    )


def list_patient_admissions(session: Session, patient_id: uuid.UUID) -> AdmissionListResponse:
    _get_patient(session, patient_id)
    admissions = list(
        session.exec(
            select(Admission)
            .where(Admission.patient_id == patient_id)
            .order_by(Admission.admitted_at.desc(), Admission.id)
        ).all()
    )
    return AdmissionListResponse(
        items=_admissions_to_reads(session, admissions, include_history=True),
        total=len(admissions),
    )


def get_admission_detail(session: Session, admission_id: uuid.UUID) -> AdmissionRead:
    admission = _get_admission(session, admission_id)
    return _admissions_to_reads(session, [admission], include_history=True)[0]


def _end_admission_without_commit(
    session: Session,
    admission: Admission,
    *,
    next_status: str,
    reason: str,
    actor_user_id: uuid.UUID,
    admission_audit_action: str = "admission_status_changed",
    location_audit_action: str = "location_closed_on_admission_end",
) -> None:
    if admission.status != "active":
        raise _conflict("La hospitalización ya se encuentra terminada.")
    # This helper is shared by discharge, death, administrative close, and
    # duplicate-admission reconciliation, so every terminal path cancels an
    # open transfer in the same transaction.
    from app.services.transfer_service import cancel_open_transfer_on_admission_end

    cancel_open_transfer_on_admission_end(
        session,
        admission.id,
        reason=reason,
        actor_user_id=actor_user_id,
    )
    before = _snapshot(admission, ADMISSION_AUDIT_FIELDS)
    now = utc_now()
    current_location = session.exec(
        select(PatientLocationHistory).where(
            PatientLocationHistory.admission_id == admission.id,
            PatientLocationHistory.ended_at.is_(None),
        ).with_for_update()
    ).first()
    if current_location is not None:
        location_before = _snapshot(current_location, LOCATION_AUDIT_FIELDS)
        current_location.ended_at = now
        current_location.ended_by_user_id = actor_user_id
        session.add(current_location)
        record_audit(
            session,
            action=location_audit_action,
            actor_user_id=actor_user_id,
            entity_type="patient_location",
            entity_id=current_location.id,
            before_state=location_before,
            after_state=_snapshot(current_location, LOCATION_AUDIT_FIELDS),
            admission_id=admission.id,
        )
    admission.status = next_status
    admission.ended_at = now
    admission.end_reason = reason
    admission.updated_at = now
    admission.updated_by_user_id = actor_user_id
    session.add(admission)
    session.add(
        AdmissionStatusHistory(
            admission_id=admission.id,
            from_status="active",
            to_status=next_status,
            reason=reason,
            changed_at=now,
            changed_by_user_id=actor_user_id,
        )
    )
    record_audit(
        session,
        action=admission_audit_action,
        actor_user_id=actor_user_id,
        entity_type="admission",
        entity_id=admission.id,
        before_state=before,
        after_state=_snapshot(admission, ADMISSION_AUDIT_FIELDS),
        admission_id=admission.id,
    )


def update_admission_status(
    session: Session,
    admission_id: uuid.UUID,
    payload: AdmissionStatusUpdate,
    actor_user_id: uuid.UUID,
) -> AdmissionRead:
    admission = _get_admission(session, admission_id, for_update=True)
    _end_admission_without_commit(
        session,
        admission,
        next_status=payload.status.value,
        reason=payload.reason,
        actor_user_id=actor_user_id,
    )
    session.commit()
    return get_admission_detail(session, admission.id)


def assign_location(
    session: Session,
    admission_id: uuid.UUID,
    payload: LocationAssignment,
    actor_user_id: uuid.UUID,
) -> LocationRead:
    admission = _get_admission(session, admission_id, for_update=True)
    location = _assign_location_without_commit(session, admission, payload, actor_user_id)
    _commit_or_conflict(session, "La cama fue ocupada por otra solicitud concurrente.")
    return get_current_location(session, location.admission_id)


def get_current_location(session: Session, admission_id: uuid.UUID) -> LocationRead:
    _get_admission(session, admission_id)
    rows = _location_rows(session, [admission_id], current_only=True)
    if not rows:
        raise _not_found("Ubicación actual")
    return _to_location_read(*rows[0])


def get_location_history(session: Session, admission_id: uuid.UUID) -> list[LocationRead]:
    _get_admission(session, admission_id)
    return [_to_location_read(*row) for row in _location_rows(session, [admission_id])]
