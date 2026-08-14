from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.bed_map import router as bed_map_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.hospital import router as hospital_router
from app.api.v1.endpoints.nutritionist_service_assignments import (
    router as nutritionist_service_assignments_router,
)
from app.api.v1.endpoints.nutrition import router as nutrition_router
from app.api.v1.endpoints.patients import router as patients_router
from app.api.v1.endpoints.roles import router as roles_router
from app.api.v1.endpoints.users import router as users_router
from app.api.v1.endpoints.transfers import router as transfers_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(roles_router)
api_router.include_router(nutritionist_service_assignments_router)
api_router.include_router(nutrition_router)
api_router.include_router(hospital_router)
api_router.include_router(patients_router)
api_router.include_router(bed_map_router)
api_router.include_router(transfers_router)
