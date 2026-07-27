import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from app.models.common import utc_now

AUDIT_JSON_TYPE = JSON().with_variant(JSONB(), "postgresql")


class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_logs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    actor_user_id: uuid.UUID | None = Field(default=None, foreign_key="users.id", index=True)
    entity_type: str = Field(index=True)
    entity_id: uuid.UUID | None = Field(default=None, index=True)
    action: str = Field(index=True)
    occurred_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True), index=True)
    before_state: dict[str, Any] | None = Field(default=None, sa_type=AUDIT_JSON_TYPE)
    after_state: dict[str, Any] | None = Field(default=None, sa_type=AUDIT_JSON_TYPE)
    admission_id: uuid.UUID | None = Field(default=None, index=True)
