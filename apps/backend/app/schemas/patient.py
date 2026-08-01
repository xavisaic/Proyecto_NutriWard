import re
import uuid
from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.split())
    return normalized or None


def normalize_required_text(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError("El valor no puede estar vacío.")
    return normalized


def normalize_rut(value: str) -> str:
    normalized = re.sub(r"[.\s-]", "", value).upper()
    if not re.fullmatch(r"\d{7,8}[\dK]", normalized):
        raise ValueError("El RUT no tiene un formato válido.")
    body, supplied_digit = normalized[:-1], normalized[-1]
    total = 0
    multiplier = 2
    for digit in reversed(body):
        total += int(digit) * multiplier
        multiplier = 2 if multiplier == 7 else multiplier + 1
    calculated = 11 - (total % 11)
    expected_digit = "0" if calculated == 11 else "K" if calculated == 10 else str(calculated)
    if supplied_digit != expected_digit:
        raise ValueError("El dígito verificador del RUT no es válido.")
    return f"{body}-{supplied_digit}"


class IdentityStatus(StrEnum):
    UNIDENTIFIED = "unidentified"
    PROVISIONAL = "provisional"
    IDENTIFIED = "identified"


class PatientSex(StrEnum):
    FEMALE = "female"
    MALE = "male"
    INTERSEX = "intersex"
    UNKNOWN = "unknown"


class AdmissionStatus(StrEnum):
    ACTIVE = "active"
    DISCHARGED = "discharged"
    DECEASED = "deceased"
    CLOSED = "closed"


class PatientCreate(BaseModel):
    identity_status: IdentityStatus = IdentityStatus.IDENTIFIED
    rut: str | None = None
    given_names: str | None = Field(default=None, max_length=160)
    first_surname: str | None = Field(default=None, max_length=100)
    second_surname: str | None = Field(default=None, max_length=100)
    date_of_birth: date | None = None
    date_of_birth_is_estimated: bool = False
    sex: PatientSex | None = None
    hospital_identifier: str | None = Field(default=None, max_length=80)
    phone: str | None = Field(default=None, max_length=40)
    provisional_description: str | None = Field(default=None, max_length=1000)

    _normalize_text = field_validator(
        "given_names",
        "first_surname",
        "second_surname",
        "hospital_identifier",
        "phone",
        "provisional_description",
    )(normalize_optional_text)

    @field_validator("rut")
    @classmethod
    def validate_rut(cls, value: str | None) -> str | None:
        return normalize_rut(value) if value else None

    @model_validator(mode="after")
    def validate_identity(self):
        if self.identity_status == IdentityStatus.UNIDENTIFIED:
            raise ValueError("Use el endpoint de pacientes no identificados.")
        if self.identity_status == IdentityStatus.IDENTIFIED:
            if not self.rut:
                raise ValueError("Un paciente identificado requiere RUT.")
            if not self.given_names or not self.first_surname:
                raise ValueError("Un paciente identificado requiere nombres y primer apellido.")
        elif self.rut:
            raise ValueError("Una ficha provisoria no puede confirmar un RUT.")
        return self


class UnidentifiedPatientCreate(BaseModel):
    provisional_description: str | None = Field(default=None, max_length=1000)
    date_of_birth: date | None = None
    date_of_birth_is_estimated: bool = True
    sex: PatientSex | None = None
    hospital_identifier: str | None = Field(default=None, max_length=80)

    _normalize_text = field_validator(
        "provisional_description",
        "hospital_identifier",
    )(normalize_optional_text)


class PatientIdentityUpdate(BaseModel):
    rut: str
    given_names: str = Field(min_length=1, max_length=160)
    first_surname: str = Field(min_length=1, max_length=100)
    second_surname: str | None = Field(default=None, max_length=100)
    date_of_birth: date | None = None
    date_of_birth_is_estimated: bool = False
    sex: PatientSex | None = None
    hospital_identifier: str | None = Field(default=None, max_length=80)
    phone: str | None = Field(default=None, max_length=40)

    _normalize_rut = field_validator("rut")(normalize_rut)
    _normalize_required = field_validator(
        "given_names",
        "first_surname",
    )(normalize_required_text)
    _normalize_text = field_validator(
        "second_surname",
        "hospital_identifier",
        "phone",
    )(normalize_optional_text)


class PatientReconcile(BaseModel):
    rut: str
    reason: str = Field(min_length=10, max_length=500)

    _normalize_rut = field_validator("rut")(normalize_rut)
    _normalize_reason = field_validator("reason")(normalize_required_text)


class LocationAssignment(BaseModel):
    care_unit_id: uuid.UUID
    reason: str | None = Field(default=None, max_length=500)

    _normalize_reason = field_validator("reason")(normalize_optional_text)


class AdmissionCreate(BaseModel):
    patient_id: uuid.UUID
    admitted_at: datetime | None = None
    admission_identifier: str | None = Field(default=None, max_length=50)
    care_unit_id: uuid.UUID | None = None
    location_reason: str | None = Field(default=None, max_length=500)

    _normalize_identifier = field_validator("admission_identifier")(normalize_optional_text)
    _normalize_reason = field_validator("location_reason")(normalize_optional_text)


class AdmissionStatusUpdate(BaseModel):
    status: AdmissionStatus
    reason: str = Field(min_length=3, max_length=500)

    _normalize_reason = field_validator("reason")(normalize_required_text)

    @model_validator(mode="after")
    def terminal_only(self):
        if self.status == AdmissionStatus.ACTIVE:
            raise ValueError("El estado activo no puede restaurarse en esta fase.")
        return self


class LocationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    admission_id: uuid.UUID
    care_unit_id: uuid.UUID
    started_at: datetime
    ended_at: datetime | None
    reason: str | None
    assigned_by_user_id: uuid.UUID | None
    ended_by_user_id: uuid.UUID | None
    created_at: datetime
    care_unit_code: str | None = None
    care_unit_label: str | None = None
    room_id: uuid.UUID | None = None
    room_code: str | None = None
    room_name: str | None = None
    service_id: uuid.UUID | None = None
    service_code: str | None = None
    service_name: str | None = None


class AdmissionStatusHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    admission_id: uuid.UUID
    from_status: AdmissionStatus | None
    to_status: AdmissionStatus
    reason: str | None
    changed_at: datetime
    changed_by_user_id: uuid.UUID | None


class AdmissionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    patient_id: uuid.UUID
    admission_identifier: str
    status: AdmissionStatus
    admitted_at: datetime
    ended_at: datetime | None
    end_reason: str | None
    created_at: datetime
    updated_at: datetime
    current_location: LocationRead | None = None
    status_history: list[AdmissionStatusHistoryRead] = Field(default_factory=list)
    location_history: list[LocationRead] = Field(default_factory=list)


class PatientSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    identity_status: IdentityStatus
    temporary_identifier: str | None
    rut: str | None
    given_names: str | None
    first_surname: str | None
    second_surname: str | None
    date_of_birth: date | None
    date_of_birth_is_estimated: bool
    sex: PatientSex | None
    hospital_identifier: str | None
    phone: str | None
    provisional_description: str | None
    identified_at: datetime | None
    merged_into_patient_id: uuid.UUID | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    active_admission: AdmissionRead | None = None


class PatientDetail(PatientSummary):
    admissions: list[AdmissionRead] = Field(default_factory=list)


class PatientListResponse(BaseModel):
    items: list[PatientSummary]
    total: int
    page: int
    page_size: int


class AdmissionListResponse(BaseModel):
    items: list[AdmissionRead]
    total: int
