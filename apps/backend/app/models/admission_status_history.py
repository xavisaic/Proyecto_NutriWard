import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime
from sqlmodel import Field, SQLModel

from app.models.common import utc_now


class AdmissionStatusHistory(SQLModel, table=True):
    __tablename__ = "admission_status_history"
    __table_args__ = (
        CheckConstraint(
            "from_status IS NULL OR from_status IN ('active', 'discharged', 'deceased', 'closed')",
            name="ck_admission_status_history_from",
        ),
        CheckConstraint(
            "to_status IN ('active', 'discharged', 'deceased', 'closed')",
            name="ck_admission_status_history_to",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    admission_id: uuid.UUID = Field(foreign_key="admissions.id", index=True)
    from_status: str | None = Field(default=None, max_length=20)
    to_status: str = Field(max_length=20)
    reason: str | None = Field(default=None, max_length=500)
    changed_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True), index=True)
    changed_by_user_id: uuid.UUID | None = Field(default=None, foreign_key="users.id")
