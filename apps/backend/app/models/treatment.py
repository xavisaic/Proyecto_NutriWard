import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, Integer, Numeric, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.models.common import utc_now


class MedicationCatalogItem(SQLModel, table=True):
    __tablename__ = "medication_catalog_items"
    __table_args__ = (
        CheckConstraint(
            "clinical_profile IN ('standard','intravenous','continuous_infusion')",
            name="ck_medication_catalog_clinical_profile",
        ),
        Index("ix_medication_catalog_search_active", "normalized_name", "is_active"),
    )

    code: str = Field(primary_key=True, max_length=40)
    alternate_code: str | None = Field(default=None, max_length=40, index=True)
    display_name: str = Field(max_length=300, index=True)
    normalized_name: str = Field(max_length=400, index=True)
    route: str | None = Field(default=None, max_length=80)
    available_inpatient: bool = Field(default=False, sa_type=Boolean)
    available_outpatient: bool = Field(default=False, sa_type=Boolean)
    restriction: str | None = Field(default=None, max_length=1000)
    clinical_profile: str = Field(default="standard", max_length=30, index=True)
    default_category: str = Field(default="other", max_length=40)
    source_version: str = Field(max_length=80, index=True)
    source_row: int = Field(sa_type=Integer)
    is_active: bool = Field(default=True, sa_type=Boolean, index=True)


class AdmissionTreatment(SQLModel, table=True):
    __tablename__ = "admission_treatments"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('medication','nutritional_support')",
            name="ck_admission_treatment_kind",
        ),
        Index("ix_admission_treatments_admission_created", "admission_id", "created_at"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    admission_id: uuid.UUID = Field(foreign_key="admissions.id", index=True)
    kind: str = Field(max_length=30, index=True)
    created_by_user_id: uuid.UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True))


class AdmissionTreatmentVersion(SQLModel, table=True):
    __tablename__ = "admission_treatment_versions"
    __table_args__ = (
        UniqueConstraint("treatment_id", "version", name="uq_treatment_version_number"),
        CheckConstraint("version > 0", name="ck_treatment_version_positive"),
        CheckConstraint(
            "category IN ('nutritional_support','vasoactive','sedative_analgesic',"
            "'antimicrobial','corticosteroid','diuretic','insulin_glycemic',"
            "'gastrointestinal','anticoagulant','other')",
            name="ck_treatment_version_category",
        ),
        CheckConstraint(
            "order_status IN ('draft','active','on_hold','ended','stopped','completed',"
            "'cancelled','entered_in_error','unknown')",
            name="ck_treatment_version_order_status",
        ),
        CheckConstraint(
            "verification_status IN ('pending','verified','stale')",
            name="ck_treatment_version_verification_status",
        ),
        CheckConstraint(
            "dose_value IS NULL OR dose_value >= 0",
            name="ck_treatment_version_dose_non_negative",
        ),
        CheckConstraint(
            "concentration_value IS NULL OR concentration_value >= 0",
            name="ck_treatment_version_concentration_non_negative",
        ),
        CheckConstraint(
            "diluent_volume_ml IS NULL OR diluent_volume_ml >= 0",
            name="ck_treatment_version_diluent_non_negative",
        ),
        CheckConstraint(
            "rate_value IS NULL OR rate_value >= 0",
            name="ck_treatment_version_rate_non_negative",
        ),
        CheckConstraint(
            "infusion_duration_hours IS NULL OR infusion_duration_hours >= 0",
            name="ck_treatment_version_infusion_duration_non_negative",
        ),
        CheckConstraint(
            "administered_volume_ml IS NULL OR administered_volume_ml >= 0",
            name="ck_treatment_version_administered_volume_non_negative",
        ),
        CheckConstraint(
            "prescribed_energy_kcal_day IS NULL OR prescribed_energy_kcal_day >= 0",
            name="ck_treatment_version_energy_non_negative",
        ),
        Index("ix_treatment_versions_treatment_version", "treatment_id", "version"),
        Index("ix_treatment_versions_status", "order_status", "verification_status"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    treatment_id: uuid.UUID = Field(foreign_key="admission_treatments.id", index=True)
    version: int
    previous_version_id: uuid.UUID | None = Field(
        default=None, foreign_key="admission_treatment_versions.id"
    )
    medication_catalog_code: str | None = Field(
        default=None, foreign_key="medication_catalog_items.code", max_length=40, index=True
    )
    raw_medication_text: str | None = Field(default=None, max_length=2000)
    name: str = Field(max_length=300, index=True)
    category: str = Field(max_length=40, index=True)
    prescription_text: str = Field(max_length=2000)
    concentration_value: Decimal | None = Field(default=None, sa_type=Numeric(12, 4))
    concentration_unit: str | None = Field(default=None, max_length=40)
    diluent_volume_ml: Decimal | None = Field(default=None, sa_type=Numeric(12, 2))
    dose_value: Decimal | None = Field(default=None, sa_type=Numeric(12, 4))
    dose_unit: str | None = Field(default=None, max_length=40)
    route: str | None = Field(default=None, max_length=80)
    modality: str | None = Field(default=None, max_length=80)
    frequency: str | None = Field(default=None, max_length=160)
    rate_value: Decimal | None = Field(default=None, sa_type=Numeric(12, 4))
    rate_unit: str | None = Field(default=None, max_length=40)
    infusion_duration_hours: Decimal | None = Field(
        default=None, sa_type=Numeric(10, 2)
    )
    administered_volume_ml: Decimal | None = Field(default=None, sa_type=Numeric(12, 2))
    prescribed_energy_kcal_day: Decimal | None = Field(default=None, sa_type=Numeric(12, 2))
    starts_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True), index=True)
    planned_ends_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    indication: str | None = Field(default=None, max_length=1000)
    order_status: str = Field(max_length=30, index=True)
    source_type: str = Field(max_length=80)
    source_reference: str | None = Field(default=None, max_length=500)
    observed_at: datetime = Field(sa_type=DateTime(timezone=True), index=True)
    verification_status: str = Field(max_length=20, index=True)
    verified_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    verified_by_user_id: uuid.UUID | None = Field(default=None, foreign_key="users.id")
    nutritional_note: str | None = Field(default=None, max_length=2000)
    change_reason: str = Field(max_length=1000)
    created_by_user_id: uuid.UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True))


class AdmissionTreatmentReview(SQLModel, table=True):
    __tablename__ = "admission_treatment_reviews"
    __table_args__ = (
        CheckConstraint(
            "assertion IN ('reviewed_with_findings','no_known','information_unavailable')",
            name="ck_admission_treatment_review_assertion",
        ),
        Index("ix_treatment_reviews_admission_recorded", "admission_id", "recorded_at"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    admission_id: uuid.UUID = Field(foreign_key="admissions.id", index=True)
    assertion: str = Field(max_length=40, index=True)
    source_type: str = Field(max_length=80)
    note: str | None = Field(default=None, max_length=1000)
    recorded_by_user_id: uuid.UUID = Field(foreign_key="users.id")
    recorded_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True))
