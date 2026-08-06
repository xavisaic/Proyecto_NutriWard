import uuid
from datetime import date, datetime

from sqlalchemy import CheckConstraint, DateTime, Index, text
from sqlmodel import Field, SQLModel

from app.models.common import utc_now

IDENTITY_STATUSES = ("unidentified", "provisional", "identified")
PATIENT_SEXES = ("female", "male", "intersex", "unknown")


class Patient(SQLModel, table=True):
    __tablename__ = "patients"
    __table_args__ = (
        CheckConstraint(
            "identity_status IN ('unidentified', 'provisional', 'identified')",
            name="ck_patients_identity_status",
        ),
        CheckConstraint(
            "sex IS NULL OR sex IN ('female', 'male', 'intersex', 'unknown')",
            name="ck_patients_sex",
        ),
        CheckConstraint(
            "(identity_status != 'identified') OR rut IS NOT NULL",
            name="ck_patients_identified_has_rut",
        ),
        CheckConstraint(
            "(identity_status = 'identified') OR temporary_identifier IS NOT NULL",
            name="ck_patients_non_identified_has_temporary_identifier",
        ),
        CheckConstraint(
            "hospital_identifier IS NULL OR hospital_identifier = upper(hospital_identifier)",
            name="ck_patients_hospital_identifier_uppercase",
        ),
        Index(
            "uq_patients_rut_not_null",
            "rut",
            unique=True,
            postgresql_where=text("rut IS NOT NULL"),
            sqlite_where=text("rut IS NOT NULL"),
        ),
        Index(
            "uq_patients_hospital_identifier_not_null",
            "hospital_identifier",
            unique=True,
            postgresql_where=text("hospital_identifier IS NOT NULL"),
            sqlite_where=text("hospital_identifier IS NOT NULL"),
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    identity_status: str = Field(index=True, max_length=20)
    temporary_identifier: str | None = Field(default=None, unique=True, index=True, max_length=40)
    rut: str | None = Field(default=None, index=True, max_length=12)
    given_names: str | None = Field(default=None, index=True, max_length=160)
    first_surname: str | None = Field(default=None, index=True, max_length=100)
    second_surname: str | None = Field(default=None, max_length=100)
    date_of_birth: date | None = None
    date_of_birth_is_estimated: bool = False
    sex: str | None = Field(default=None, max_length=20)
    hospital_identifier: str | None = Field(default=None, max_length=80)
    phone: str | None = Field(default=None, max_length=40)
    provisional_description: str | None = Field(default=None, max_length=1000)
    identified_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    identified_by_user_id: uuid.UUID | None = Field(default=None, foreign_key="users.id")
    merged_into_patient_id: uuid.UUID | None = Field(default=None, foreign_key="patients.id", index=True)
    merged_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    merged_by_user_id: uuid.UUID | None = Field(default=None, foreign_key="users.id")
    merge_reason: str | None = Field(default=None, max_length=500)
    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True))
    updated_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True))
    created_by_user_id: uuid.UUID | None = Field(default=None, foreign_key="users.id")
    updated_by_user_id: uuid.UUID | None = Field(default=None, foreign_key="users.id")
