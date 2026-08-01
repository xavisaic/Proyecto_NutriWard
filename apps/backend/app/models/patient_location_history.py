import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, text
from sqlmodel import Field, SQLModel

from app.models.common import utc_now


class PatientLocationHistory(SQLModel, table=True):
    __tablename__ = "patient_location_history"
    __table_args__ = (
        Index(
            "uq_patient_location_one_current_per_admission",
            "admission_id",
            unique=True,
            postgresql_where=text("ended_at IS NULL"),
            sqlite_where=text("ended_at IS NULL"),
        ),
        Index(
            "uq_patient_location_one_current_per_bed",
            "care_unit_id",
            unique=True,
            postgresql_where=text("ended_at IS NULL"),
            sqlite_where=text("ended_at IS NULL"),
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    admission_id: uuid.UUID = Field(foreign_key="admissions.id", index=True)
    care_unit_id: uuid.UUID = Field(foreign_key="care_units.id", index=True)
    started_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True), index=True)
    ended_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True), index=True)
    reason: str | None = Field(default=None, max_length=500)
    assigned_by_user_id: uuid.UUID | None = Field(default=None, foreign_key="users.id")
    ended_by_user_id: uuid.UUID | None = Field(default=None, foreign_key="users.id")
    created_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True))
