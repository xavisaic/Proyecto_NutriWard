import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Index, text
from sqlmodel import Field, SQLModel

from app.models.common import utc_now

TRANSFER_MODES = ("direct", "reception_tray")
TRANSFER_STATUSES = (
    "requested",
    "pending_reception",
    "accepted",
    "pending_bed",
    "assigned_to_bed",
    "rejected",
    "returned",
    "cancelled",
)
OPEN_TRANSFER_STATUSES = ("requested", "pending_reception", "accepted", "pending_bed")


class PatientTransferRequest(SQLModel, table=True):
    __tablename__ = "patient_transfer_requests"
    __table_args__ = (
        CheckConstraint(
            "origin_service_id != destination_service_id",
            name="ck_transfer_request_different_services",
        ),
        CheckConstraint(
            "transfer_mode IN ('direct', 'reception_tray')",
            name="ck_transfer_request_mode",
        ),
        CheckConstraint(
            "status IN ('requested', 'pending_reception', 'accepted', 'pending_bed', "
            "'assigned_to_bed', 'rejected', 'returned', 'cancelled')",
            name="ck_transfer_request_status",
        ),
        CheckConstraint(
            "status != 'assigned_to_bed' OR destination_care_unit_id IS NOT NULL",
            name="ck_transfer_request_assigned_has_bed",
        ),
        Index(
            "uq_transfer_request_one_open_per_admission",
            "admission_id",
            unique=True,
            postgresql_where=text(
                "status IN ('requested', 'pending_reception', 'accepted', 'pending_bed')"
            ),
            sqlite_where=text(
                "status IN ('requested', 'pending_reception', 'accepted', 'pending_bed')"
            ),
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    admission_id: uuid.UUID = Field(foreign_key="admissions.id", index=True)
    origin_service_id: uuid.UUID = Field(foreign_key="services.id", index=True)
    destination_service_id: uuid.UUID = Field(foreign_key="services.id", index=True)
    origin_care_unit_id: uuid.UUID = Field(foreign_key="care_units.id", index=True)
    destination_care_unit_id: uuid.UUID | None = Field(
        default=None, foreign_key="care_units.id", index=True
    )
    transfer_mode: str = Field(index=True, max_length=30)
    status: str = Field(default="requested", index=True, max_length=30)
    request_reason: str | None = Field(default=None, max_length=500)
    requested_by_user_id: uuid.UUID = Field(foreign_key="users.id")
    requested_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True), index=True)
    completed_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    created_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True))
    updated_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True))
