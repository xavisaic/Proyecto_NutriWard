import uuid
from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, Index, Numeric, Time, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.models.common import utc_now


MEAL_TIMES = (
    "breakfast",
    "morning_snack",
    "lunch",
    "afternoon_snack",
    "dinner",
    "night_snack",
)


class FoodRegimenCatalogItem(SQLModel, table=True):
    __tablename__ = "food_regimen_catalog_items"
    __table_args__ = (
        CheckConstraint(
            "item_type IN ('base_regimen','beverage','supplement','dessert',"
            "'bread_or_cereal','modifier','modular_product','other')",
            name="ck_food_catalog_item_type",
        ),
        Index("ix_food_catalog_search_active", "normalized_name", "is_active"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    code: str = Field(unique=True, index=True, max_length=80)
    display_name: str = Field(index=True, max_length=300)
    normalized_name: str = Field(index=True, max_length=400)
    item_type: str = Field(default="other", index=True, max_length=30)
    default_unit: str = Field(default="porción", max_length=30)
    standard_recipe_note: str | None = Field(default=None, max_length=1000)
    source_version: str = Field(default="regimenes-2026-v1", max_length=80)
    source_row: int | None = Field(default=None)
    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True))
    updated_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True))


class NutritionalMealPlan(SQLModel, table=True):
    __tablename__ = "nutritional_meal_plans"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft','finalized','superseded','cancelled')",
            name="ck_meal_plan_status",
        ),
        CheckConstraint(
            "validity_mode IN ('until_changed','single_day','date_range')",
            name="ck_meal_plan_validity_mode",
        ),
        CheckConstraint("version >= 1", name="ck_meal_plan_version"),
        CheckConstraint(
            "effective_until IS NULL OR effective_until >= effective_from",
            name="ck_meal_plan_dates",
        ),
        CheckConstraint(
            "oral_enabled OR enteral_enabled OR parenteral_enabled",
            name="ck_meal_plan_has_route",
        ),
        Index("ix_meal_plan_admission_status_dates", "admission_id", "status", "effective_from"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    admission_id: uuid.UUID = Field(foreign_key="admissions.id", index=True)
    source_prescription_id: uuid.UUID | None = Field(
        default=None, foreign_key="nutritional_prescriptions.id", index=True
    )
    effective_from: date = Field(index=True)
    effective_until: date | None = Field(default=None, index=True)
    validity_mode: str = Field(default="until_changed", max_length=20)
    status: str = Field(default="draft", index=True, max_length=20)
    version: int = Field(default=1)
    oral_enabled: bool = Field(default=True)
    enteral_enabled: bool = Field(default=False)
    parenteral_enabled: bool = Field(default=False)
    general_instructions: str | None = Field(default=None, max_length=4000)
    created_by_user_id: uuid.UUID = Field(foreign_key="users.id")
    updated_by_user_id: uuid.UUID = Field(foreign_key="users.id")
    finalized_by_user_id: uuid.UUID | None = Field(default=None, foreign_key="users.id")
    finalized_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    created_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True))
    updated_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True))


class NutritionalMealPlanSlot(SQLModel, table=True):
    __tablename__ = "nutritional_meal_plan_slots"
    __table_args__ = (
        UniqueConstraint("meal_plan_id", "meal_time", name="uq_meal_plan_slot_time"),
        CheckConstraint(
            "meal_time IN ('breakfast','morning_snack','lunch','afternoon_snack',"
            "'dinner','night_snack')",
            name="ck_meal_plan_slot_time",
        ),
        CheckConstraint(
            "fulfillment_status IN ('ordered','no_tray','not_applicable','hold')",
            name="ck_meal_plan_slot_fulfillment",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    meal_plan_id: uuid.UUID = Field(foreign_key="nutritional_meal_plans.id", index=True)
    meal_time: str = Field(index=True, max_length=30)
    fulfillment_status: str = Field(default="not_applicable", max_length=20)
    is_special: bool = Field(default=False, index=True)
    special_instructions: str | None = Field(default=None, max_length=3000)


class NutritionalMealPlanItem(SQLModel, table=True):
    __tablename__ = "nutritional_meal_plan_items"
    __table_args__ = (
        CheckConstraint(
            "(catalog_item_id IS NOT NULL AND custom_name IS NULL) OR "
            "(catalog_item_id IS NULL AND custom_name IS NOT NULL)",
            name="ck_meal_plan_item_source",
        ),
        CheckConstraint("quantity > 0", name="ck_meal_plan_item_quantity"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    meal_plan_slot_id: uuid.UUID = Field(foreign_key="nutritional_meal_plan_slots.id", index=True)
    catalog_item_id: uuid.UUID | None = Field(
        default=None, foreign_key="food_regimen_catalog_items.id", index=True
    )
    custom_name: str | None = Field(default=None, max_length=500)
    quantity: Decimal = Field(default=Decimal("1"), sa_type=Numeric(12, 3))
    unit: str = Field(default="porción", max_length=30)
    instructions: str | None = Field(default=None, max_length=2000)
    sort_order: int = Field(default=0)


class NutritionalModularPreparation(SQLModel, table=True):
    __tablename__ = "nutritional_modular_preparations"
    __table_args__ = (
        CheckConstraint(
            "preparation_type IN ('protein_bolus','modular_preparation')",
            name="ck_modular_preparation_type",
        ),
        CheckConstraint("powder_grams > 0", name="ck_modular_preparation_powder"),
        CheckConstraint("dilution_volume_ml > 0", name="ck_modular_preparation_volume"),
        CheckConstraint("units_per_delivery > 0", name="ck_modular_preparation_units"),
        CheckConstraint(
            "meal_time IS NULL OR meal_time IN ('breakfast','morning_snack','lunch',"
            "'afternoon_snack','dinner','night_snack')",
            name="ck_modular_preparation_meal_time",
        ),
        CheckConstraint(
            "meal_time IS NOT NULL OR scheduled_time IS NOT NULL",
            name="ck_modular_preparation_schedule",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    meal_plan_id: uuid.UUID = Field(foreign_key="nutritional_meal_plans.id", index=True)
    preparation_type: str = Field(default="protein_bolus", max_length=30)
    product_name: str = Field(default="Módulo proteico", max_length=300)
    powder_grams: Decimal = Field(sa_type=Numeric(12, 3))
    diluent: str = Field(default="Agua", max_length=100)
    dilution_volume_ml: Decimal = Field(sa_type=Numeric(12, 3))
    units_per_delivery: int = Field(default=1)
    meal_time: str | None = Field(default=None, index=True, max_length=30)
    scheduled_time: time | None = Field(default=None, sa_type=Time())
    instructions: str | None = Field(default=None, max_length=2000)
    sort_order: int = Field(default=0)
