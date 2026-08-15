import uuid
from datetime import date, datetime

from sqlalchemy import CheckConstraint, DateTime, Index, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.models.common import utc_now


class PatientAllergyIntolerance(SQLModel, table=True):
    __tablename__ = "patient_allergy_intolerances"
    __table_args__ = (
        CheckConstraint(
            "allergy_type IS NULL OR allergy_type IN ('allergy','intolerance')",
            name="ck_patient_allergy_type",
        ),
        CheckConstraint(
            "category IN ('food','medication','environment','biologic','other')",
            name="ck_patient_allergy_category",
        ),
        CheckConstraint(
            "clinical_status IS NULL OR clinical_status IN ('active','inactive','resolved')",
            name="ck_patient_allergy_clinical_status",
        ),
        CheckConstraint(
            "verification_status IN ('unconfirmed','presumed','confirmed','refuted','entered_in_error')",
            name="ck_patient_allergy_verification_status",
        ),
        CheckConstraint(
            "criticality IN ('low','high','unable_to_assess')",
            name="ck_patient_allergy_criticality",
        ),
        CheckConstraint("version > 0", name="ck_patient_allergy_version_positive"),
        Index("ix_patient_allergy_patient_status", "patient_id", "clinical_status"),
        Index("ix_patient_allergy_patient_category", "patient_id", "category"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    patient_id: uuid.UUID = Field(foreign_key="patients.id", index=True)
    asserted_admission_id: uuid.UUID | None = Field(default=None, foreign_key="admissions.id", index=True)
    substance_name: str = Field(max_length=500, index=True)
    code_system: str | None = Field(default=None, max_length=100)
    code: str | None = Field(default=None, max_length=100, index=True)
    allergy_type: str | None = Field(default=None, max_length=30, index=True)
    category: str = Field(max_length=30, index=True)
    clinical_status: str | None = Field(default="active", max_length=30, index=True)
    verification_status: str = Field(default="unconfirmed", max_length=30, index=True)
    criticality: str = Field(default="unable_to_assess", max_length=30, index=True)
    onset_date: date | None = None
    source: str = Field(max_length=80)
    note: str | None = Field(default=None, max_length=2000)
    version: int = Field(default=1)
    created_by_user_id: uuid.UUID = Field(foreign_key="users.id")
    updated_by_user_id: uuid.UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True))
    updated_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True))


class AllergyIntoleranceReaction(SQLModel, table=True):
    __tablename__ = "allergy_intolerance_reactions"
    __table_args__ = (
        CheckConstraint(
            "severity IS NULL OR severity IN ('mild','moderate','severe')",
            name="ck_allergy_reaction_severity",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    allergy_intolerance_id: uuid.UUID = Field(
        foreign_key="patient_allergy_intolerances.id", index=True
    )
    manifestation: str = Field(max_length=500, index=True)
    severity: str | None = Field(default=None, max_length=20, index=True)
    occurred_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True), index=True)
    exposure_route: str | None = Field(default=None, max_length=100)
    note: str | None = Field(default=None, max_length=1000)
    created_by_user_id: uuid.UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True))


class AllergyIntoleranceStatusHistory(SQLModel, table=True):
    __tablename__ = "allergy_intolerance_status_history"
    __table_args__ = (
        UniqueConstraint(
            "allergy_intolerance_id",
            "sequence_number",
            name="uq_allergy_status_history_sequence",
        ),
        CheckConstraint("sequence_number > 0", name="ck_allergy_status_history_sequence"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    allergy_intolerance_id: uuid.UUID = Field(
        foreign_key="patient_allergy_intolerances.id", index=True
    )
    sequence_number: int
    from_clinical_status: str | None = Field(default=None, max_length=30)
    to_clinical_status: str | None = Field(default=None, max_length=30)
    from_verification_status: str | None = Field(default=None, max_length=30)
    to_verification_status: str = Field(max_length=30)
    from_criticality: str | None = Field(default=None, max_length=30)
    to_criticality: str = Field(max_length=30)
    reason: str = Field(max_length=1000)
    source: str = Field(max_length=80)
    changed_by_user_id: uuid.UUID = Field(foreign_key="users.id")
    changed_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True), index=True)
    version: int


class PatientAllergyReviewAssertion(SQLModel, table=True):
    __tablename__ = "patient_allergy_review_assertions"
    __table_args__ = (
        CheckConstraint(
            "category IN ('all','food','medication','environment','biologic','other')",
            name="ck_allergy_review_category",
        ),
        CheckConstraint(
            "assertion IN ('not_asked','information_unavailable','no_known','reviewed_with_findings')",
            name="ck_allergy_review_assertion",
        ),
        Index(
            "ix_allergy_review_patient_admission_category",
            "patient_id",
            "admission_id",
            "category",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    patient_id: uuid.UUID = Field(foreign_key="patients.id", index=True)
    admission_id: uuid.UUID = Field(foreign_key="admissions.id", index=True)
    category: str = Field(max_length=30, index=True)
    assertion: str = Field(max_length=40, index=True)
    source: str = Field(max_length=80)
    note: str | None = Field(default=None, max_length=1000)
    recorded_by_user_id: uuid.UUID = Field(foreign_key="users.id")
    recorded_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True), index=True)
