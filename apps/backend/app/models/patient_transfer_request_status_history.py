import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.models.common import utc_now


class PatientTransferRequestStatusHistory(SQLModel, table=True):
    __tablename__ = "patient_transfer_request_status_history"
    __table_args__ = (
        UniqueConstraint(
            "transfer_request_id",
            "sequence_number",
            name="uq_transfer_status_history_sequence",
        ),
        CheckConstraint("sequence_number > 0", name="ck_transfer_status_history_sequence_positive"),
        CheckConstraint(
            "from_status IS NULL OR from_status IN ('requested', 'pending_reception', "
            "'accepted', 'pending_bed', 'assigned_to_bed', 'rejected', 'returned', 'cancelled')",
            name="ck_transfer_status_history_from",
        ),
        CheckConstraint(
            "to_status IN ('requested', 'pending_reception', 'accepted', 'pending_bed', "
            "'assigned_to_bed', 'rejected', 'returned', 'cancelled')",
            name="ck_transfer_status_history_to",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    transfer_request_id: uuid.UUID = Field(
        foreign_key="patient_transfer_requests.id", index=True
    )
    sequence_number: int
    from_status: str | None = Field(default=None, max_length=30)
    to_status: str = Field(max_length=30, index=True)
    reason: str | None = Field(default=None, max_length=500)
    changed_by_user_id: uuid.UUID = Field(foreign_key="users.id")
    changed_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True), index=True)
    is_coverage: bool = Field(default=False, sa_type=Boolean())
