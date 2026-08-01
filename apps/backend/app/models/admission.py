import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Index, text
from sqlmodel import Field, SQLModel

from app.models.common import utc_now

ADMISSION_STATUSES = ("active", "discharged", "deceased", "closed")


class Admission(SQLModel, table=True):
    __tablename__ = "admissions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'discharged', 'deceased', 'closed')",
            name="ck_admissions_status",
        ),
        Index(
            "uq_admissions_one_active_per_patient",
            "patient_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
            sqlite_where=text("status = 'active'"),
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    patient_id: uuid.UUID = Field(foreign_key="patients.id", index=True)
    admission_identifier: str = Field(unique=True, index=True, max_length=50)
    status: str = Field(default="active", index=True, max_length=20)
    admitted_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True), index=True)
    ended_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    end_reason: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True))
    updated_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True))
    created_by_user_id: uuid.UUID | None = Field(default=None, foreign_key="users.id")
    updated_by_user_id: uuid.UUID | None = Field(default=None, foreign_key="users.id")
