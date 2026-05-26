from sqlmodel import SQLModel

# Import models here so Alembic/metadata can discover tables in future phases.
from app.models.user import User  # noqa: F401


def get_metadata():
    return SQLModel.metadata
