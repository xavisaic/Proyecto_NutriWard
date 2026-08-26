import uuid
from collections import defaultdict
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models.admission import Admission
from app.models.common import utc_now
from app.models.treatment import (
    AdmissionTreatment,
    AdmissionTreatmentReview,
    AdmissionTreatmentVersion,
    MedicationCatalogItem,
)
from app.models.user import User
from app.schemas.treatment import (
    TreatmentBulkCreate,
    TreatmentBulkRead,
    TreatmentCategory,
    TreatmentContextRead,
    TreatmentCounts,
    TreatmentCreate,
    TreatmentImpactItem,
    TreatmentImpactSummary,
    TreatmentRead,
    TreatmentReviewCreate,
    TreatmentReviewRead,
    TreatmentUpdate,
    TreatmentVersionRead,
)
from app.services.audit_service import record_audit
from app.services.medication_catalog_service import get_catalog_item


CURRENT_STATUSES = {"draft", "active", "on_hold", "unknown"}


def _not_found(label: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{label} no encontrado.")


def _conflict(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


def _commit(session: Session) -> None:
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise _conflict("No fue posible guardar el tratamiento por un conflicto.") from exc


def _admission(session: Session, admission_id: uuid.UUID, *, editable: bool = False) -> Admission:
    admission = session.get(Admission, admission_id)
    if admission is None:
        raise _not_found("Hospitalización")
    if editable and admission.status != "active":
        raise _conflict("Un episodio histórico es de solo lectura.")
    return admission


def _user_name(session: Session, user_id: uuid.UUID | None) -> str | None:
    if user_id is None:
        return None
    user = session.get(User, user_id)
    if user is None:
        return None
    return user.full_name


def _version_read(session: Session, row: AdmissionTreatmentVersion) -> TreatmentVersionRead:
    result = TreatmentVersionRead.model_validate(row)
    result.author_name = _user_name(session, row.created_by_user_id) or "Usuario no disponible"
    result.verifier_name = _user_name(session, row.verified_by_user_id)
    if row.medication_catalog_code:
        catalog = session.get(MedicationCatalogItem, row.medication_catalog_code)
        if catalog is not None:
            result.medication_catalog = catalog
    if (
        row.rate_value is not None
        and row.rate_unit
        and row.rate_unit.casefold().replace(" ", "") == "ml/h"
        and row.infusion_duration_hours is not None
    ):
        result.estimated_volume_ml = (
            row.rate_value * row.infusion_duration_hours
        ).quantize(Decimal("0.01"))
    return result


def _versions_by_treatment(
    session: Session, treatment_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[AdmissionTreatmentVersion]]:
    grouped: dict[uuid.UUID, list[AdmissionTreatmentVersion]] = defaultdict(list)
    if not treatment_ids:
        return grouped
    rows = session.exec(
        select(AdmissionTreatmentVersion)
        .where(AdmissionTreatmentVersion.treatment_id.in_(treatment_ids))
        .order_by(
            AdmissionTreatmentVersion.treatment_id,
            AdmissionTreatmentVersion.version.desc(),
        )
    ).all()
    for row in rows:
        grouped[row.treatment_id].append(row)
    return grouped


def _treatment_read(
    session: Session,
    row: AdmissionTreatment,
    versions: list[AdmissionTreatmentVersion] | None = None,
) -> TreatmentRead:
    if versions is None:
        versions = list(
            session.exec(
                select(AdmissionTreatmentVersion)
                .where(AdmissionTreatmentVersion.treatment_id == row.id)
                .order_by(AdmissionTreatmentVersion.version.desc())
            ).all()
        )
    if not versions:
        raise _conflict("El tratamiento no tiene una versión clínica válida.")
    history = [_version_read(session, item) for item in versions]
    return TreatmentRead(
        id=row.id,
        admission_id=row.admission_id,
        kind=row.kind,
        created_by_user_id=row.created_by_user_id,
        created_at=row.created_at,
        current=history[0],
        history=history,
    )


def _review_read(session: Session, row: AdmissionTreatmentReview) -> TreatmentReviewRead:
    result = TreatmentReviewRead.model_validate(row)
    result.author_name = _user_name(session, row.recorded_by_user_id) or "Usuario no disponible"
    return result


def read_treatment_context(session: Session, admission_id: uuid.UUID) -> TreatmentContextRead:
    _admission(session, admission_id)
    treatments = list(
        session.exec(
            select(AdmissionTreatment)
            .where(AdmissionTreatment.admission_id == admission_id)
            .order_by(AdmissionTreatment.created_at.desc(), AdmissionTreatment.id)
        ).all()
    )
    grouped = _versions_by_treatment(session, [row.id for row in treatments])
    items = [_treatment_read(session, row, grouped[row.id]) for row in treatments]
    items.sort(key=lambda item: (item.current.observed_at, str(item.id)), reverse=True)
    review = session.exec(
        select(AdmissionTreatmentReview)
        .where(AdmissionTreatmentReview.admission_id == admission_id)
        .order_by(AdmissionTreatmentReview.recorded_at.desc(), AdmissionTreatmentReview.id.desc())
    ).first()
    active = sum(item.current.order_status == "active" for item in items)
    on_hold = sum(item.current.order_status == "on_hold" for item in items)
    pending = sum(item.current.verification_status != "verified" for item in items if item.current.order_status in CURRENT_STATUSES)
    historical = sum(item.current.order_status not in CURRENT_STATUSES for item in items)
    return TreatmentContextRead(
        admission_id=admission_id,
        review_status=review.assertion if review else "not_reviewed",
        latest_review=_review_read(session, review) if review else None,
        items=items,
        counts=TreatmentCounts(
            active=active,
            on_hold=on_hold,
            pending_verification=pending,
            historical=historical,
        ),
    )


def get_treatment(session: Session, treatment_id: uuid.UUID) -> TreatmentRead:
    row = session.get(AdmissionTreatment, treatment_id)
    if row is None:
        raise _not_found("Tratamiento")
    return _treatment_read(session, row)


def _version_values(payload: TreatmentCreate | TreatmentUpdate, actor_id: uuid.UUID) -> dict:
    data = payload.model_dump(mode="python", exclude={"kind", "expected_version", "change_reason"})
    verified = payload.verification_status.value == "verified"
    data.update(
        verified_at=utc_now() if verified else None,
        verified_by_user_id=actor_id if verified else None,
    )
    return data


def create_treatment(
    session: Session,
    admission_id: uuid.UUID,
    payload: TreatmentCreate,
    actor_id: uuid.UUID,
) -> TreatmentRead:
    _admission(session, admission_id, editable=True)
    payload = _catalog_payload(session, payload)
    context = read_treatment_context(session, admission_id)
    duplicate = next(
        (
            item
            for item in context.items
            if item.current.order_status in CURRENT_STATUSES
            and item.current.name.casefold() == payload.name.casefold()
        ),
        None,
    )
    if duplicate:
        raise _conflict(
            f"'{payload.name}' ya tiene un registro vigente. Actualice su versión existente."
        )
    now = utc_now()
    treatment = AdmissionTreatment(
        admission_id=admission_id,
        kind=payload.kind.value,
        created_by_user_id=actor_id,
        created_at=now,
    )
    session.add(treatment)
    session.flush()
    version = AdmissionTreatmentVersion(
        treatment_id=treatment.id,
        version=1,
        change_reason="Registro inicial del tratamiento.",
        created_by_user_id=actor_id,
        created_at=now,
        **_version_values(payload, actor_id),
    )
    session.add(version)
    review = AdmissionTreatmentReview(
        admission_id=admission_id,
        assertion="reviewed_with_findings",
        source_type=payload.source_type,
        note=None,
        recorded_by_user_id=actor_id,
        recorded_at=now,
    )
    session.add(review)
    record_audit(
        session,
        action="admission_treatment_created",
        actor_user_id=actor_id,
        entity_type="admission_treatment",
        entity_id=treatment.id,
        admission_id=admission_id,
        after_state={"version": 1, "status": payload.order_status.value},
    )
    _commit(session)
    session.refresh(treatment)
    return get_treatment(session, treatment.id)


def _catalog_payload(
    session: Session, payload: TreatmentCreate
) -> TreatmentCreate:
    if not payload.medication_catalog_code:
        return payload
    catalog = get_catalog_item(session, payload.medication_catalog_code)
    if catalog is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La presentación seleccionada no está disponible en el arsenal vigente.",
        )
    category = payload.category
    if category == TreatmentCategory.OTHER and catalog.default_category != "other":
        category = TreatmentCategory(catalog.default_category)
    return payload.model_copy(
        update={
            "name": catalog.display_name,
            "route": payload.route or catalog.route,
            "category": category,
        }
    )


def create_treatments_bulk(
    session: Session,
    admission_id: uuid.UUID,
    payload: TreatmentBulkCreate,
    actor_id: uuid.UUID,
) -> TreatmentBulkRead:
    _admission(session, admission_id, editable=True)
    context = read_treatment_context(session, admission_id)
    current_items = [
        item for item in context.items if item.current.order_status in CURRENT_STATUSES
    ]
    existing_names = {item.current.name.casefold() for item in current_items}
    existing_codes = {
        item.current.medication_catalog_code
        for item in current_items
        if item.current.medication_catalog_code
    }

    prepared = [_catalog_payload(session, item) for item in payload.items]
    new_names: set[str] = set()
    new_codes: set[str] = set()
    for item in prepared:
        name_key = item.name.casefold()
        code = item.medication_catalog_code
        if name_key in existing_names or (code and code in existing_codes):
            raise _conflict(
                f"'{item.name}' ya tiene un registro vigente. Actualice su versión existente."
            )
        if name_key in new_names or (code and code in new_codes):
            raise _conflict(f"'{item.name}' está repetido en la lista.")
        new_names.add(name_key)
        if code:
            new_codes.add(code)

    now = utc_now()
    treatment_ids: list[uuid.UUID] = []
    for item in prepared:
        treatment = AdmissionTreatment(
            admission_id=admission_id,
            kind=item.kind.value,
            created_by_user_id=actor_id,
            created_at=now,
        )
        session.add(treatment)
        session.flush()
        treatment_ids.append(treatment.id)
        session.add(
            AdmissionTreatmentVersion(
                treatment_id=treatment.id,
                version=1,
                change_reason="Registro inicial del tratamiento.",
                created_by_user_id=actor_id,
                created_at=now,
                **_version_values(item, actor_id),
            )
        )
        record_audit(
            session,
            action="admission_treatment_created",
            actor_user_id=actor_id,
            entity_type="admission_treatment",
            entity_id=treatment.id,
            admission_id=admission_id,
            after_state={"version": 1, "status": item.order_status.value},
        )

    session.add(
        AdmissionTreatmentReview(
            admission_id=admission_id,
            assertion="reviewed_with_findings",
            source_type=prepared[0].source_type,
            note=f"Conciliación de {len(prepared)} tratamiento(s).",
            recorded_by_user_id=actor_id,
            recorded_at=now,
        )
    )
    _commit(session)
    return TreatmentBulkRead(
        items=[get_treatment(session, treatment_id) for treatment_id in treatment_ids]
    )


def update_treatment(
    session: Session,
    treatment_id: uuid.UUID,
    payload: TreatmentUpdate,
    actor_id: uuid.UUID,
) -> TreatmentRead:
    treatment = session.get(AdmissionTreatment, treatment_id)
    if treatment is None:
        raise _not_found("Tratamiento")
    _admission(session, treatment.admission_id, editable=True)
    payload = _catalog_payload(session, payload)
    current = session.exec(
        select(AdmissionTreatmentVersion)
        .where(AdmissionTreatmentVersion.treatment_id == treatment.id)
        .order_by(AdmissionTreatmentVersion.version.desc())
    ).first()
    if current is None:
        raise _conflict("El tratamiento no tiene una versión clínica válida.")
    if current.order_status == "entered_in_error":
        raise _conflict(
            "Un tratamiento ingresado por error es terminal; registre uno nuevo si corresponde."
        )
    if current.version != payload.expected_version:
        raise _conflict(
            f"El tratamiento fue actualizado por otro usuario. Versión vigente: {current.version}."
        )
    now = utc_now()
    next_row = AdmissionTreatmentVersion(
        treatment_id=treatment.id,
        version=current.version + 1,
        previous_version_id=current.id,
        change_reason=payload.change_reason,
        created_by_user_id=actor_id,
        created_at=now,
        **_version_values(payload, actor_id),
    )
    session.add(next_row)
    record_audit(
        session,
        action="admission_treatment_version_created",
        actor_user_id=actor_id,
        entity_type="admission_treatment",
        entity_id=treatment.id,
        admission_id=treatment.admission_id,
        before_state={"version": current.version, "status": current.order_status},
        after_state={"version": next_row.version, "status": payload.order_status.value},
    )
    _commit(session)
    return get_treatment(session, treatment.id)


def create_treatment_review(
    session: Session,
    admission_id: uuid.UUID,
    payload: TreatmentReviewCreate,
    actor_id: uuid.UUID,
) -> TreatmentReviewRead:
    _admission(session, admission_id, editable=True)
    context = read_treatment_context(session, admission_id)
    if payload.assertion.value == "no_known" and any(
        item.current.order_status in CURRENT_STATUSES for item in context.items
    ):
        raise _conflict("No puede declarar ausencia de tratamientos mientras existan registros vigentes.")
    row = AdmissionTreatmentReview(
        admission_id=admission_id,
        assertion=payload.assertion.value,
        source_type=payload.source_type,
        note=payload.note,
        recorded_by_user_id=actor_id,
        recorded_at=utc_now(),
    )
    session.add(row)
    record_audit(
        session,
        action="admission_treatments_reviewed",
        actor_user_id=actor_id,
        entity_type="admission_treatment_review",
        entity_id=row.id,
        admission_id=admission_id,
        after_state={"assertion": row.assertion},
    )
    _commit(session)
    session.refresh(row)
    return _review_read(session, row)


IMPACT_RULES = {
    "vasoactive": (
        "hemodynamic_context",
        "Considerar estabilidad hemodinámica y perfusión gastrointestinal al evaluar el soporte enteral.",
    ),
    "antimicrobial": (
        "gastrointestinal_tolerance",
        "Vigilar tolerancia gastrointestinal y patrón de deposiciones durante el tratamiento antimicrobiano.",
    ),
    "corticosteroid": (
        "glycemic_catabolic_context",
        "Relacionar el control glicémico y el contexto catabólico con el aporte nutricional.",
    ),
    "diuretic": (
        "fluid_balance_context",
        "Interpretar peso y balance hídrico considerando el tratamiento diurético activo.",
    ),
    "insulin_glycemic": (
        "carbohydrate_glycemic_context",
        "Relacionar insulina, controles de glicemia y aporte de carbohidratos.",
    ),
    "gastrointestinal": (
        "enteral_tolerance_context",
        "Considerar este tratamiento al interpretar motilidad y tolerancia enteral.",
    ),
    "sedative_analgesic": (
        "motility_context",
        "Considerar sedación, analgesia y posible impacto sobre motilidad/tolerancia gastrointestinal.",
    ),
}


def treatment_impact_summary(
    session: Session, admission_id: uuid.UUID
) -> TreatmentImpactSummary:
    context = read_treatment_context(session, admission_id)
    active = [item for item in context.items if item.current.order_status == "active"]
    potential_energy = sum(
        (item.current.prescribed_energy_kcal_day or Decimal("0") for item in active),
        start=Decimal("0"),
    )
    impact_items: list[TreatmentImpactItem] = []
    energy_source_count = 0
    for item in active:
        current = item.current
        if current.prescribed_energy_kcal_day is not None:
            energy_source_count += 1
            impact_items.append(
                TreatmentImpactItem(
                    treatment_id=item.id,
                    treatment_name=current.name,
                    rule_code="potential_prescribed_energy",
                    kind="potential_energy",
                    message=(
                        f"Aporte energético prescrito/potencial: "
                        f"{current.prescribed_energy_kcal_day} kcal/día."
                    ),
                )
            )
        elif current.category in {"nutritional_support", "sedative_analgesic"}:
            impact_items.append(
                TreatmentImpactItem(
                    treatment_id=item.id,
                    treatment_name=current.name,
                    rule_code="missing_energy_data",
                    kind="missing_data",
                    severity="warning",
                    message="Falta confirmar el aporte energético prescrito; no se incorpora al total potencial.",
                )
            )
        rule = IMPACT_RULES.get(current.category)
        if rule:
            impact_items.append(
                TreatmentImpactItem(
                    treatment_id=item.id,
                    treatment_name=current.name,
                    rule_code=rule[0],
                    kind="consideration",
                    message=rule[1],
                )
            )
    return TreatmentImpactSummary(
        admission_id=admission_id,
        potential_energy_kcal_day=potential_energy,
        energy_source_count=energy_source_count,
        items=impact_items,
        disclaimer=(
            "Resumen informativo para análisis nutricional. No constituye una indicación médica "
            "ni confirma administración efectiva."
        ),
    )
