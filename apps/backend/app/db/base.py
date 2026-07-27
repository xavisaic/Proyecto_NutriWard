from sqlmodel import SQLModel

# Import models here so Alembic/metadata can discover every table.
from app.models.audit_log import AuditLog  # noqa: F401
from app.models.nutritionist_service_assignment import (  # noqa: F401
    NutritionistServiceAssignment,
)
from app.models.role import Role  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.user_role import UserRole  # noqa: F401


def get_metadata():
    return SQLModel.metadata
