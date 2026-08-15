import uuid

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models.admission import Admission
from app.models.allergy import (
    AllergyIntoleranceReaction,
    AllergyIntoleranceStatusHistory,
    PatientAllergyIntolerance,
    PatientAllergyReviewAssertion,
)
from app.models.common import utc_now
from app.schemas.allergy import (
    AllergyContextRead,
    AllergyIntoleranceBulkCreate,
    AllergyIntoleranceRead,
    AllergyReactionCreate,
    AllergyReactionRead,
    AllergyReviewAssertionCreate,
    AllergyReviewAssertionRead,
    AllergyStatusHistoryRead,
    AllergyStatusUpdate,
    FoodSafetyAllergyProjection,
    FoodSafetyAllergyRead,
    FoodSafetyReactionRead,
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
        raise _conflict("No fue posible guardar el registro de alergia por un conflicto.") from exc


def _admission(session: Session, admission_id: uuid.UUID, *, editable: bool = False) -> Admission:
    admission = session.get(Admission, admission_id)
    if admission is None:
        raise _not_found("Hospitalización")
    if editable and admission.status != "active":
        raise _conflict("Un episodio histórico es de solo lectura.")
    return admission


def _normalized(value: str) -> str:
    return " ".join(value.casefold().split())


def _read_item(session: Session, row: PatientAllergyIntolerance) -> AllergyIntoleranceRead:
    reactions = session.exec(
        select(AllergyIntoleranceReaction)
        .where(AllergyIntoleranceReaction.allergy_intolerance_id == row.id)
        .order_by(AllergyIntoleranceReaction.occurred_at.desc(), AllergyIntoleranceReaction.created_at.desc())
    ).all()
    history = session.exec(
        select(AllergyIntoleranceStatusHistory)
        .where(AllergyIntoleranceStatusHistory.allergy_intolerance_id == row.id)
        .order_by(AllergyIntoleranceStatusHistory.sequence_number)
    ).all()
    result = AllergyIntoleranceRead.model_validate(row)
    result.reactions = [AllergyReactionRead.model_validate(item) for item in reactions]
    result.history = [AllergyStatusHistoryRead.model_validate(item) for item in history]
    return result


def read_allergy_context(session: Session, admission_id: uuid.UUID) -> AllergyContextRead:
    admission = _admission(session, admission_id)
    items = session.exec(
        select(PatientAllergyIntolerance)
        .where(PatientAllergyIntolerance.patient_id == admission.patient_id)
        .order_by(PatientAllergyIntolerance.created_at.desc())
    ).all()
    assertions = session.exec(
        select(PatientAllergyReviewAssertion)
        .where(PatientAllergyReviewAssertion.patient_id == admission.patient_id)
        .order_by(PatientAllergyReviewAssertion.recorded_at.desc())
    ).all()
    return AllergyContextRead(
        admission_id=admission.id,
        patient_id=admission.patient_id,
        items=[_read_item(session, row) for row in items],
        review_assertions=[AllergyReviewAssertionRead.model_validate(row) for row in assertions],
    )


def _add_reviewed_with_findings(
    session: Session,
    admission: Admission,
    categories: set[str],
    source: str,
    actor_id: uuid.UUID,
    now,
) -> None:
    for category in sorted(categories):
        session.add(PatientAllergyReviewAssertion(
            patient_id=admission.patient_id,
            admission_id=admission.id,
            category=category,
            assertion="reviewed_with_findings",
            source=source,
            note=None,
            recorded_by_user_id=actor_id,
            recorded_at=now,
        ))


def create_allergies(
    session: Session,
    admission_id: uuid.UUID,
    payload: AllergyIntoleranceBulkCreate,
    actor_id: uuid.UUID,
) -> list[AllergyIntoleranceRead]:
    admission = _admission(session, admission_id, editable=True)
    supplied = [(_normalized(item.substance_name), item.category.value) for item in payload.items]
    if len(supplied) != len(set(supplied)):
        raise _conflict("La lista contiene alergias o intolerancias duplicadas.")
    existing = session.exec(
        select(PatientAllergyIntolerance).where(
            PatientAllergyIntolerance.patient_id == admission.patient_id,
            PatientAllergyIntolerance.verification_status != "entered_in_error",
        )
    ).all()
    existing_keys = {(_normalized(row.substance_name), row.category) for row in existing}
    duplicate = next(
        (item.substance_name for item in payload.items if (_normalized(item.substance_name), item.category.value) in existing_keys),
        None,
    )
    if duplicate:
        raise _conflict(f"'{duplicate}' ya está registrado para este paciente.")

    now = utc_now()
    rows: list[PatientAllergyIntolerance] = []
    category_sources: dict[str, str] = {}
    for item in payload.items:
        data = item.model_dump(mode="python")
        reactions = data.pop("reactions")
        row = PatientAllergyIntolerance(
            patient_id=admission.patient_id,
            asserted_admission_id=admission.id,
            **data,
            created_by_user_id=actor_id,
            updated_by_user_id=actor_id,
            created_at=now,
            updated_at=now,
        )
        session.add(row)
        session.flush()
        for reaction in reactions:
            session.add(AllergyIntoleranceReaction(
                allergy_intolerance_id=row.id,
                **reaction,
                created_by_user_id=actor_id,
                created_at=now,
            ))
        session.add(AllergyIntoleranceStatusHistory(
            allergy_intolerance_id=row.id,
            sequence_number=1,
            to_clinical_status=row.clinical_status,
            to_verification_status=row.verification_status,
            to_criticality=row.criticality,
            reason="Registro inicial de alergia o intolerancia.",
            source=row.source,
            changed_by_user_id=actor_id,
            changed_at=now,
            version=1,
        ))
        record_audit(
            session,
            action="allergy_intolerance_created",
            actor_user_id=actor_id,
            entity_type="patient_allergy_intolerance",
            entity_id=row.id,
            admission_id=admission.id,
            after_state={
                "category": row.category,
                "clinical_status": row.clinical_status,
                "verification_status": row.verification_status,
                "criticality": row.criticality,
                "version": 1,
            },
        )
        rows.append(row)
        category_sources.setdefault(row.category, row.source)
    for category, source in category_sources.items():
        _add_reviewed_with_findings(session, admission, {category}, source, actor_id, now)
    _commit(session)
    return [_read_item(session, row) for row in rows]


def update_allergy_status(
    session: Session,
    allergy_id: uuid.UUID,
    payload: AllergyStatusUpdate,
    actor_id: uuid.UUID,
) -> AllergyIntoleranceRead:
    row = session.exec(
        select(PatientAllergyIntolerance)
        .where(PatientAllergyIntolerance.id == allergy_id)
        .with_for_update()
    ).first()
    if row is None:
        raise _not_found("Alergia o intolerancia")
    if row.version != payload.version:
        raise _conflict("El registro fue actualizado por otro usuario. Recargue la ficha.")
    previous = (row.clinical_status, row.verification_status, row.criticality)
    row.clinical_status = payload.clinical_status.value if payload.clinical_status else None
    row.verification_status = payload.verification_status.value
    row.criticality = payload.criticality.value
    row.source = payload.source.value
    row.version += 1
    row.updated_by_user_id = actor_id
    row.updated_at = utc_now()
    session.add(row)
    session.add(AllergyIntoleranceStatusHistory(
        allergy_intolerance_id=row.id,
        sequence_number=row.version,
        from_clinical_status=previous[0],
        to_clinical_status=row.clinical_status,
        from_verification_status=previous[1],
        to_verification_status=row.verification_status,
        from_criticality=previous[2],
        to_criticality=row.criticality,
        reason=payload.reason,
        source=row.source,
        changed_by_user_id=actor_id,
        changed_at=row.updated_at,
        version=row.version,
    ))
    record_audit(
        session,
        action="allergy_intolerance_status_changed",
        actor_user_id=actor_id,
        entity_type="patient_allergy_intolerance",
        entity_id=row.id,
        admission_id=row.asserted_admission_id,
        before_state={"clinical_status": previous[0], "verification_status": previous[1], "criticality": previous[2], "version": payload.version},
        after_state={"clinical_status": row.clinical_status, "verification_status": row.verification_status, "criticality": row.criticality, "version": row.version},
    )
    _commit(session)
    return _read_item(session, row)


def add_reaction(
    session: Session,
    allergy_id: uuid.UUID,
    payload: AllergyReactionCreate,
    actor_id: uuid.UUID,
) -> AllergyIntoleranceRead:
    row = session.get(PatientAllergyIntolerance, allergy_id)
    if row is None:
        raise _not_found("Alergia o intolerancia")
    reaction = AllergyIntoleranceReaction(
        allergy_intolerance_id=row.id,
        **payload.model_dump(mode="python"),
        created_by_user_id=actor_id,
    )
    session.add(reaction)
    record_audit(
        session,
        action="allergy_intolerance_reaction_added",
        actor_user_id=actor_id,
        entity_type="patient_allergy_intolerance",
        entity_id=row.id,
        admission_id=row.asserted_admission_id,
        after_state={"reaction_added": True, "version": row.version},
    )
    _commit(session)
    return _read_item(session, row)


def create_review_assertion(
    session: Session,
    admission_id: uuid.UUID,
    payload: AllergyReviewAssertionCreate,
    actor_id: uuid.UUID,
) -> AllergyReviewAssertionRead:
    admission = _admission(session, admission_id, editable=True)
    category = payload.category.value
    if payload.assertion.value == "no_known":
        statement = select(PatientAllergyIntolerance).where(
            PatientAllergyIntolerance.patient_id == admission.patient_id,
            PatientAllergyIntolerance.clinical_status == "active",
            PatientAllergyIntolerance.verification_status.notin_(("refuted", "entered_in_error")),
        )
        if category != "all":
            statement = statement.where(PatientAllergyIntolerance.category == category)
        if session.exec(statement).first() is not None:
            raise _conflict("No puede declarar ausencia mientras existan registros activos en esa categoría.")
    row = PatientAllergyReviewAssertion(
        patient_id=admission.patient_id,
        admission_id=admission.id,
        **payload.model_dump(mode="python"),
        recorded_by_user_id=actor_id,
    )
    session.add(row)
    session.flush()
    record_audit(
        session,
        action="allergy_review_assertion_recorded",
        actor_user_id=actor_id,
        entity_type="patient_allergy_review_assertion",
        entity_id=row.id,
        admission_id=admission.id,
        after_state={"category": row.category, "assertion": row.assertion},
    )
    _commit(session)
    return AllergyReviewAssertionRead.model_validate(row)


def food_safety_projection(session: Session, admission_id: uuid.UUID) -> FoodSafetyAllergyProjection:
    admission = _admission(session, admission_id)
    rows = session.exec(
        select(PatientAllergyIntolerance).where(
            PatientAllergyIntolerance.patient_id == admission.patient_id,
            PatientAllergyIntolerance.category == "food",
            PatientAllergyIntolerance.clinical_status == "active",
            PatientAllergyIntolerance.verification_status.notin_(("refuted", "entered_in_error")),
        ).order_by(PatientAllergyIntolerance.criticality, PatientAllergyIntolerance.substance_name)
    ).all()
    items: list[FoodSafetyAllergyRead] = []
    for row in rows:
        reactions = session.exec(
            select(AllergyIntoleranceReaction)
            .where(AllergyIntoleranceReaction.allergy_intolerance_id == row.id)
            .order_by(AllergyIntoleranceReaction.created_at.desc())
        ).all()
        items.append(FoodSafetyAllergyRead(
            id=row.id,
            substance_name=row.substance_name,
            allergy_type=row.allergy_type,
            criticality=row.criticality,
            reactions=[FoodSafetyReactionRead(manifestation=item.manifestation, severity=item.severity) for item in reactions],
        ))
    if items:
        review_status = "active_food_risks"
    else:
        assertion = session.exec(
            select(PatientAllergyReviewAssertion).where(
                PatientAllergyReviewAssertion.patient_id == admission.patient_id,
                PatientAllergyReviewAssertion.admission_id == admission.id,
                PatientAllergyReviewAssertion.category.in_(("food", "all")),
            ).order_by(PatientAllergyReviewAssertion.recorded_at.desc())
        ).first()
        review_status = {
            "no_known": "no_known",
            "information_unavailable": "information_unavailable",
            "not_asked": "not_reviewed",
            "reviewed_with_findings": "no_active_food_risks",
        }.get(assertion.assertion if assertion else "not_asked", "not_reviewed")
    return FoodSafetyAllergyProjection(
        admission_id=admission.id,
        review_status=review_status,
        items=items,
    )
