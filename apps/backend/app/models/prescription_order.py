import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, Integer, Numeric, UniqueConstraint, text
from sqlmodel import Field, SQLModel

from app.models.common import utc_now


class EnteralFormulaCatalogItem(SQLModel, table=True):
    __tablename__ = "enteral_formula_catalog_items"
    __table_args__ = (
        UniqueConstraint("code", "catalog_version", name="uq_enteral_formula_code_version"),
        CheckConstraint("kcal_per_ml > 0", name="ck_enteral_formula_kcal_positive"),
        Index("ix_enteral_formula_active_name", "is_active", "display_name"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    code: str = Field(max_length=60, index=True)
    display_name: str = Field(max_length=300, index=True)
    manufacturer: str | None = Field(default=None, max_length=200)
    catalog_version: str = Field(max_length=80, index=True)
    kcal_per_ml: Decimal = Field(sa_type=Numeric(10, 4))
    protein_g_per_l: Decimal = Field(default=0, sa_type=Numeric(12, 4))
    carbohydrate_g_per_l: Decimal = Field(default=0, sa_type=Numeric(12, 4))
    lipid_g_per_l: Decimal = Field(default=0, sa_type=Numeric(12, 4))
    fiber_g_per_l: Decimal = Field(default=0, sa_type=Numeric(12, 4))
    sodium_mg_per_l: Decimal = Field(default=0, sa_type=Numeric(12, 4))
    potassium_mg_per_l: Decimal = Field(default=0, sa_type=Numeric(12, 4))
    phosphorus_mg_per_l: Decimal = Field(default=0, sa_type=Numeric(12, 4))
    free_water_ml_per_l: Decimal = Field(default=0, sa_type=Numeric(12, 4))
    is_active: bool = Field(default=True, sa_type=Boolean, index=True)
    created_by_user_id: uuid.UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True))


class NutritionPrescriptionSetting(SQLModel, table=True):
    __tablename__ = "nutrition_prescription_settings"

    key: str = Field(default="default", primary_key=True, max_length=40)
    green_min_percent: Decimal = Field(default=Decimal("90"), sa_type=Numeric(6, 2))
    green_max_percent: Decimal = Field(default=Decimal("110"), sa_type=Numeric(6, 2))
    yellow_min_percent: Decimal = Field(default=Decimal("80"), sa_type=Numeric(6, 2))
    yellow_max_percent: Decimal = Field(default=Decimal("120"), sa_type=Numeric(6, 2))
    updated_by_user_id: uuid.UUID | None = Field(default=None, foreign_key="users.id")
    updated_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True))


class NutritionPrescriptionOrder(SQLModel, table=True):
    __tablename__ = "nutrition_prescription_orders"
    __table_args__ = (
        UniqueConstraint("admission_id", "version_number", name="uq_prescription_order_admission_version"),
        CheckConstraint("version_number > 0", name="ck_prescription_order_version_positive"),
        CheckConstraint("lock_version > 0", name="ck_prescription_order_lock_positive"),
        CheckConstraint("status IN ('draft','validated','active','suspended','superseded','cancelled')", name="ck_prescription_order_status"),
        CheckConstraint("fluid_goal_kind IN ('target','minimum','maximum','range')", name="ck_prescription_order_fluid_goal_kind"),
        CheckConstraint("food_iddsi IS NULL OR (food_iddsi >= 3 AND food_iddsi <= 7)", name="ck_prescription_food_iddsi"),
        CheckConstraint("liquid_iddsi IS NULL OR (liquid_iddsi >= 0 AND liquid_iddsi <= 4)", name="ck_prescription_liquid_iddsi"),
        Index("ix_prescription_order_admission_status", "admission_id", "status"),
        Index(
            "uq_prescription_order_one_active_per_admission",
            "admission_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
            sqlite_where=text("status = 'active'"),
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    admission_id: uuid.UUID = Field(foreign_key="admissions.id", index=True)
    version_number: int = Field(sa_type=Integer)
    lock_version: int = Field(default=1, sa_type=Integer)
    supersedes_order_id: uuid.UUID | None = Field(default=None, foreign_key="nutrition_prescription_orders.id")
    source_encounter_id: uuid.UUID | None = Field(default=None, foreign_key="nutritional_care_encounters.id")
    status: str = Field(default="draft", max_length=20, index=True)
    change_reason: str = Field(max_length=1000)
    effective_from: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    suggested_reassessment_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    oral_enabled: bool = Field(default=False, sa_type=Boolean)
    enteral_enabled: bool = Field(default=False, sa_type=Boolean)
    fasting_enabled: bool = Field(default=False, sa_type=Boolean)
    energy_goal_kcal: Decimal | None = Field(default=None, sa_type=Numeric(12, 2))
    protein_goal_g: Decimal | None = Field(default=None, sa_type=Numeric(12, 2))
    carbohydrate_goal_g: Decimal | None = Field(default=None, sa_type=Numeric(12, 2))
    lipid_goal_g: Decimal | None = Field(default=None, sa_type=Numeric(12, 2))
    fluid_goal_ml: Decimal | None = Field(default=None, sa_type=Numeric(12, 2))
    fluid_goal_kind: str = Field(default="target", max_length=20)
    regimen_type: str | None = Field(default=None, max_length=300)
    food_iddsi: int | None = Field(default=None, sa_type=Integer)
    liquid_iddsi: int | None = Field(default=None, sa_type=Integer)
    restrictions: str | None = Field(default=None, max_length=2000)
    allergies_snapshot: str | None = Field(default=None, max_length=2000)
    feeding_assistance: str | None = Field(default=None, max_length=200)
    kitchen_instructions: str | None = Field(default=None, max_length=3000)
    nursing_instructions: str | None = Field(default=None, max_length=3000)
    oral_energy_kcal: Decimal = Field(default=0, sa_type=Numeric(12, 2))
    oral_protein_g: Decimal = Field(default=0, sa_type=Numeric(12, 2))
    oral_carbohydrate_g: Decimal = Field(default=0, sa_type=Numeric(12, 2))
    oral_lipid_g: Decimal = Field(default=0, sa_type=Numeric(12, 2))
    oral_fluid_ml: Decimal = Field(default=0, sa_type=Numeric(12, 2))
    enteral_formula_id: uuid.UUID | None = Field(default=None, foreign_key="enteral_formula_catalog_items.id")
    enteral_access_route: str | None = Field(default=None, max_length=100)
    enteral_tube_location: str | None = Field(default=None, max_length=100)
    enteral_modality: str | None = Field(default=None, max_length=40)
    enteral_rate_ml_h: Decimal | None = Field(default=None, sa_type=Numeric(12, 2))
    enteral_effective_hours: Decimal | None = Field(default=None, sa_type=Numeric(8, 2))
    enteral_volume_ml: Decimal = Field(default=0, sa_type=Numeric(12, 2))
    water_flush_ml: Decimal = Field(default=0, sa_type=Numeric(12, 2))
    water_flush_every_hours: Decimal | None = Field(default=None, sa_type=Numeric(8, 2))
    medication_pause_hours: Decimal = Field(default=0, sa_type=Numeric(8, 2))
    enteral_starts_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    prescribed_energy_kcal: Decimal = Field(default=0, sa_type=Numeric(12, 2))
    prescribed_protein_g: Decimal = Field(default=0, sa_type=Numeric(12, 2))
    prescribed_carbohydrate_g: Decimal = Field(default=0, sa_type=Numeric(12, 2))
    prescribed_lipid_g: Decimal = Field(default=0, sa_type=Numeric(12, 2))
    prescribed_fluid_ml: Decimal = Field(default=0, sa_type=Numeric(12, 2))
    recipe_text: str | None = Field(default=None, max_length=8000)
    general_observations: str | None = Field(default=None, max_length=3000)
    created_by_user_id: uuid.UUID = Field(foreign_key="users.id")
    validated_by_user_id: uuid.UUID | None = Field(default=None, foreign_key="users.id")
    activated_by_user_id: uuid.UUID | None = Field(default=None, foreign_key="users.id")
    suspended_by_user_id: uuid.UUID | None = Field(default=None, foreign_key="users.id")
    created_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True))
    updated_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True))
    validated_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    activated_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    suspended_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    suspension_reason: str | None = Field(default=None, max_length=1000)


class NutritionPrescriptionMeal(SQLModel, table=True):
    __tablename__ = "nutrition_prescription_order_meals"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    order_id: uuid.UUID = Field(foreign_key="nutrition_prescription_orders.id", index=True)
    meal_time: str = Field(max_length=40)
    instruction: str = Field(max_length=1000)


class NutritionPrescriptionSupplement(SQLModel, table=True):
    __tablename__ = "nutrition_prescription_supplements"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    order_id: uuid.UUID = Field(foreign_key="nutrition_prescription_orders.id", index=True)
    product_type: str = Field(max_length=60)
    product_name: str = Field(max_length=300)
    dose: Decimal | None = Field(default=None, sa_type=Numeric(12, 2))
    dose_unit: str | None = Field(default=None, max_length=40)
    schedule: str | None = Field(default=None, max_length=200)
    route: str | None = Field(default=None, max_length=60)
    duration: str | None = Field(default=None, max_length=200)
    energy_kcal: Decimal = Field(default=0, sa_type=Numeric(12, 2))
    protein_g: Decimal = Field(default=0, sa_type=Numeric(12, 2))
    carbohydrate_g: Decimal = Field(default=0, sa_type=Numeric(12, 2))
    lipid_g: Decimal = Field(default=0, sa_type=Numeric(12, 2))
    fluid_ml: Decimal = Field(default=0, sa_type=Numeric(12, 2))


class NutritionPrescriptionProgression(SQLModel, table=True):
    __tablename__ = "nutrition_prescription_progressions"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    order_id: uuid.UUID = Field(foreign_key="nutrition_prescription_orders.id", index=True)
    sequence: int = Field(sa_type=Integer)
    stage: str = Field(max_length=100)
    rate_ml_h: Decimal = Field(sa_type=Numeric(12, 2))
    duration_hours: Decimal = Field(sa_type=Numeric(8, 2))
    condition: str | None = Field(default=None, max_length=1000)


class NutritionPrescriptionMonitoring(SQLModel, table=True):
    __tablename__ = "nutrition_prescription_monitoring"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    order_id: uuid.UUID = Field(foreign_key="nutrition_prescription_orders.id", index=True)
    parameter: str = Field(max_length=200)
    frequency: str = Field(max_length=200)
    responsible: str | None = Field(default=None, max_length=200)
    instruction: str | None = Field(default=None, max_length=1000)
