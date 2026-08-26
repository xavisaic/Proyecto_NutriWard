import uuid
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.patient import normalize_optional_text, normalize_required_text


class TreatmentKind(StrEnum):
    MEDICATION = "medication"
    NUTRITIONAL_SUPPORT = "nutritional_support"


class TreatmentCategory(StrEnum):
    NUTRITIONAL_SUPPORT = "nutritional_support"
    VASOACTIVE = "vasoactive"
    SEDATIVE_ANALGESIC = "sedative_analgesic"
    ANTIMICROBIAL = "antimicrobial"
    CORTICOSTEROID = "corticosteroid"
    DIURETIC = "diuretic"
    INSULIN_GLYCEMIC = "insulin_glycemic"
    GASTROINTESTINAL = "gastrointestinal"
    ANTICOAGULANT = "anticoagulant"
    OTHER = "other"


class TreatmentOrderStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    ENDED = "ended"
    STOPPED = "stopped"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ENTERED_IN_ERROR = "entered_in_error"
    UNKNOWN = "unknown"


class TreatmentVerificationStatus(StrEnum):
    PENDING = "pending"
    VERIFIED = "verified"
    STALE = "stale"


class TreatmentReviewAssertion(StrEnum):
    REVIEWED_WITH_FINDINGS = "reviewed_with_findings"
    NO_KNOWN = "no_known"
    INFORMATION_UNAVAILABLE = "information_unavailable"


class MedicationCatalogItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    alternate_code: str | None
    display_name: str
    route: str | None
    available_inpatient: bool
    available_outpatient: bool
    restriction: str | None
    clinical_profile: str
    default_category: str
    source_version: str


class MedicationCatalogList(BaseModel):
    items: list[MedicationCatalogItemRead]
    total: int


class MedicationCatalogMatchRequest(BaseModel):
    lines: list[str] = Field(min_length=1, max_length=50)

    @field_validator("lines")
    @classmethod
    def normalize_lines(cls, value: list[str]) -> list[str]:
        cleaned = [normalize_required_text(item) for item in value if item.strip()]
        if not cleaned:
            raise ValueError("Debe incluir al menos un medicamento.")
        if len(cleaned) != len(set(item.casefold() for item in cleaned)):
            raise ValueError("La lista contiene lineas duplicadas.")
        return cleaned


class MedicationCatalogMatchItem(BaseModel):
    source_text: str
    status: str
    match: MedicationCatalogItemRead | None = None
    suggestions: list[MedicationCatalogItemRead] = Field(default_factory=list)


class MedicationCatalogMatchResponse(BaseModel):
    items: list[MedicationCatalogMatchItem]


class TreatmentData(BaseModel):
    medication_catalog_code: str | None = Field(default=None, max_length=40)
    raw_medication_text: str | None = Field(default=None, max_length=2000)
    name: str = Field(min_length=1, max_length=300)
    category: TreatmentCategory
    prescription_text: str = Field(min_length=1, max_length=2000)
    concentration_value: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=4)
    concentration_unit: str | None = Field(default=None, max_length=40)
    diluent_volume_ml: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    dose_value: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=4)
    dose_unit: str | None = Field(default=None, max_length=40)
    route: str | None = Field(default=None, max_length=80)
    modality: str | None = Field(default=None, max_length=80)
    frequency: str | None = Field(default=None, max_length=160)
    rate_value: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=4)
    rate_unit: str | None = Field(default=None, max_length=40)
    infusion_duration_hours: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    administered_volume_ml: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    prescribed_energy_kcal_day: Decimal | None = Field(
        default=None, ge=0, max_digits=12, decimal_places=2
    )
    starts_at: datetime | None = None
    planned_ends_at: datetime | None = None
    indication: str | None = Field(default=None, max_length=1000)
    order_status: TreatmentOrderStatus = TreatmentOrderStatus.ACTIVE
    source_type: str = Field(min_length=1, max_length=80)
    source_reference: str | None = Field(default=None, max_length=500)
    observed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    verification_status: TreatmentVerificationStatus = TreatmentVerificationStatus.VERIFIED
    nutritional_note: str | None = Field(default=None, max_length=2000)

    _required = field_validator("name", "prescription_text", "source_type")(
        normalize_required_text
    )
    _optional = field_validator(
        "concentration_unit",
        "dose_unit",
        "route",
        "modality",
        "frequency",
        "rate_unit",
        "indication",
        "raw_medication_text",
        "source_reference",
        "nutritional_note",
    )(normalize_optional_text)

    @model_validator(mode="after")
    def validate_pairs_and_dates(self):
        pairs = (
            (self.concentration_value, self.concentration_unit, "concentración"),
            (self.dose_value, self.dose_unit, "dosis"),
            (self.rate_value, self.rate_unit, "velocidad"),
        )
        for value, unit, label in pairs:
            if (value is None) != (unit is None):
                raise ValueError(f"{label.capitalize()} requiere valor y unidad.")
        if self.planned_ends_at and self.starts_at and self.planned_ends_at < self.starts_at:
            raise ValueError("La fecha prevista de término no puede preceder al inicio.")
        if self.infusion_duration_hours is not None and self.rate_value is None:
            raise ValueError("La duracion de infusion requiere una velocidad informada.")
        return self


class TreatmentCreate(TreatmentData):
    kind: TreatmentKind = TreatmentKind.MEDICATION

    @model_validator(mode="after")
    def validate_catalog_kind(self):
        if self.medication_catalog_code and self.kind != TreatmentKind.MEDICATION:
            raise ValueError("El arsenal solo puede vincularse a medicamentos.")
        return self


class TreatmentBulkCreate(BaseModel):
    items: list[TreatmentCreate] = Field(min_length=1, max_length=50)


class TreatmentUpdate(TreatmentData):
    expected_version: int = Field(ge=1)
    change_reason: str = Field(min_length=3, max_length=1000)

    _reason = field_validator("change_reason")(normalize_required_text)


class TreatmentReviewCreate(BaseModel):
    assertion: TreatmentReviewAssertion
    source_type: str = Field(min_length=1, max_length=80)
    note: str | None = Field(default=None, max_length=1000)

    _source = field_validator("source_type")(normalize_required_text)
    _note = field_validator("note")(normalize_optional_text)


class TreatmentVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    treatment_id: uuid.UUID
    version: int
    previous_version_id: uuid.UUID | None
    medication_catalog_code: str | None
    raw_medication_text: str | None
    name: str
    category: str
    prescription_text: str
    concentration_value: Decimal | None
    concentration_unit: str | None
    diluent_volume_ml: Decimal | None
    dose_value: Decimal | None
    dose_unit: str | None
    route: str | None
    modality: str | None
    frequency: str | None
    rate_value: Decimal | None
    rate_unit: str | None
    infusion_duration_hours: Decimal | None
    administered_volume_ml: Decimal | None
    estimated_volume_ml: Decimal | None = None
    prescribed_energy_kcal_day: Decimal | None
    starts_at: datetime | None
    planned_ends_at: datetime | None
    indication: str | None
    order_status: str
    source_type: str
    source_reference: str | None
    observed_at: datetime
    verification_status: str
    verified_at: datetime | None
    verified_by_user_id: uuid.UUID | None
    verifier_name: str | None = None
    nutritional_note: str | None
    change_reason: str
    created_by_user_id: uuid.UUID
    author_name: str = ""
    medication_catalog: MedicationCatalogItemRead | None = None
    created_at: datetime


class TreatmentRead(BaseModel):
    id: uuid.UUID
    admission_id: uuid.UUID
    kind: str
    created_by_user_id: uuid.UUID
    created_at: datetime
    current: TreatmentVersionRead
    history: list[TreatmentVersionRead]


class TreatmentBulkRead(BaseModel):
    items: list[TreatmentRead]


class TreatmentReviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    admission_id: uuid.UUID
    assertion: str
    source_type: str
    note: str | None
    recorded_by_user_id: uuid.UUID
    author_name: str = ""
    recorded_at: datetime


class TreatmentCounts(BaseModel):
    active: int
    on_hold: int
    pending_verification: int
    historical: int


class TreatmentContextRead(BaseModel):
    admission_id: uuid.UUID
    review_status: str
    latest_review: TreatmentReviewRead | None
    items: list[TreatmentRead]
    counts: TreatmentCounts


class TreatmentImpactItem(BaseModel):
    treatment_id: uuid.UUID
    treatment_name: str
    rule_code: str
    kind: str
    message: str
    severity: str = "info"


class TreatmentImpactSummary(BaseModel):
    admission_id: uuid.UUID
    potential_energy_kcal_day: Decimal
    energy_source_count: int
    items: list[TreatmentImpactItem]
    disclaimer: str
