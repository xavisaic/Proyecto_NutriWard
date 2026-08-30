import uuid
from datetime import date, datetime, time
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.food_production import MEAL_TIMES
from app.schemas.patient import normalize_optional_text, normalize_required_text


MealTime = Literal[
    "breakfast",
    "morning_snack",
    "lunch",
    "afternoon_snack",
    "dinner",
    "night_snack",
]


class FoodCatalogItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    display_name: str
    item_type: str
    default_unit: str
    standard_recipe_note: str | None
    is_active: bool


class FoodCatalogItemCreate(BaseModel):
    display_name: str = Field(min_length=1, max_length=300)
    item_type: Literal[
        "base_regimen",
        "beverage",
        "supplement",
        "dessert",
        "bread_or_cereal",
        "modifier",
        "modular_product",
        "other",
    ] = "other"
    default_unit: str = Field(default="porción", min_length=1, max_length=30)
    standard_recipe_note: str | None = Field(default=None, max_length=1000)

    _name = field_validator("display_name", "default_unit")(normalize_required_text)
    _note = field_validator("standard_recipe_note")(normalize_optional_text)


class FoodCatalogItemUpdate(FoodCatalogItemCreate):
    is_active: bool = True


class MealPlanItemInput(BaseModel):
    catalog_item_id: uuid.UUID | None = None
    custom_name: str | None = Field(default=None, max_length=500)
    quantity: Decimal = Field(default=Decimal("1"), gt=0)
    unit: str = Field(default="porción", min_length=1, max_length=30)
    instructions: str | None = Field(default=None, max_length=2000)

    _custom = field_validator("custom_name", "instructions")(normalize_optional_text)
    _unit = field_validator("unit")(normalize_required_text)

    @model_validator(mode="after")
    def validate_source(self):
        if (self.catalog_item_id is None) == (self.custom_name is None):
            raise ValueError("Seleccione un ítem del catálogo o indique una preparación libre.")
        if self.catalog_item_id is not None and self.quantity != self.quantity.to_integral_value():
            raise ValueError("La cantidad de un ítem del catálogo debe ser un número entero.")
        return self


class MealPlanSlotInput(BaseModel):
    meal_time: MealTime
    fulfillment_status: Literal["ordered", "no_tray", "not_applicable", "hold"]
    is_special: bool = False
    special_instructions: str | None = Field(default=None, max_length=3000)
    items: list[MealPlanItemInput] = Field(default_factory=list, max_length=30)

    _instructions = field_validator("special_instructions")(normalize_optional_text)

    @model_validator(mode="after")
    def validate_items(self):
        if self.fulfillment_status == "ordered" and not self.items:
            raise ValueError("Una bandeja solicitada debe incluir al menos un ítem.")
        if self.fulfillment_status != "ordered" and self.items:
            raise ValueError("Un tiempo sin bandeja no puede contener preparaciones orales.")
        return self


class ModularPreparationInput(BaseModel):
    preparation_type: Literal["protein_bolus", "modular_preparation"] = "protein_bolus"
    product_name: str = Field(default="Módulo proteico", min_length=1, max_length=300)
    powder_grams: Decimal = Field(gt=0)
    diluent: str = Field(default="Agua", min_length=1, max_length=100)
    dilution_volume_ml: Decimal = Field(gt=0)
    units_per_delivery: int = Field(default=1, ge=1, le=50)
    meal_time: MealTime | None = None
    scheduled_time: time | None = None
    instructions: str | None = Field(default=None, max_length=2000)

    _required = field_validator("product_name", "diluent")(normalize_required_text)
    _instructions = field_validator("instructions")(normalize_optional_text)

    @model_validator(mode="after")
    def validate_schedule(self):
        if self.meal_time is None and self.scheduled_time is None:
            raise ValueError("Indique un tiempo de comida o una hora de entrega.")
        return self


class MealPlanBaseInput(BaseModel):
    effective_from: date
    effective_until: date | None = None
    validity_mode: Literal["until_changed", "single_day", "date_range"] = "until_changed"
    oral_enabled: bool = True
    enteral_enabled: bool = False
    parenteral_enabled: bool = False
    general_instructions: str | None = Field(default=None, max_length=4000)
    slots: list[MealPlanSlotInput] = Field(default_factory=list, max_length=6)
    modular_preparations: list[ModularPreparationInput] = Field(default_factory=list, max_length=30)

    _instructions = field_validator("general_instructions")(normalize_optional_text)

    @model_validator(mode="after")
    def validate_plan(self):
        if not (self.oral_enabled or self.enteral_enabled or self.parenteral_enabled):
            raise ValueError("Seleccione al menos una vía de alimentación.")
        if self.validity_mode == "single_day":
            self.effective_until = self.effective_from
        elif self.validity_mode == "date_range" and self.effective_until is None:
            raise ValueError("Una vigencia por rango requiere fecha de término.")
        elif self.validity_mode == "until_changed":
            self.effective_until = None
        if self.effective_until and self.effective_until < self.effective_from:
            raise ValueError("La fecha de término no puede preceder al inicio.")
        times = [slot.meal_time for slot in self.slots]
        if len(times) != len(set(times)):
            raise ValueError("Cada tiempo de comida puede aparecer una sola vez.")
        if self.oral_enabled and set(times) != set(MEAL_TIMES):
            raise ValueError("Una minuta oral debe definir los seis tiempos de comida.")
        if not self.oral_enabled and any(slot.fulfillment_status == "ordered" for slot in self.slots):
            raise ValueError("No puede solicitar bandejas si la vía oral no está activa.")
        return self


class MealPlanCreate(MealPlanBaseInput):
    pass


class MealPlanUpdate(MealPlanBaseInput):
    version: int = Field(ge=1)


class MealPlanItemRead(BaseModel):
    id: uuid.UUID
    catalog_item_id: uuid.UUID | None
    catalog_code: str | None = None
    display_name: str
    is_custom: bool
    quantity: Decimal
    unit: str
    instructions: str | None
    sort_order: int


class MealPlanSlotRead(BaseModel):
    id: uuid.UUID
    meal_time: MealTime
    fulfillment_status: str
    is_special: bool
    special_instructions: str | None
    items: list[MealPlanItemRead]


class ModularPreparationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    preparation_type: str
    product_name: str
    powder_grams: Decimal
    diluent: str
    dilution_volume_ml: Decimal
    units_per_delivery: int
    meal_time: MealTime | None
    scheduled_time: time | None
    instructions: str | None
    sort_order: int


class MealPlanRead(BaseModel):
    id: uuid.UUID
    admission_id: uuid.UUID
    effective_from: date
    effective_until: date | None
    validity_mode: str
    status: str
    version: int
    oral_enabled: bool
    enteral_enabled: bool
    parenteral_enabled: bool
    general_instructions: str | None
    created_by_user_id: uuid.UUID
    updated_by_user_id: uuid.UUID
    finalized_by_user_id: uuid.UUID | None
    finalized_at: datetime | None
    created_at: datetime
    updated_at: datetime
    slots: list[MealPlanSlotRead]
    modular_preparations: list[ModularPreparationRead]


class MealPlanFinalize(BaseModel):
    version: int = Field(ge=1)


class ProductionSummaryLine(BaseModel):
    service_id: uuid.UUID
    service_name: str
    meal_time: MealTime
    standard_rations: int
    special_rations: int
    total_rations: int


class ProductionPreparationLine(BaseModel):
    service_name: str
    meal_time: MealTime
    item_name: str
    quantity: Decimal
    unit: str
    patient_count: int


class ProductionRationDetail(BaseModel):
    admission_id: uuid.UUID
    patient_name: str
    service_name: str
    room_name: str
    bed_name: str
    meal_time: MealTime
    ration_count: int
    is_special: bool
    items: list[str]
    instructions: str | None
    food_safety_alerts: list[str]


class ProductionModularDetail(BaseModel):
    admission_id: uuid.UUID
    patient_name: str
    service_name: str
    room_name: str
    bed_name: str
    delivery: str
    product_name: str
    powder_grams: Decimal
    diluent: str
    dilution_volume_ml: Decimal
    units_per_delivery: int
    instructions: str | None


class ProductionException(BaseModel):
    admission_id: uuid.UUID
    patient_name: str
    service_name: str | None
    room_name: str | None
    bed_name: str | None
    reason: str


class ProductionConsolidatedRead(BaseModel):
    service_date: date
    generated_at: datetime
    meal_time: MealTime | None
    summaries: list[ProductionSummaryLine]
    preparations: list[ProductionPreparationLine]
    rations: list[ProductionRationDetail]
    modular_preparations: list[ProductionModularDetail]
    exceptions: list[ProductionException]
