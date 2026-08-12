import uuid
from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _required_text(value: str) -> str:
    normalized = " ".join(value.split())
    if len(normalized) < 3:
        raise ValueError("Debe indicar un motivo de al menos 3 caracteres.")
    return normalized


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.split())
    return normalized or None


class TransferMode(StrEnum):
    DIRECT = "direct"
    RECEPTION_TRAY = "reception_tray"


class TransferStatus(StrEnum):
    REQUESTED = "requested"
    PENDING_RECEPTION = "pending_reception"
    ACCEPTED = "accepted"
    PENDING_BED = "pending_bed"
    ASSIGNED_TO_BED = "assigned_to_bed"
    REJECTED = "rejected"
    RETURNED = "returned"
    CANCELLED = "cancelled"


class TransferRequestCreate(BaseModel):
    admission_id: uuid.UUID
    destination_service_id: uuid.UUID
    transfer_mode: TransferMode
    destination_care_unit_id: uuid.UUID | None = None
    reason: str | None = Field(default=None, max_length=500)

    _normalize_reason = field_validator("reason")(_optional_text)

    @model_validator(mode="after")
    def validate_destination_bed(self):
        if self.transfer_mode == TransferMode.DIRECT and self.destination_care_unit_id is None:
            raise ValueError("El traslado directo requiere una cama destino.")
        if self.transfer_mode == TransferMode.RECEPTION_TRAY and self.destination_care_unit_id is not None:
            raise ValueError("El envío a bandeja no admite una cama destino.")
        return self


class TransferAccept(BaseModel):
    destination_care_unit_id: uuid.UUID | None = None
    observation: str | None = Field(default=None, max_length=500)

    _normalize_observation = field_validator("observation")(_optional_text)


class TransferAssignBed(BaseModel):
    destination_care_unit_id: uuid.UUID
    observation: str | None = Field(default=None, max_length=500)

    _normalize_observation = field_validator("observation")(_optional_text)


class TransferRequiredReason(BaseModel):
    reason: str = Field(min_length=3, max_length=500)

    _normalize_reason = field_validator("reason")(_required_text)


class TransferStatusHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sequence_number: int
    from_status: TransferStatus | None
    to_status: TransferStatus
    reason: str | None
    changed_by_user_id: uuid.UUID
    changed_at: datetime
    is_coverage: bool


class TransferServiceSummary(BaseModel):
    id: uuid.UUID
    code: str
    name: str


class TransferLocationSummary(BaseModel):
    care_unit_id: uuid.UUID
    care_unit_code: str
    care_unit_label: str | None
    room_id: uuid.UUID
    room_code: str
    room_name: str
    service_id: uuid.UUID
    service_code: str
    service_name: str


class TransferPatientSummary(BaseModel):
    id: uuid.UUID
    display_name: str
    identity_status: Literal["unidentified", "provisional", "identified"]
    age_years: int | None
    age_is_estimated: bool


class TransferAdmissionSummary(BaseModel):
    id: uuid.UUID
    admission_identifier: str
    status: str
    admitted_at: datetime


class TransferRequestRead(BaseModel):
    id: uuid.UUID
    admission_id: uuid.UUID
    transfer_mode: TransferMode
    status: TransferStatus
    request_reason: str | None
    requested_by_user_id: uuid.UUID
    requested_at: datetime
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    origin_service: TransferServiceSummary
    destination_service: TransferServiceSummary
    origin_care_unit_id: uuid.UUID
    destination_care_unit_id: uuid.UUID | None
    current_origin_location: TransferLocationSummary | None
    patient: TransferPatientSummary
    admission: TransferAdmissionSummary
    has_coverage_support: bool = False
    status_history: list[TransferStatusHistoryRead] = Field(default_factory=list)


class TransferRequestListResponse(BaseModel):
    items: list[TransferRequestRead]
    total: int
    page: int
    page_size: int
