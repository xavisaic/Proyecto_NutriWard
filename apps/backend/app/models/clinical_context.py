import uuid
from datetime import date, datetime

from sqlalchemy import CheckConstraint, DateTime, Index, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.models.common import utc_now


class PatientCondition(SQLModel, table=True):
    __tablename__ = "patient_conditions"
    __table_args__ = (
        CheckConstraint(
            "clinical_status IN ('active','inactive','remission','resolved','entered_in_error')",
            name="ck_patient_condition_clinical_status",
        ),
        CheckConstraint(
            "verification_status IN ('unconfirmed','confirmed','refuted')",
            name="ck_patient_condition_verification_status",
        ),
        CheckConstraint("version > 0", name="ck_patient_condition_version_positive"),
        Index("ix_patient_condition_patient_status", "patient_id", "clinical_status"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    patient_id: uuid.UUID = Field(foreign_key="patients.id", index=True)
    condition_name: str = Field(max_length=500, index=True)
    code_system: str | None = Field(default=None, max_length=50)
    code: str | None = Field(default=None, max_length=50, index=True)
    clinical_status: str = Field(default="active", max_length=30, index=True)
    verification_status: str = Field(default="confirmed", max_length=30, index=True)
    onset_date: date | None = None
    resolved_on: date | None = None
    source: str = Field(max_length=80)
    note: str | None = Field(default=None, max_length=2000)
    version: int = Field(default=1)
    created_by_user_id: uuid.UUID = Field(foreign_key="users.id")
    updated_by_user_id: uuid.UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True))
    updated_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True))


class PatientConditionStatusHistory(SQLModel, table=True):
    __tablename__ = "patient_condition_status_history"
    __table_args__ = (
        UniqueConstraint(
            "patient_condition_id", "sequence_number", name="uq_patient_condition_history_sequence"
        ),
        CheckConstraint("sequence_number > 0", name="ck_patient_condition_history_sequence"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    patient_condition_id: uuid.UUID = Field(foreign_key="patient_conditions.id", index=True)
    sequence_number: int
    from_clinical_status: str | None = Field(default=None, max_length=30)
    to_clinical_status: str = Field(max_length=30)
    from_verification_status: str | None = Field(default=None, max_length=30)
    to_verification_status: str = Field(max_length=30)
    reason: str = Field(max_length=1000)
    source: str = Field(max_length=80)
    changed_by_user_id: uuid.UUID = Field(foreign_key="users.id")
    changed_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True), index=True)
    version: int


class AdmissionDiagnosis(SQLModel, table=True):
    __tablename__ = "admission_diagnoses"
    __table_args__ = (
        CheckConstraint(
            "diagnosis_type IN ('principal','secondary','complication')",
            name="ck_admission_diagnosis_type",
        ),
        CheckConstraint(
            "clinical_status IN ('active','resolved','entered_in_error')",
            name="ck_admission_diagnosis_clinical_status",
        ),
        CheckConstraint(
            "verification_status IN ('provisional','confirmed','ruled_out')",
            name="ck_admission_diagnosis_verification_status",
        ),
        CheckConstraint("version > 0", name="ck_admission_diagnosis_version_positive"),
        Index("ix_admission_diagnosis_admission_status", "admission_id", "clinical_status"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    admission_id: uuid.UUID = Field(foreign_key="admissions.id", index=True)
    diagnosis_name: str = Field(max_length=500, index=True)
    code_system: str | None = Field(default=None, max_length=50)
    code: str | None = Field(default=None, max_length=50, index=True)
    diagnosis_type: str = Field(default="secondary", max_length=30, index=True)
    clinical_status: str = Field(default="active", max_length=30, index=True)
    verification_status: str = Field(default="provisional", max_length=30, index=True)
    present_on_admission: bool = True
    diagnosed_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True), index=True)
    resolved_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    source: str = Field(max_length=80)
    note: str | None = Field(default=None, max_length=2000)
    version: int = Field(default=1)
    created_by_user_id: uuid.UUID = Field(foreign_key="users.id")
    updated_by_user_id: uuid.UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True))
    updated_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True))


class AdmissionDiagnosisStatusHistory(SQLModel, table=True):
    __tablename__ = "admission_diagnosis_status_history"
    __table_args__ = (
        UniqueConstraint(
            "admission_diagnosis_id", "sequence_number", name="uq_admission_diagnosis_history_sequence"
        ),
        CheckConstraint("sequence_number > 0", name="ck_admission_diagnosis_history_sequence"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    admission_diagnosis_id: uuid.UUID = Field(foreign_key="admission_diagnoses.id", index=True)
    sequence_number: int
    from_clinical_status: str | None = Field(default=None, max_length=30)
    to_clinical_status: str = Field(max_length=30)
    from_verification_status: str | None = Field(default=None, max_length=30)
    to_verification_status: str = Field(max_length=30)
    reason: str = Field(max_length=1000)
    source: str = Field(max_length=80)
    changed_by_user_id: uuid.UUID = Field(foreign_key="users.id")
    changed_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True), index=True)
    version: int
