import uuid
from datetime import datetime

from sqlalchemy import DateTime, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.models.common import utc_now


class NutritionistServiceAssignment(SQLModel, table=True):
    __tablename__ = "nutritionist_service_assignments"
    __table_args__ = (
        UniqueConstraint(
            "nutritionist_user_id",
            "service_id",
            name="uq_nutritionist_service_assignments_user_service",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    nutritionist_user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    # Fase 3 agregará la FK cuando exista la tabla services.
    service_id: uuid.UUID = Field(index=True)
    is_active: bool = True
    created_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True))
    updated_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True))
