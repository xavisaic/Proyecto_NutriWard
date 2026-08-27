from sqlmodel import SQLModel

# Import models here so Alembic/metadata can discover every table.
from app.models.audit_log import AuditLog  # noqa: F401
from app.models.allergy import (  # noqa: F401
    AllergyIntoleranceReaction,
    AllergyIntoleranceStatusHistory,
    PatientAllergyIntolerance,
    PatientAllergyReviewAssertion,
)
from app.models.admission import Admission  # noqa: F401
from app.models.admission_status_history import AdmissionStatusHistory  # noqa: F401
from app.models.care_unit import CareUnit  # noqa: F401
from app.models.care_unit_layout_position import CareUnitLayoutPosition  # noqa: F401
from app.models.clinical_context import (  # noqa: F401
    AdmissionClinicalHistoryVersion,
    AdmissionDiagnosis,
    AdmissionDiagnosisStatusHistory,
    PatientCondition,
    PatientConditionStatusHistory,
)
from app.models.hospital_service import HospitalService  # noqa: F401
from app.models.nutritionist_service_assignment import (  # noqa: F401
    NutritionistServiceAssignment,
)
from app.models.nutrition import (  # noqa: F401
    NutritionalAlert,
    NutritionalAnthropometricMeasurement,
    NutritionalAssessment,
    NutritionalCareEncounter,
    NutritionalClinicalContextItem,
    NutritionalDiagnosis,
    NutritionalIntakeRecord,
    NutritionalLabObservation,
    NutritionalMeasurementSession,
    NutritionalMeasurementValue,
    NutritionalMonitoringRecord,
    NutritionalPrescription,
    NutritionalPrescriptionMealTime,
    NutritionalRequirementCalculation,
    NutritionalScreening,
    NutritionalScreeningAnswer,
)
from app.models.patient import Patient  # noqa: F401
from app.models.patient_location_history import PatientLocationHistory  # noqa: F401
from app.models.patient_transfer_request import PatientTransferRequest  # noqa: F401
from app.models.patient_transfer_request_status_history import (  # noqa: F401
    PatientTransferRequestStatusHistory,
)
from app.models.prescription_order import (  # noqa: F401
    EnteralFormulaCatalogItem,
    NutritionPrescriptionMeal,
    NutritionPrescriptionElectrolyte,
    NutritionPrescriptionNonNutritionalContribution,
    NutritionPrescriptionDispatch,
    NutritionPrescriptionMonitoring,
    NutritionPrescriptionOrder,
    NutritionPrescriptionProgression,
    NutritionPrescriptionSetting,
    NutritionPrescriptionSupplement,
)
from app.models.role import Role  # noqa: F401
from app.models.room import Room  # noqa: F401
from app.models.treatment import (  # noqa: F401
    AdmissionTreatment,
    AdmissionTreatmentReview,
    AdmissionTreatmentVersion,
    MedicationCatalogItem,
)
from app.models.user import User  # noqa: F401
from app.models.user_role import UserRole  # noqa: F401


def get_metadata():
    return SQLModel.metadata
