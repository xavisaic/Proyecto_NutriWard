import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.models.common import utc_now

CARE_UNIT_TYPES = ("bed", "stretcher", "station", "box")


class CareUnit(SQLModel, table=True):
    __tablename__ = "care_units"
    __table_args__ = (
        UniqueConstraint("room_id", "code", name="uq_care_units_room_code"),
        CheckConstraint(
            "unit_type IN ('bed', 'stretcher', 'station', 'box')",
            name="ck_care_units_unit_type",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    room_id: uuid.UUID = Field(foreign_key="rooms.id", index=True)
    code: str = Field(max_length=30)
    label: str | None = Field(default=None, max_length=120)
    unit_type: str = Field(default="bed", max_length=20, index=True)
    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True))
    updated_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True))
