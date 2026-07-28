import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime
from sqlmodel import Field, SQLModel

from app.models.common import utc_now


class CareUnitLayoutPosition(SQLModel, table=True):
    __tablename__ = "care_unit_layout_positions"
    __table_args__ = (
        CheckConstraint("grid_x >= 0", name="ck_care_unit_layout_positions_grid_x"),
        CheckConstraint("grid_y >= 0", name="ck_care_unit_layout_positions_grid_y"),
        CheckConstraint("width > 0", name="ck_care_unit_layout_positions_width"),
        CheckConstraint("height > 0", name="ck_care_unit_layout_positions_height"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    care_unit_id: uuid.UUID = Field(foreign_key="care_units.id", unique=True, index=True)
    grid_x: int = 0
    grid_y: int = 0
    width: int = 1
    height: int = 1
    created_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True))
    updated_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True))
