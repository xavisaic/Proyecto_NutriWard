import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class BedMapService(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str


class BedMapLayout(BaseModel):
    grid_x: int
    grid_y: int
    width: int
    height: int


class BedMapPatient(BaseModel):
    id: uuid.UUID
    display_name: str
    identity_status: Literal["unidentified", "provisional", "identified"]
    age_years: int | None
    age_is_estimated: bool


class BedMapAdmission(BaseModel):
    id: uuid.UUID
    admission_identifier: str
    status: Literal["active"]
    admitted_at: datetime


class BedMapOccupancy(BaseModel):
    patient: BedMapPatient
    admission: BedMapAdmission


class BedMapBed(BaseModel):
    id: uuid.UUID
    code: str
    label: str | None
    status: Literal["free", "occupied"]
    layout: BedMapLayout | None
    occupancy: BedMapOccupancy | None


class BedMapRoom(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    floor: str | None
    beds: list[BedMapBed]


class BedMapResponse(BaseModel):
    generated_at: datetime
    service: BedMapService
    rooms: list[BedMapRoom]
