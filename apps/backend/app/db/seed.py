"""Idempotent seed data for local NutriWard development environments."""

from datetime import datetime, timezone

from sqlalchemy import or_
from sqlmodel import Session, select

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import engine
from app.models.care_unit import CareUnit
from app.models.care_unit_layout_position import CareUnitLayoutPosition
from app.models.admission import Admission
from app.models.admission_status_history import AdmissionStatusHistory
from app.models.common import utc_now
from app.models.hospital_service import HospitalService
from app.models.nutritionist_service_assignment import NutritionistServiceAssignment
from app.models.patient import Patient
from app.models.patient_location_history import PatientLocationHistory
from app.models.patient_transfer_request import PatientTransferRequest
from app.models.patient_transfer_request_status_history import (
    PatientTransferRequestStatusHistory,
)
from app.models.role import Role
from app.models.room import Room
from app.models.user import User
from app.models.user_role import UserRole
from app.services.audit_service import record_audit
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

SERVICE_DEFINITIONS = {
    "MED": ("Medicina", "Hospitalización médico-quirúrgica."),
    "UCI": ("Unidad de Cuidados Intensivos", "Atención de pacientes críticos."),
    "UTI": ("Unidad de Tratamiento Intermedio", "Atención intermedia y monitorización."),
    "CIR": ("Cirugía", "Hospitalización quirúrgica."),
}

ROOM_DEFINITIONS = {
    "MED": (
        ("A101", "Sala A101", "Piso 1"),
        ("A102", "Sala A102", "Piso 1"),
    ),
    "UCI": (("UCI-A", "UCI Sector A", "Piso 2"),),
    "UTI": (("UTI-A", "UTI Sector A", "Piso 2"),),
    "CIR": (("C201", "Sala C201", "Piso 2"),),
}

CARE_UNIT_DEFINITIONS = {
    ("MED", "A101"): ("01", "02"),
    ("MED", "A102"): ("01", "02"),
    ("UCI", "UCI-A"): ("01", "02"),
    ("UTI", "UTI-A"): ("01", "02"),
    ("CIR", "C201"): ("01", "02"),
}

PATIENT_DEFINITIONS = (
    {
        "key": "identified_one",
        "identity_status": "identified",
        "rut": "11111111-1",
        "given_names": "Paciente",
        "first_surname": "Demostración Uno",
        "date_of_birth": datetime(1980, 1, 15, tzinfo=timezone.utc).date(),
        "sex": "female",
        "hospital_identifier": "DEMO-PAC-001",
    },
    {
        "key": "identified_two",
        "identity_status": "identified",
        "rut": "22222222-2",
        "given_names": "Paciente",
        "first_surname": "Demostración Dos",
        "date_of_birth": datetime(1972, 6, 20, tzinfo=timezone.utc).date(),
        "sex": "male",
        "hospital_identifier": "DEMO-PAC-002",
    },
    {
        "key": "nn_one",
        "identity_status": "unidentified",
        "temporary_identifier": "NN-20260731-A001",
        "provisional_description": "Persona adulta de identidad desconocida, caso demostrativo A.",
        "sex": "unknown",
    },
    {
        "key": "nn_two",
        "identity_status": "unidentified",
        "temporary_identifier": "NN-20260731-A002",
        "provisional_description": "Persona adulta de identidad desconocida, caso demostrativo B.",
        "sex": "unknown",
    },
)

ADMISSION_DEFINITIONS = (
    {
        "identifier": "ADM-DEMO-ACT-001",
        "patient_key": "identified_one",
        "status": "active",
        "admitted_at": datetime(2026, 7, 29, 13, 0, tzinfo=timezone.utc),
        "bed": ("MED", "A101", "01"),
    },
    {
        "identifier": "ADM-DEMO-ACT-002",
        "patient_key": "nn_one",
        "status": "active",
        "admitted_at": datetime(2026, 7, 30, 17, 30, tzinfo=timezone.utc),
        "bed": ("UCI", "UCI-A", "01"),
    },
    {
        "identifier": "ADM-DEMO-ACT-003",
        "patient_key": "nn_two",
        "status": "active",
        "admitted_at": datetime(2026, 7, 31, 8, 15, tzinfo=timezone.utc),
        "bed": None,
    },
    {
        "identifier": "ADM-DEMO-HIST-001",
        "patient_key": "identified_two",
        "status": "discharged",
        "admitted_at": datetime(2026, 7, 10, 12, 0, tzinfo=timezone.utc),
        "ended_at": datetime(2026, 7, 15, 16, 0, tzinfo=timezone.utc),
        "end_reason": "Alta médica demostrativa.",
        "bed": ("MED", "A102", "01"),
    },
)


def seed_database(session: Session) -> None:
    roles: dict[str, Role] = {}
    users: dict[str, User] = {}
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
        elif not assignment.is_active:
            assignment.is_active = True
            assignment.updated_at = utc_now()
            session.add(assignment)
        users[role_name] = user

    services: dict[str, HospitalService] = {}
    for code, (name, description) in SERVICE_DEFINITIONS.items():
        service = session.exec(
            select(HospitalService).where(
                or_(HospitalService.code == code, HospitalService.name == name)
            )
        ).first()
        if service is None:
            service = HospitalService(code=code, name=name, description=description)
            session.add(service)
            session.flush()
        services[code] = service

    rooms: dict[tuple[str, str], Room] = {}
    for service_code, definitions in ROOM_DEFINITIONS.items():
        for room_code, room_name, floor in definitions:
            room = session.exec(
                select(Room).where(
                    Room.service_id == services[service_code].id,
                    Room.code == room_code,
                )
            ).first()
            if room is None:
                room = Room(
                    service_id=services[service_code].id,
                    code=room_code,
                    name=room_name,
                    floor=floor,
                )
                session.add(room)
                session.flush()
            rooms[(service_code, room_code)] = room

    for room_key, care_unit_codes in CARE_UNIT_DEFINITIONS.items():
        for position, care_unit_code in enumerate(care_unit_codes):
            room = rooms[room_key]
            care_unit = session.exec(
                select(CareUnit).where(CareUnit.room_id == room.id, CareUnit.code == care_unit_code)
            ).first()
            if care_unit is None:
                care_unit = CareUnit(room_id=room.id, code=care_unit_code, label=f"Cama {care_unit_code}")
                session.add(care_unit)
                session.flush()
            layout = session.exec(
                select(CareUnitLayoutPosition).where(CareUnitLayoutPosition.care_unit_id == care_unit.id)
            ).first()
            if layout is None:
                session.add(
                    CareUnitLayoutPosition(
                        care_unit_id=care_unit.id,
                        grid_x=position * 2,
                        grid_y=0,
                    )
                )

    for service_code in ("MED", "UCI"):
        nutritionist_assignment = session.exec(
            select(NutritionistServiceAssignment).where(
                NutritionistServiceAssignment.nutritionist_user_id
                == users["nutricionista"].id,
                NutritionistServiceAssignment.service_id == services[service_code].id,
            )
        ).first()
        if nutritionist_assignment is None:
            session.add(
                NutritionistServiceAssignment(
                    nutritionist_user_id=users["nutricionista"].id,
                    service_id=services[service_code].id,
                )
            )
        elif not nutritionist_assignment.is_active:
            nutritionist_assignment.is_active = True
            nutritionist_assignment.updated_at = utc_now()
            session.add(nutritionist_assignment)

    patients: dict[str, Patient] = {}
    seed_actor = users["administrador"]
    for definition in PATIENT_DEFINITIONS:
        lookup = (
            Patient.rut == definition["rut"]
            if definition.get("rut")
            else Patient.temporary_identifier == definition["temporary_identifier"]
        )
        patient = session.exec(select(Patient).where(lookup)).first()
        if patient is None:
            data = {key: value for key, value in definition.items() if key != "key"}
            patient = Patient(
                **data,
                identified_at=utc_now() if data["identity_status"] == "identified" else None,
                identified_by_user_id=seed_actor.id
                if data["identity_status"] == "identified"
                else None,
                created_by_user_id=seed_actor.id,
                updated_by_user_id=seed_actor.id,
            )
            session.add(patient)
            session.flush()
        patients[definition["key"]] = patient

    care_units_by_key: dict[tuple[str, str, str], CareUnit] = {}
    for service_code, room_code, care_unit_code in {
        definition["bed"] for definition in ADMISSION_DEFINITIONS if definition["bed"]
    }:
        room = rooms[(service_code, room_code)]
        care_units_by_key[(service_code, room_code, care_unit_code)] = session.exec(
            select(CareUnit).where(
                CareUnit.room_id == room.id,
                CareUnit.code == care_unit_code,
            )
        ).one()

    for definition in ADMISSION_DEFINITIONS:
        admission = session.exec(
            select(Admission).where(
                Admission.admission_identifier == definition["identifier"]
            )
        ).first()
        if admission is None:
            admission = Admission(
                patient_id=patients[definition["patient_key"]].id,
                admission_identifier=definition["identifier"],
                status=definition["status"],
                admitted_at=definition["admitted_at"],
                ended_at=definition.get("ended_at"),
                end_reason=definition.get("end_reason"),
                created_by_user_id=seed_actor.id,
                updated_by_user_id=seed_actor.id,
            )
            session.add(admission)
            session.flush()
        initial_history = session.exec(
            select(AdmissionStatusHistory).where(
                AdmissionStatusHistory.admission_id == admission.id,
                AdmissionStatusHistory.to_status == "active",
            )
        ).first()
        if initial_history is None:
            session.add(
                AdmissionStatusHistory(
                    admission_id=admission.id,
                    from_status=None,
                    to_status="active",
                    reason="Creación de hospitalización demo.",
                    changed_at=definition["admitted_at"],
                    changed_by_user_id=seed_actor.id,
                )
            )
        if definition["status"] != "active":
            terminal_history = session.exec(
                select(AdmissionStatusHistory).where(
                    AdmissionStatusHistory.admission_id == admission.id,
                    AdmissionStatusHistory.to_status == definition["status"],
                )
            ).first()
            if terminal_history is None:
                session.add(
                    AdmissionStatusHistory(
                        admission_id=admission.id,
                        from_status="active",
                        to_status=definition["status"],
                        reason=definition["end_reason"],
                        changed_at=definition["ended_at"],
                        changed_by_user_id=seed_actor.id,
                    )
                )
        if definition["bed"]:
            care_unit = care_units_by_key[definition["bed"]]
            location = session.exec(
                select(PatientLocationHistory).where(
                    PatientLocationHistory.admission_id == admission.id,
                    PatientLocationHistory.care_unit_id == care_unit.id,
                )
            ).first()
            if location is None:
                session.add(
                    PatientLocationHistory(
                        admission_id=admission.id,
                        care_unit_id=care_unit.id,
                        started_at=definition["admitted_at"],
                        ended_at=definition.get("ended_at"),
                        reason="Asignación demo.",
                        assigned_by_user_id=seed_actor.id,
                        ended_by_user_id=seed_actor.id
                        if definition.get("ended_at")
                        else None,
                    )
                )
    session.flush()

    # Phase 7 transfer examples use the existing fictitious admissions. Terminal
    # requests are historical and the two final definitions are the only open
    # requests, one per admission. Re-running the seed never adds another current
    # location or another status event.
    active_med = session.exec(
        select(Admission).where(Admission.admission_identifier == "ADM-DEMO-ACT-001")
    ).one()
    active_uci = session.exec(
        select(Admission).where(Admission.admission_identifier == "ADM-DEMO-ACT-002")
    ).one()
    service_by_code = {
        code: session.exec(select(HospitalService).where(HospitalService.code == code)).one()
        for code in ("MED", "UCI", "UTI")
    }

    def bed(service_code: str, room_code: str, code: str) -> CareUnit:
        return session.exec(
            select(CareUnit)
            .join(Room, Room.id == CareUnit.room_id)
            .where(
                Room.service_id == service_by_code[service_code].id,
                Room.code == room_code,
                CareUnit.code == code,
            )
        ).one()

    uti_bed = bed("UTI", "UTI-A", "02")
    uci_bed = bed("UCI", "UCI-A", "01")

    # A demo admission may have been discharged or administratively closed by a
    # developer between seed runs. Never recreate an open transfer on that
    # inactive admission: retire any legacy open fixture first, preserving its
    # history and audit trail.
    open_statuses = ("requested", "pending_reception", "accepted", "pending_bed")
    stale_open_transfers = session.exec(
        select(PatientTransferRequest, Admission)
        .join(Admission, Admission.id == PatientTransferRequest.admission_id)
        .where(
            PatientTransferRequest.status.in_(open_statuses),
            PatientTransferRequest.request_reason.startswith("Dato ficticio Fase 7"),
            Admission.status != "active",
        )
    ).all()
    for transfer, inactive_admission in stale_open_transfers:
        cleanup_at = utc_now()
        last_event = session.exec(
            select(PatientTransferRequestStatusHistory)
            .where(
                PatientTransferRequestStatusHistory.transfer_request_id == transfer.id
            )
            .order_by(PatientTransferRequestStatusHistory.sequence_number.desc())
        ).first()
        previous_status = transfer.status
        cleanup_reason = (
            "Seed cerrado automaticamente: la hospitalizacion ya no esta activa."
        )
        session.add(
            PatientTransferRequestStatusHistory(
                transfer_request_id=transfer.id,
                sequence_number=(last_event.sequence_number if last_event else 0) + 1,
                from_status=previous_status,
                to_status="cancelled",
                reason=cleanup_reason,
                changed_by_user_id=seed_actor.id,
                changed_at=cleanup_at,
                is_coverage=False,
            )
        )
        transfer.status = "cancelled"
        transfer.completed_at = cleanup_at
        transfer.updated_at = cleanup_at
        session.add(transfer)
        record_audit(
            session,
            action="transfer_cancelled",
            actor_user_id=seed_actor.id,
            entity_type="patient_transfer_request",
            entity_id=transfer.id,
            before_state={"status": previous_status},
            after_state={
                "status": "cancelled",
                "reason": cleanup_reason,
                "seed_cleanup": True,
            },
            admission_id=inactive_admission.id,
        )
        current_locations = session.exec(
            select(PatientLocationHistory).where(
                PatientLocationHistory.admission_id == inactive_admission.id,
                PatientLocationHistory.ended_at.is_(None),
            )
        ).all()
        for location in current_locations:
            location.ended_at = cleanup_at
            location.ended_by_user_id = seed_actor.id
            session.add(location)
    session.flush()

    def open_seed_admission(
        *,
        base_admission: Admission,
        identifier_prefix: str,
        patient_identifier_prefix: str,
        preferred_bed: CareUnit,
        admitted_at: datetime,
        destination_service: HospitalService,
    ) -> tuple[Admission, CareUnit, HospitalService]:
        """Return an active, bedded admission reserved for an open Phase 7 fixture."""

        candidates = [base_admission]
        candidates.extend(
            session.exec(
                select(Admission)
                .where(
                    Admission.admission_identifier.startswith(identifier_prefix),
                    Admission.status == "active",
                )
                .order_by(Admission.admitted_at.desc(), Admission.id)
            ).all()
        )
        for candidate in candidates:
            if candidate.status != "active":
                continue
            current_row = session.exec(
                select(PatientLocationHistory, CareUnit, Room, HospitalService)
                .join(CareUnit, CareUnit.id == PatientLocationHistory.care_unit_id)
                .join(Room, Room.id == CareUnit.room_id)
                .join(HospitalService, HospitalService.id == Room.service_id)
                .where(
                    PatientLocationHistory.admission_id == candidate.id,
                    PatientLocationHistory.ended_at.is_(None),
                    CareUnit.is_active.is_(True),
                    CareUnit.unit_type == "bed",
                    Room.is_active.is_(True),
                    HospitalService.is_active.is_(True),
                    HospitalService.id != destination_service.id,
                )
            ).first()
            if current_row is not None:
                _, current_bed, _, current_service = current_row
                return candidate, current_bed, current_service

        occupied_bed_ids = set(
            session.exec(
                select(PatientLocationHistory.care_unit_id).where(
                    PatientLocationHistory.ended_at.is_(None)
                )
            ).all()
        )
        available_rows = session.exec(
            select(CareUnit, Room, HospitalService)
            .join(Room, Room.id == CareUnit.room_id)
            .join(HospitalService, HospitalService.id == Room.service_id)
            .where(
                CareUnit.is_active.is_(True),
                CareUnit.unit_type == "bed",
                Room.is_active.is_(True),
                HospitalService.is_active.is_(True),
                HospitalService.id != destination_service.id,
            )
            .order_by(HospitalService.code, Room.code, CareUnit.code, CareUnit.id)
        ).all()
        available_rows = [
            row for row in available_rows if row[0].id not in occupied_bed_ids
        ]
        selected_row = next(
            (row for row in available_rows if row[0].id == preferred_bed.id),
            available_rows[0] if available_rows else None,
        )
        if selected_row is None:
            raise RuntimeError(
                "No existe una cama activa y libre para el seed abierto de Fase 7."
            )
        selected_bed, _, selected_service = selected_row

        existing_identifiers = set(
            session.exec(
                select(Admission.admission_identifier).where(
                    Admission.admission_identifier.startswith(identifier_prefix)
                )
            ).all()
        )
        suffix = 1
        identifier = f"{identifier_prefix}-{suffix:02d}"
        while identifier in existing_identifiers:
            suffix += 1
            identifier = f"{identifier_prefix}-{suffix:02d}"
        replacement_patient_id = base_admission.patient_id
        patient_has_active_admission = session.exec(
            select(Admission.id).where(
                Admission.patient_id == replacement_patient_id,
                Admission.status == "active",
            )
        ).first()
        if patient_has_active_admission is not None:
            seed_patients = session.exec(
                select(Patient)
                .where(
                    Patient.temporary_identifier.startswith(patient_identifier_prefix),
                    Patient.is_active.is_(True),
                    Patient.merged_into_patient_id.is_(None),
                )
                .order_by(Patient.temporary_identifier, Patient.id)
            ).all()
            replacement_patient = next(
                (
                    patient
                    for patient in seed_patients
                    if session.exec(
                        select(Admission.id).where(
                            Admission.patient_id == patient.id,
                            Admission.status == "active",
                        )
                    ).first()
                    is None
                ),
                None,
            )
            if replacement_patient is None:
                existing_patient_identifiers = {
                    patient.temporary_identifier for patient in seed_patients
                }
                patient_suffix = 1
                temporary_identifier = (
                    f"{patient_identifier_prefix}-{patient_suffix:02d}"
                )
                while temporary_identifier in existing_patient_identifiers:
                    patient_suffix += 1
                    temporary_identifier = (
                        f"{patient_identifier_prefix}-{patient_suffix:02d}"
                    )
                replacement_patient = Patient(
                    identity_status="unidentified",
                    temporary_identifier=temporary_identifier,
                    provisional_description=(
                        "Paciente ficticio exclusivo para traslado abierto de Fase 7."
                    ),
                    sex="unknown",
                    is_active=True,
                    created_by_user_id=seed_actor.id,
                    updated_by_user_id=seed_actor.id,
                )
                session.add(replacement_patient)
                session.flush()
            replacement_patient_id = replacement_patient.id

        replacement = Admission(
            patient_id=replacement_patient_id,
            admission_identifier=identifier,
            status="active",
            admitted_at=admitted_at,
            created_by_user_id=seed_actor.id,
            updated_by_user_id=seed_actor.id,
        )
        session.add(replacement)
        session.flush()
        session.add(
            AdmissionStatusHistory(
                admission_id=replacement.id,
                from_status=None,
                to_status="active",
                reason="HospitalizaciÃ³n ficticia exclusiva para traslado abierto de Fase 7.",
                changed_at=admitted_at,
                changed_by_user_id=seed_actor.id,
            )
        )
        session.add(
            PatientLocationHistory(
                admission_id=replacement.id,
                care_unit_id=selected_bed.id,
                started_at=admitted_at,
                reason="UbicaciÃ³n ficticia exclusiva para traslado abierto de Fase 7.",
                assigned_by_user_id=seed_actor.id,
            )
        )
        session.flush()
        return replacement, selected_bed, selected_service

    def ensure_transfer(
        *,
        admission: Admission,
        key: str,
        origin_service: HospitalService,
        destination_service: HospitalService,
        origin_bed: CareUnit,
        final_status: str,
        history_statuses: tuple[str, ...],
        requested_at: datetime,
        mode: str = "reception_tray",
        destination_bed: CareUnit | None = None,
    ) -> PatientTransferRequest:
        request_reason = f"Dato ficticio Fase 7 · {key}"
        transfer = session.exec(
            select(PatientTransferRequest).where(
                PatientTransferRequest.admission_id == admission.id,
                PatientTransferRequest.request_reason == request_reason,
            )
        ).first()
        if transfer is None:
            transfer = PatientTransferRequest(
                admission_id=admission.id,
                origin_service_id=origin_service.id,
                destination_service_id=destination_service.id,
                origin_care_unit_id=origin_bed.id,
                destination_care_unit_id=destination_bed.id if destination_bed else None,
                transfer_mode=mode,
                status=final_status,
                request_reason=request_reason,
                requested_by_user_id=seed_actor.id,
                requested_at=requested_at,
                completed_at=requested_at if final_status in {
                    "assigned_to_bed", "rejected", "returned", "cancelled"
                } else None,
                created_at=requested_at,
                updated_at=requested_at,
            )
            session.add(transfer)
            session.flush()
        existing_history = session.exec(
            select(PatientTransferRequestStatusHistory.id).where(
                PatientTransferRequestStatusHistory.transfer_request_id == transfer.id
            )
        ).first()
        if existing_history is None:
            previous = None
            for sequence, target_status in enumerate(history_statuses, start=1):
                session.add(
                    PatientTransferRequestStatusHistory(
                        transfer_request_id=transfer.id,
                        sequence_number=sequence,
                        from_status=previous,
                        to_status=target_status,
                        reason=request_reason if sequence == 1 else f"Hito demo: {target_status}",
                        changed_by_user_id=seed_actor.id,
                        changed_at=requested_at,
                        is_coverage=False,
                    )
                )
                previous = target_status
        return transfer

    direct = ensure_transfer(
        admission=active_med,
        key="traslado directo completado",
        origin_service=service_by_code["MED"],
        destination_service=service_by_code["UTI"],
        origin_bed=session.exec(
            select(CareUnit)
            .join(Room, Room.id == CareUnit.room_id)
            .where(Room.service_id == service_by_code["MED"].id, Room.code == "A101", CareUnit.code == "01")
        ).one(),
        destination_bed=uti_bed,
        mode="direct",
        final_status="assigned_to_bed",
        history_statuses=("requested", "pending_reception", "accepted", "assigned_to_bed"),
        requested_at=datetime(2026, 8, 6, 9, 0, tzinfo=timezone.utc),
    )
    if active_med.status == "active":
        current_med = session.exec(
            select(PatientLocationHistory).where(
                PatientLocationHistory.admission_id == active_med.id,
                PatientLocationHistory.ended_at.is_(None),
            )
        ).first()
        if current_med is None or current_med.care_unit_id != uti_bed.id:
            moved_at = datetime(2026, 8, 6, 9, 0, tzinfo=timezone.utc)
            if current_med is not None:
                current_med.ended_at = moved_at
                current_med.ended_by_user_id = seed_actor.id
                session.add(current_med)
                session.flush()
            session.add(
                PatientLocationHistory(
                    admission_id=active_med.id,
                    care_unit_id=uti_bed.id,
                    started_at=moved_at,
                    reason=f"Traslado demo {direct.id}",
                    assigned_by_user_id=seed_actor.id,
                )
            )
            session.flush()

    terminal_definitions = (
        ("traslado rechazado", "rejected", ("requested", "pending_reception", "rejected"), 7),
        (
            "traslado devuelto",
            "returned",
            ("requested", "pending_reception", "accepted", "pending_bed", "returned"),
            8,
        ),
        ("traslado cancelado", "cancelled", ("requested", "pending_reception", "cancelled"), 9),
    )
    for key, final_status, history_statuses, day in terminal_definitions:
        ensure_transfer(
            admission=active_med,
            key=key,
            origin_service=service_by_code["UTI"],
            destination_service=service_by_code["MED"],
            origin_bed=uti_bed,
            final_status=final_status,
            history_statuses=history_statuses,
            requested_at=datetime(2026, 8, day, 9, 0, tzinfo=timezone.utc),
        )

    pending_reception_admission, pending_reception_bed, pending_reception_origin = (
        open_seed_admission(
            base_admission=active_med,
            identifier_prefix="ADM-DEMO-P7-OPEN-RECEPTION",
            patient_identifier_prefix="NN-P7-RECEPTION",
            preferred_bed=uti_bed,
            admitted_at=datetime(2026, 8, 10, 8, 30, tzinfo=timezone.utc),
            destination_service=service_by_code["MED"],
        )
    )
    ensure_transfer(
        admission=pending_reception_admission,
        key="traslado pendiente recepción",
        origin_service=pending_reception_origin,
        destination_service=service_by_code["MED"],
        origin_bed=pending_reception_bed,
        final_status="pending_reception",
        history_statuses=("requested", "pending_reception"),
        requested_at=datetime(2026, 8, 10, 9, 0, tzinfo=timezone.utc),
    )
    pending_bed_admission, pending_bed_origin_bed, pending_bed_origin = (
        open_seed_admission(
            base_admission=active_uci,
            identifier_prefix="ADM-DEMO-P7-OPEN-BED",
            patient_identifier_prefix="NN-P7-BED",
            preferred_bed=uci_bed,
            admitted_at=datetime(2026, 8, 11, 8, 30, tzinfo=timezone.utc),
            destination_service=service_by_code["MED"],
        )
    )
    ensure_transfer(
        admission=pending_bed_admission,
        key="traslado aceptado pendiente de cama",
        origin_service=pending_bed_origin,
        destination_service=service_by_code["MED"],
        origin_bed=pending_bed_origin_bed,
        final_status="pending_bed",
        history_statuses=("requested", "pending_reception", "accepted", "pending_bed"),
        requested_at=datetime(2026, 8, 11, 9, 0, tzinfo=timezone.utc),
    )
    session.commit()

def main() -> None:
    with Session(engine) as session:
        seed_database(session)
    print("Phase 5 demo identity, hospital structure, patients, and admissions are ready.")


if __name__ == "__main__":
    main()
