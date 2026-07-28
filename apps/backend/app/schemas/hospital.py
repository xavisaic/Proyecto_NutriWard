import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def normalize_required_text(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError("El valor no puede estar vacío.")
    return normalized


def normalize_code(value: str | None) -> str | None:
    normalized = normalize_optional_text(value)
    return normalized.upper() if normalized is not None else None


def normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.split())
    return normalized or None


class ServiceCreate(BaseModel):
    code: str = Field(min_length=1, max_length=30)
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)

    _normalize_code = field_validator("code")(normalize_code)
    _normalize_name = field_validator("name")(normalize_required_text)
    _normalize_description = field_validator("description")(normalize_optional_text)


class ServiceUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=30)
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None

    _normalize_code = field_validator("code")(normalize_code)
    _normalize_name = field_validator("name")(normalize_optional_text)
    _normalize_description = field_validator("description")(normalize_optional_text)

    @model_validator(mode="after")
    def reject_null_identity(self):
        for field in ("code", "name"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} no puede ser nulo.")
        return self


class RoomCreate(BaseModel):
    service_id: uuid.UUID
    code: str = Field(min_length=1, max_length=30)
    name: str = Field(min_length=1, max_length=120)
    floor: str | None = Field(default=None, max_length=50)
    notes: str | None = Field(default=None, max_length=500)

    _normalize_code = field_validator("code")(normalize_code)
    _normalize_name = field_validator("name")(normalize_required_text)
    _normalize_floor = field_validator("floor")(normalize_optional_text)
    _normalize_notes = field_validator("notes")(normalize_optional_text)


class RoomUpdate(BaseModel):
    service_id: uuid.UUID | None = None
    code: str | None = Field(default=None, min_length=1, max_length=30)
    name: str | None = Field(default=None, min_length=1, max_length=120)
    floor: str | None = Field(default=None, max_length=50)
    notes: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None

    _normalize_code = field_validator("code")(normalize_code)
    _normalize_name = field_validator("name")(normalize_optional_text)
    _normalize_floor = field_validator("floor")(normalize_optional_text)
    _normalize_notes = field_validator("notes")(normalize_optional_text)

    @model_validator(mode="after")
    def reject_null_identity(self):
        for field in ("service_id", "code", "name"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} no puede ser nulo.")
        return self


class CareUnitType(StrEnum):
    BED = "bed"
    STRETCHER = "stretcher"
    STATION = "station"
    BOX = "box"


class CareUnitCreate(BaseModel):
    room_id: uuid.UUID
    code: str | None = Field(default=None, min_length=1, max_length=30)
    label: str | None = Field(default=None, max_length=120)
    unit_type: CareUnitType = CareUnitType.BED

    _normalize_code = field_validator("code")(normalize_code)
    _normalize_label = field_validator("label")(normalize_optional_text)


class CareUnitUpdate(BaseModel):
    room_id: uuid.UUID | None = None
    code: str | None = Field(default=None, min_length=1, max_length=30)
    label: str | None = Field(default=None, max_length=120)
    unit_type: CareUnitType | None = None
    is_active: bool | None = None

    _normalize_code = field_validator("code")(normalize_code)
    _normalize_label = field_validator("label")(normalize_optional_text)

    @model_validator(mode="after")
    def reject_null_identity(self):
        for field in ("room_id", "code", "unit_type"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} no puede ser nulo.")
        return self


class LayoutUpsert(BaseModel):
    grid_x: int = Field(ge=0, le=100)
    grid_y: int = Field(ge=0, le=100)
    width: int = Field(default=1, ge=1, le=12)
    height: int = Field(default=1, ge=1, le=12)


class PurgeRequest(BaseModel):
    reason: str = Field(min_length=10, max_length=500)

    _normalize_reason = field_validator("reason")(normalize_required_text)


class LayoutRead(LayoutUpsert):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    care_unit_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class CareUnitRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    room_id: uuid.UUID
    code: str
    label: str | None
    unit_type: CareUnitType
    is_active: bool
    layout: LayoutRead | None = None
    created_at: datetime
    updated_at: datetime


class RoomRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    service_id: uuid.UUID
    code: str
    name: str
    floor: str | None
    notes: str | None
    is_active: bool
    care_units: list[CareUnitRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ServiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    description: str | None
    is_active: bool
    rooms: list[RoomRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class HospitalStructureResponse(BaseModel):
    items: list[ServiceRead]
    total: int
