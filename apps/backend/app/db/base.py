from sqlmodel import SQLModel

# Import models here so Alembic/metadata can discover every table.
from app.models.audit_log import AuditLog  # noqa: F401
from app.models.admission import Admission  # noqa: F401
from app.models.admission_status_history import AdmissionStatusHistory  # noqa: F401
from app.models.care_unit import CareUnit  # noqa: F401
from app.models.care_unit_layout_position import CareUnitLayoutPosition  # noqa: F401
from app.models.hospital_service import HospitalService  # noqa: F401
from app.models.nutritionist_service_assignment import (  # noqa: F401
    NutritionistServiceAssignment,
)
from app.models.patient import Patient  # noqa: F401
from app.models.patient_location_history import PatientLocationHistory  # noqa: F401
from app.models.role import Role  # noqa: F401
from app.models.room import Room  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.user_role import UserRole  # noqa: F401


def get_metadata():
    return SQLModel.metadata
