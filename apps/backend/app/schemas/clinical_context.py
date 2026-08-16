import uuid
from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.patient import normalize_optional_text, normalize_required_text


class ClinicalSource(StrEnum):
    TRAKCARE_MANUAL = "trakcare_manual"
    CLINICAL_RECORD = "clinical_record"
    CARE_TEAM = "care_team"
    PATIENT = "patient"
    FAMILY_OR_CAREGIVER = "family_or_caregiver"
    COMBINED = "combined"
    OTHER = "other"


class ConditionClinicalStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    REMISSION = "remission"
    RESOLVED = "resolved"
    ENTERED_IN_ERROR = "entered_in_error"


class ConditionVerificationStatus(StrEnum):
    UNCONFIRMED = "unconfirmed"
    CONFIRMED = "confirmed"
    REFUTED = "refuted"


class DiagnosisClinicalStatus(StrEnum):
    ACTIVE = "active"
    RESOLVED = "resolved"
    ENTERED_IN_ERROR = "entered_in_error"


class DiagnosisVerificationStatus(StrEnum):
    PROVISIONAL = "provisional"
    CONFIRMED = "confirmed"
    RULED_OUT = "ruled_out"


class DiagnosisType(StrEnum):
    PRINCIPAL = "principal"
    SECONDARY = "secondary"
    COMPLICATION = "complication"


class PatientConditionCreate(BaseModel):
    condition_name: str = Field(min_length=1, max_length=500)
    code_system: str | None = Field(default=None, max_length=50)
    code: str | None = Field(default=None, max_length=50)
    clinical_status: ConditionClinicalStatus = ConditionClinicalStatus.ACTIVE
    verification_status: ConditionVerificationStatus = ConditionVerificationStatus.CONFIRMED
    onset_date: date | None = None
    resolved_on: date | None = None
    source: ClinicalSource
    note: str | None = Field(default=None, max_length=2000)

    _name = field_validator("condition_name")(normalize_required_text)
    _optional = field_validator("code_system", "code", "note")(normalize_optional_text)

    @model_validator(mode="after")
    def resolved_date_matches_status(self):
        if self.resolved_on and self.clinical_status != ConditionClinicalStatus.RESOLVED:
            raise ValueError("La fecha de resolución requiere estado resuelto.")
        return self


class PatientConditionBulkCreate(BaseModel):
    items: list[PatientConditionCreate] = Field(min_length=1, max_length=100)


class AdmissionDiagnosisCreate(BaseModel):
    diagnosis_name: str = Field(min_length=1, max_length=500)
    code_system: str | None = Field(default=None, max_length=50)
    code: str | None = Field(default=None, max_length=50)
    diagnosis_type: DiagnosisType = DiagnosisType.SECONDARY
    clinical_status: DiagnosisClinicalStatus = DiagnosisClinicalStatus.ACTIVE
    verification_status: DiagnosisVerificationStatus = DiagnosisVerificationStatus.PROVISIONAL
    present_on_admission: bool = True
    diagnosed_at: datetime | None = None
    resolved_at: datetime | None = None
    source: ClinicalSource
    note: str | None = Field(default=None, max_length=2000)

    _name = field_validator("diagnosis_name")(normalize_required_text)
    _optional = field_validator("code_system", "code", "note")(normalize_optional_text)

    @model_validator(mode="after")
    def resolved_date_matches_status(self):
        if self.resolved_at and self.clinical_status != DiagnosisClinicalStatus.RESOLVED:
            raise ValueError("La fecha de resolución requiere estado resuelto.")
        return self


class AdmissionDiagnosisBulkCreate(BaseModel):
    items: list[AdmissionDiagnosisCreate] = Field(min_length=1, max_length=100)


class ConditionStatusUpdate(BaseModel):
    version: int = Field(ge=1)
    clinical_status: ConditionClinicalStatus
    verification_status: ConditionVerificationStatus
    reason: str = Field(min_length=3, max_length=1000)
    source: ClinicalSource
    resolved_on: date | None = None

    _reason = field_validator("reason")(normalize_required_text)

    @model_validator(mode="after")
    def resolved_date_matches_status(self):
        if self.resolved_on and self.clinical_status != ConditionClinicalStatus.RESOLVED:
            raise ValueError("La fecha de resolución requiere estado resuelto.")
        return self


class DiagnosisStatusUpdate(BaseModel):
    version: int = Field(ge=1)
    clinical_status: DiagnosisClinicalStatus
    verification_status: DiagnosisVerificationStatus
    reason: str = Field(min_length=3, max_length=1000)
    source: ClinicalSource
    resolved_at: datetime | None = None

    _reason = field_validator("reason")(normalize_required_text)

    @model_validator(mode="after")
    def resolved_date_matches_status(self):
        if self.resolved_at and self.clinical_status != DiagnosisClinicalStatus.RESOLVED:
            raise ValueError("La fecha de resolución requiere estado resuelto.")
        return self


class StatusHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sequence_number: int
    from_clinical_status: str | None
    to_clinical_status: str
    from_verification_status: str | None
    to_verification_status: str
    reason: str
    source: str
    changed_by_user_id: uuid.UUID
    changed_at: datetime
    version: int


class PatientConditionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    patient_id: uuid.UUID
    condition_name: str
    code_system: str | None
    code: str | None
    clinical_status: str
    verification_status: str
    onset_date: date | None
    resolved_on: date | None
    source: str
    note: str | None
    version: int
    created_by_user_id: uuid.UUID
    updated_by_user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    history: list[StatusHistoryRead] = Field(default_factory=list)


class AdmissionDiagnosisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    admission_id: uuid.UUID
    diagnosis_name: str
    code_system: str | None
    code: str | None
    diagnosis_type: str
    clinical_status: str
    verification_status: str
    present_on_admission: bool
    diagnosed_at: datetime
    resolved_at: datetime | None
    source: str
    note: str | None
    version: int
    created_by_user_id: uuid.UUID
    updated_by_user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    history: list[StatusHistoryRead] = Field(default_factory=list)


def normalize_clinical_narrative(value: str) -> str:
    normalized_lines = [
        line.rstrip()
        for line in value.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    ]
    normalized = "\n".join(normalized_lines).strip()
    if not normalized:
        raise ValueError("La historia del episodio no puede estar vacía.")
    return normalized


class AdmissionClinicalHistoryCreate(BaseModel):
    narrative: str = Field(min_length=10, max_length=10000)
    event_start_date: date | None = None
    source: ClinicalSource

    _narrative = field_validator("narrative")(normalize_clinical_narrative)


class AdmissionClinicalHistoryUpdate(AdmissionClinicalHistoryCreate):
    version: int = Field(ge=1)
    change_reason: str = Field(min_length=3, max_length=1000)

    _reason = field_validator("change_reason")(normalize_required_text)


class AdmissionClinicalHistoryVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    admission_id: uuid.UUID
    version: int
    narrative: str
    event_start_date: date | None
    source: str
    change_reason: str | None
    recorded_by_user_id: uuid.UUID
    author_name: str
    recorded_at: datetime


class AdmissionClinicalHistoryRead(BaseModel):
    admission_id: uuid.UUID
    current: AdmissionClinicalHistoryVersionRead
    versions: list[AdmissionClinicalHistoryVersionRead]


class ClinicalContextRead(BaseModel):
    admission_id: uuid.UUID
    patient_id: uuid.UUID
    episode_history: AdmissionClinicalHistoryRead | None
    diagnoses: list[AdmissionDiagnosisRead]
    conditions: list[PatientConditionRead]
