import uuid
from datetime import date, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.clinical_context import ClinicalSource
from app.schemas.patient import normalize_optional_text, normalize_required_text


class AllergyType(StrEnum):
    ALLERGY = "allergy"
    INTOLERANCE = "intolerance"


class AllergyCategory(StrEnum):
    FOOD = "food"
    MEDICATION = "medication"
    ENVIRONMENT = "environment"
    BIOLOGIC = "biologic"
    OTHER = "other"


class AllergyClinicalStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    RESOLVED = "resolved"


class AllergyVerificationStatus(StrEnum):
    UNCONFIRMED = "unconfirmed"
    PRESUMED = "presumed"
    CONFIRMED = "confirmed"
    REFUTED = "refuted"
    ENTERED_IN_ERROR = "entered_in_error"


class AllergyCriticality(StrEnum):
    LOW = "low"
    HIGH = "high"
    UNABLE_TO_ASSESS = "unable_to_assess"


class ReactionSeverity(StrEnum):
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"


class AllergyReviewCategory(StrEnum):
    ALL = "all"
    FOOD = "food"
    MEDICATION = "medication"
    ENVIRONMENT = "environment"
    BIOLOGIC = "biologic"
    OTHER = "other"


class AllergyReviewAssertionValue(StrEnum):
    NOT_ASKED = "not_asked"
    INFORMATION_UNAVAILABLE = "information_unavailable"
    NO_KNOWN = "no_known"
    REVIEWED_WITH_FINDINGS = "reviewed_with_findings"


class AllergyReactionCreate(BaseModel):
    manifestation: str = Field(min_length=1, max_length=500)
    severity: ReactionSeverity | None = None
    occurred_at: datetime | None = None
    exposure_route: str | None = Field(default=None, max_length=100)
    note: str | None = Field(default=None, max_length=1000)

    _manifestation = field_validator("manifestation")(normalize_required_text)
    _optional = field_validator("exposure_route", "note")(normalize_optional_text)


class AllergyIntoleranceCreate(BaseModel):
    substance_name: str = Field(min_length=1, max_length=500)
    code_system: str | None = Field(default=None, max_length=100)
    code: str | None = Field(default=None, max_length=100)
    allergy_type: AllergyType | None = None
    category: AllergyCategory
    clinical_status: AllergyClinicalStatus = AllergyClinicalStatus.ACTIVE
    verification_status: AllergyVerificationStatus = AllergyVerificationStatus.UNCONFIRMED
    criticality: AllergyCriticality = AllergyCriticality.UNABLE_TO_ASSESS
    onset_date: date | None = None
    source: ClinicalSource
    note: str | None = Field(default=None, max_length=2000)
    reactions: list[AllergyReactionCreate] = Field(default_factory=list, max_length=20)

    _substance = field_validator("substance_name")(normalize_required_text)
    _optional = field_validator("code_system", "code", "note")(normalize_optional_text)

    @model_validator(mode="after")
    def reject_initial_error(self):
        if self.verification_status == AllergyVerificationStatus.ENTERED_IN_ERROR:
            raise ValueError("Un registro nuevo no puede comenzar como ingresado por error.")
        return self


class AllergyIntoleranceBulkCreate(BaseModel):
    items: list[AllergyIntoleranceCreate] = Field(min_length=1, max_length=100)


class AllergyStatusUpdate(BaseModel):
    version: int = Field(ge=1)
    clinical_status: AllergyClinicalStatus | None = None
    verification_status: AllergyVerificationStatus
    criticality: AllergyCriticality
    source: ClinicalSource
    reason: str = Field(min_length=3, max_length=1000)

    _reason = field_validator("reason")(normalize_required_text)

    @model_validator(mode="after")
    def validate_entered_in_error(self):
        entered_in_error = self.verification_status == AllergyVerificationStatus.ENTERED_IN_ERROR
        if entered_in_error and self.clinical_status is not None:
            raise ValueError("Ingresado por error no debe conservar estado clínico.")
        if not entered_in_error and self.clinical_status is None:
            raise ValueError("El estado clínico es obligatorio.")
        return self


class AllergyReviewAssertionCreate(BaseModel):
    category: AllergyReviewCategory
    assertion: AllergyReviewAssertionValue
    source: ClinicalSource
    note: str | None = Field(default=None, max_length=1000)

    _note = field_validator("note")(normalize_optional_text)


class AllergyReactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    manifestation: str
    severity: str | None
    occurred_at: datetime | None
    exposure_route: str | None
    note: str | None
    created_by_user_id: uuid.UUID
    created_at: datetime


class AllergyStatusHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sequence_number: int
    from_clinical_status: str | None
    to_clinical_status: str | None
    from_verification_status: str | None
    to_verification_status: str
    from_criticality: str | None
    to_criticality: str
    reason: str
    source: str
    changed_by_user_id: uuid.UUID
    changed_at: datetime
    version: int


class AllergyIntoleranceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    patient_id: uuid.UUID
    asserted_admission_id: uuid.UUID | None
    substance_name: str
    code_system: str | None
    code: str | None
    allergy_type: str | None
    category: str
    clinical_status: str | None
    verification_status: str
    criticality: str
    onset_date: date | None
    source: str
    note: str | None
    version: int
    created_by_user_id: uuid.UUID
    updated_by_user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    reactions: list[AllergyReactionRead] = Field(default_factory=list)
    history: list[AllergyStatusHistoryRead] = Field(default_factory=list)


class AllergyReviewAssertionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    patient_id: uuid.UUID
    admission_id: uuid.UUID
    category: str
    assertion: str
    source: str
    note: str | None
    recorded_by_user_id: uuid.UUID
    recorded_at: datetime


class AllergyContextRead(BaseModel):
    admission_id: uuid.UUID
    patient_id: uuid.UUID
    items: list[AllergyIntoleranceRead]
    review_assertions: list[AllergyReviewAssertionRead]


class FoodSafetyReactionRead(BaseModel):
    manifestation: str
    severity: str | None


class FoodSafetyAllergyRead(BaseModel):
    id: uuid.UUID
    substance_name: str
    allergy_type: str | None
    criticality: str
    reactions: list[FoodSafetyReactionRead]


class FoodSafetyAllergyProjection(BaseModel):
    admission_id: uuid.UUID
    review_status: Literal[
        "active_food_risks",
        "no_known",
        "not_reviewed",
        "information_unavailable",
        "no_active_food_risks",
    ]
    items: list[FoodSafetyAllergyRead]
