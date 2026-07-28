import re
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def normalize_email(value: str) -> str:
    normalized = value.strip().lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", normalized):
        raise ValueError("El correo no tiene un formato válido.")
    return normalized


def normalize_full_name(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError("El nombre no puede estar vacío.")
    return normalized


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    is_active: bool
    roles: list[str]
    created_at: datetime
    updated_at: datetime


class UserListResponse(BaseModel):
    items: list[UserRead]
    total: int


class UserCreate(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    full_name: str = Field(min_length=1, max_length=160)
    password: str = Field(min_length=8, max_length=256)
    is_active: bool = True

    _normalize_email = field_validator("email")(normalize_email)
    _normalize_full_name = field_validator("full_name")(normalize_full_name)


class UserUpdate(BaseModel):
    email: str | None = Field(default=None, min_length=3, max_length=320)
    full_name: str | None = Field(default=None, min_length=1, max_length=160)
    is_active: bool | None = None

    _normalize_email = field_validator("email")(normalize_email)
    _normalize_full_name = field_validator("full_name")(normalize_full_name)

    @model_validator(mode="after")
    def validate_changes(self):
        if not self.model_fields_set:
            raise ValueError("Debe indicar al menos un cambio.")
        for field in ("email", "full_name", "is_active"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} no puede ser nulo.")
        return self


class RoleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str
    created_at: datetime
    updated_at: datetime


class RoleListResponse(BaseModel):
    items: list[RoleRead]
    total: int


class UserRoleAssign(BaseModel):
    role_id: uuid.UUID


class UserRoleRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    role_id: uuid.UUID
    role_name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class NutritionistServiceAssignmentCreate(BaseModel):
    nutritionist_user_id: uuid.UUID
    service_id: uuid.UUID


class NutritionistServiceAssignmentUpdate(BaseModel):
    service_id: uuid.UUID | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def validate_changes(self):
        if not self.model_fields_set:
            raise ValueError("Debe indicar al menos un cambio.")
        for field in ("service_id", "is_active"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} no puede ser nulo.")
        return self


class NutritionistServiceAssignmentRead(BaseModel):
    id: uuid.UUID
    nutritionist_user_id: uuid.UUID
    nutritionist_name: str
    nutritionist_email: str
    service_id: uuid.UUID
    service_code: str
    service_name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class NutritionistServiceAssignmentListResponse(BaseModel):
    items: list[NutritionistServiceAssignmentRead]
    total: int
