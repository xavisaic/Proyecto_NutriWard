import uuid
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models.admission import Admission
from app.models.clinical_context import (
    AdmissionClinicalHistoryVersion,
    AdmissionDiagnosis,
    AdmissionDiagnosisStatusHistory,
    PatientCondition,
    PatientConditionStatusHistory,
)
from app.models.common import utc_now
from app.models.patient import Patient
from app.models.user import User
from app.schemas.clinical_context import (
    AdmissionClinicalHistoryCreate,
    AdmissionClinicalHistoryRead,
    AdmissionClinicalHistoryUpdate,
    AdmissionClinicalHistoryVersionRead,
    AdmissionDiagnosisBulkCreate,
    AdmissionDiagnosisRead,
    ClinicalContextRead,
    ConditionStatusUpdate,
    DiagnosisStatusUpdate,
    PatientConditionBulkCreate,
    PatientConditionRead,
    StatusHistoryRead,
)
from app.services.audit_service import record_audit


def _not_found(label: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{label} no encontrado.")


def _conflict(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


def _commit(session: Session) -> None:
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise _conflict("No fue posible guardar el registro clínico por un conflicto de datos.") from exc


def _admission(session: Session, admission_id: uuid.UUID, *, editable: bool = False) -> Admission:
    admission = session.get(Admission, admission_id)
    if admission is None:
        raise _not_found("Hospitalización")
    if editable and admission.status != "active":
        raise _conflict("Un episodio histórico es de solo lectura.")
    return admission


def _patient(session: Session, patient_id: uuid.UUID) -> Patient:
    patient = session.get(Patient, patient_id)
    if patient is None or not patient.is_active:
        raise _not_found("Paciente")
    return patient


def _normalized(value: str) -> str:
    return " ".join(value.casefold().split())


def _validate_history_start_date(
    admission: Admission, event_start_date: date | None
) -> None:
    if event_start_date and event_start_date > admission.admitted_at.date():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "El inicio de los acontecimientos no puede ser posterior al ingreso "
                "hospitalario."
            ),
        )


def _condition_read(session: Session, row: PatientCondition) -> PatientConditionRead:
    history = session.exec(
        select(PatientConditionStatusHistory)
        .where(PatientConditionStatusHistory.patient_condition_id == row.id)
        .order_by(PatientConditionStatusHistory.sequence_number)
    ).all()
    result = PatientConditionRead.model_validate(row)
    result.history = [StatusHistoryRead.model_validate(item) for item in history]
    return result


def _diagnosis_read(session: Session, row: AdmissionDiagnosis) -> AdmissionDiagnosisRead:
    history = session.exec(
        select(AdmissionDiagnosisStatusHistory)
        .where(AdmissionDiagnosisStatusHistory.admission_diagnosis_id == row.id)
        .order_by(AdmissionDiagnosisStatusHistory.sequence_number)
    ).all()
    result = AdmissionDiagnosisRead.model_validate(row)
    result.history = [StatusHistoryRead.model_validate(item) for item in history]
    return result


def _clinical_history_read(
    session: Session, admission_id: uuid.UUID
) -> AdmissionClinicalHistoryRead | None:
    rows = list(
        session.exec(
            select(AdmissionClinicalHistoryVersion)
            .where(AdmissionClinicalHistoryVersion.admission_id == admission_id)
            .order_by(AdmissionClinicalHistoryVersion.version)
        ).all()
    )
    if not rows:
        return None
    versions: list[AdmissionClinicalHistoryVersionRead] = []
    for row in rows:
        author = session.get(User, row.recorded_by_user_id)
        versions.append(
            AdmissionClinicalHistoryVersionRead(
                **row.model_dump(),
                author_name=author.full_name if author else "Profesional no disponible",
            )
        )
    return AdmissionClinicalHistoryRead(
        admission_id=admission_id,
        current=versions[-1],
        versions=versions,
    )


def read_clinical_context(session: Session, admission_id: uuid.UUID) -> ClinicalContextRead:
    admission = _admission(session, admission_id)
    diagnoses = session.exec(
        select(AdmissionDiagnosis)
        .where(AdmissionDiagnosis.admission_id == admission.id)
        .order_by(AdmissionDiagnosis.diagnosed_at.desc(), AdmissionDiagnosis.created_at.desc())
    ).all()
    conditions = session.exec(
        select(PatientCondition)
        .where(PatientCondition.patient_id == admission.patient_id)
        .order_by(PatientCondition.created_at.desc())
    ).all()
    return ClinicalContextRead(
        admission_id=admission.id,
        patient_id=admission.patient_id,
        episode_history=_clinical_history_read(session, admission.id),
        diagnoses=[_diagnosis_read(session, row) for row in diagnoses],
        conditions=[_condition_read(session, row) for row in conditions],
    )


def create_clinical_history(
    session: Session,
    admission_id: uuid.UUID,
    payload: AdmissionClinicalHistoryCreate,
    actor_id: uuid.UUID,
) -> AdmissionClinicalHistoryRead:
    admission = _admission(session, admission_id, editable=True)
    _validate_history_start_date(admission, payload.event_start_date)
    existing = session.exec(
        select(AdmissionClinicalHistoryVersion.id).where(
            AdmissionClinicalHistoryVersion.admission_id == admission.id
        )
    ).first()
    if existing is not None:
        raise _conflict(
            "La historia del episodio ya existe. Recargue la ficha para actualizarla."
        )
    row = AdmissionClinicalHistoryVersion(
        admission_id=admission.id,
        version=1,
        narrative=payload.narrative,
        event_start_date=payload.event_start_date,
        source=payload.source.value,
        change_reason=None,
        recorded_by_user_id=actor_id,
        recorded_at=utc_now(),
    )
    session.add(row)
    session.flush()
    record_audit(
        session,
        action="admission_clinical_history_created",
        actor_user_id=actor_id,
        entity_type="admission_clinical_history_version",
        entity_id=row.id,
        admission_id=admission.id,
        after_state={"version": 1},
    )
    _commit(session)
    result = _clinical_history_read(session, admission.id)
    assert result is not None
    return result


def update_clinical_history(
    session: Session,
    admission_id: uuid.UUID,
    payload: AdmissionClinicalHistoryUpdate,
    actor_id: uuid.UUID,
) -> AdmissionClinicalHistoryRead:
    admission = _admission(session, admission_id, editable=True)
    _validate_history_start_date(admission, payload.event_start_date)
    current = session.exec(
        select(AdmissionClinicalHistoryVersion)
        .where(AdmissionClinicalHistoryVersion.admission_id == admission.id)
        .order_by(AdmissionClinicalHistoryVersion.version.desc())
        .with_for_update()
    ).first()
    if current is None:
        raise _not_found("Historia del episodio")
    if current.version != payload.version:
        raise _conflict(
            "La historia del episodio fue actualizada por otro usuario. Recargue la ficha."
        )
    row = AdmissionClinicalHistoryVersion(
        admission_id=admission.id,
        version=current.version + 1,
        narrative=payload.narrative,
        event_start_date=payload.event_start_date,
        source=payload.source.value,
        change_reason=payload.change_reason,
        recorded_by_user_id=actor_id,
        recorded_at=utc_now(),
    )
    session.add(row)
    session.flush()
    record_audit(
        session,
        action="admission_clinical_history_updated",
        actor_user_id=actor_id,
        entity_type="admission_clinical_history_version",
        entity_id=row.id,
        admission_id=admission.id,
        before_state={"version": current.version},
        after_state={"version": row.version},
    )
    _commit(session)
    result = _clinical_history_read(session, admission.id)
    assert result is not None
    return result


def create_conditions(
    session: Session,
    patient_id: uuid.UUID,
    payload: PatientConditionBulkCreate,
    actor_id: uuid.UUID,
) -> list[PatientConditionRead]:
    _patient(session, patient_id)
    supplied = [_normalized(item.condition_name) for item in payload.items]
    if len(supplied) != len(set(supplied)):
        raise _conflict("La lista contiene antecedentes duplicados.")
    existing = session.exec(
        select(PatientCondition).where(
            PatientCondition.patient_id == patient_id,
            PatientCondition.clinical_status != "entered_in_error",
        )
    ).all()
    existing_names = {_normalized(row.condition_name) for row in existing}
    duplicate = next(
        (
            item.condition_name
            for item in payload.items
            if _normalized(item.condition_name) in existing_names
        ),
        None,
    )
    if duplicate:
        raise _conflict(f"El antecedente '{duplicate}' ya está registrado para este paciente.")

    now = utc_now()
    rows: list[PatientCondition] = []
    for item in payload.items:
        data = item.model_dump(mode="python")
        row = PatientCondition(
            patient_id=patient_id,
            **data,
            created_by_user_id=actor_id,
            updated_by_user_id=actor_id,
            created_at=now,
            updated_at=now,
        )
        session.add(row)
        session.flush()
        session.add(PatientConditionStatusHistory(
            patient_condition_id=row.id,
            sequence_number=1,
            to_clinical_status=row.clinical_status,
            to_verification_status=row.verification_status,
            reason="Registro inicial del antecedente.",
            source=row.source,
            changed_by_user_id=actor_id,
            changed_at=now,
            version=1,
        ))
        record_audit(
            session,
            action="patient_condition_created",
            actor_user_id=actor_id,
            entity_type="patient_condition",
            entity_id=row.id,
            after_state={
                "clinical_status": row.clinical_status,
                "verification_status": row.verification_status,
                "version": 1,
            },
        )
        rows.append(row)
    _commit(session)
    return [_condition_read(session, row) for row in rows]


def create_diagnoses(
    session: Session,
    admission_id: uuid.UUID,
    payload: AdmissionDiagnosisBulkCreate,
    actor_id: uuid.UUID,
) -> list[AdmissionDiagnosisRead]:
    admission = _admission(session, admission_id, editable=True)
    supplied = [_normalized(item.diagnosis_name) for item in payload.items]
    if len(supplied) != len(set(supplied)):
        raise _conflict("La lista contiene diagnósticos duplicados.")
    existing = session.exec(
        select(AdmissionDiagnosis).where(
            AdmissionDiagnosis.admission_id == admission_id,
            AdmissionDiagnosis.clinical_status != "entered_in_error",
        )
    ).all()
    existing_names = {_normalized(row.diagnosis_name) for row in existing}
    duplicate = next(
        (
            item.diagnosis_name
            for item in payload.items
            if _normalized(item.diagnosis_name) in existing_names
        ),
        None,
    )
    if duplicate:
        raise _conflict(f"El diagnóstico '{duplicate}' ya está registrado en esta hospitalización.")

    now = utc_now()
    rows: list[AdmissionDiagnosis] = []
    for item in payload.items:
        data = item.model_dump(mode="python")
        diagnosed_at = data.pop("diagnosed_at", None) or now
        row = AdmissionDiagnosis(
            admission_id=admission.id,
            **data,
            diagnosed_at=diagnosed_at,
            created_by_user_id=actor_id,
            updated_by_user_id=actor_id,
            created_at=now,
            updated_at=now,
        )
        session.add(row)
        session.flush()
        session.add(AdmissionDiagnosisStatusHistory(
            admission_diagnosis_id=row.id,
            sequence_number=1,
            to_clinical_status=row.clinical_status,
            to_verification_status=row.verification_status,
            reason="Registro inicial del diagnóstico.",
            source=row.source,
            changed_by_user_id=actor_id,
            changed_at=now,
            version=1,
        ))
        record_audit(
            session,
            action="admission_diagnosis_created",
            actor_user_id=actor_id,
            entity_type="admission_diagnosis",
            entity_id=row.id,
            admission_id=admission.id,
            after_state={
                "clinical_status": row.clinical_status,
                "verification_status": row.verification_status,
                "version": 1,
            },
        )
        rows.append(row)
    _commit(session)
    return [_diagnosis_read(session, row) for row in rows]


def update_condition_status(
    session: Session,
    condition_id: uuid.UUID,
    payload: ConditionStatusUpdate,
    actor_id: uuid.UUID,
) -> PatientConditionRead:
    row = session.exec(
        select(PatientCondition)
        .where(PatientCondition.id == condition_id)
        .with_for_update()
    ).first()
    if row is None:
        raise _not_found("Antecedente")
    if row.version != payload.version:
        raise _conflict("El antecedente fue actualizado por otro usuario. Recargue la ficha.")
    previous_status = row.clinical_status
    previous_verification = row.verification_status
    row.clinical_status = payload.clinical_status.value
    row.verification_status = payload.verification_status.value
    row.resolved_on = (
        payload.resolved_on or row.resolved_on or utc_now().date()
        if row.clinical_status == "resolved"
        else None
    )
    row.source = payload.source.value
    row.version += 1
    row.updated_by_user_id = actor_id
    row.updated_at = utc_now()
    session.add(row)
    session.add(PatientConditionStatusHistory(
        patient_condition_id=row.id,
        sequence_number=row.version,
        from_clinical_status=previous_status,
        to_clinical_status=row.clinical_status,
        from_verification_status=previous_verification,
        to_verification_status=row.verification_status,
        reason=payload.reason,
        source=row.source,
        changed_by_user_id=actor_id,
        changed_at=row.updated_at,
        version=row.version,
    ))
    record_audit(
        session,
        action="patient_condition_status_changed",
        actor_user_id=actor_id,
        entity_type="patient_condition",
        entity_id=row.id,
        before_state={
            "clinical_status": previous_status,
            "verification_status": previous_verification,
            "version": payload.version,
        },
        after_state={
            "clinical_status": row.clinical_status,
            "verification_status": row.verification_status,
            "version": row.version,
        },
    )
    _commit(session)
    return _condition_read(session, row)


def update_diagnosis_status(
    session: Session,
    diagnosis_id: uuid.UUID,
    payload: DiagnosisStatusUpdate,
    actor_id: uuid.UUID,
) -> AdmissionDiagnosisRead:
    row = session.exec(
        select(AdmissionDiagnosis)
        .where(AdmissionDiagnosis.id == diagnosis_id)
        .with_for_update()
    ).first()
    if row is None:
        raise _not_found("Diagnóstico")
    _admission(session, row.admission_id, editable=True)
    if row.version != payload.version:
        raise _conflict("El diagnóstico fue actualizado por otro usuario. Recargue la ficha.")
    previous_status = row.clinical_status
    previous_verification = row.verification_status
    row.clinical_status = payload.clinical_status.value
    row.verification_status = payload.verification_status.value
    row.resolved_at = (
        payload.resolved_at or row.resolved_at or utc_now()
        if row.clinical_status == "resolved"
        else None
    )
    row.source = payload.source.value
    row.version += 1
    row.updated_by_user_id = actor_id
    row.updated_at = utc_now()
    session.add(row)
    session.add(AdmissionDiagnosisStatusHistory(
        admission_diagnosis_id=row.id,
        sequence_number=row.version,
        from_clinical_status=previous_status,
        to_clinical_status=row.clinical_status,
        from_verification_status=previous_verification,
        to_verification_status=row.verification_status,
        reason=payload.reason,
        source=row.source,
        changed_by_user_id=actor_id,
        changed_at=row.updated_at,
        version=row.version,
    ))
    record_audit(
        session,
        action="admission_diagnosis_status_changed",
        actor_user_id=actor_id,
        entity_type="admission_diagnosis",
        entity_id=row.id,
        admission_id=row.admission_id,
        before_state={
            "clinical_status": previous_status,
            "verification_status": previous_verification,
            "version": payload.version,
        },
        after_state={
            "clinical_status": row.clinical_status,
            "verification_status": row.verification_status,
            "version": row.version,
        },
    )
    _commit(session)
    return _diagnosis_read(session, row)
