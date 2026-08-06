import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import CurrentSession, DatabaseSession, require_roles
from app.schemas.bed_map import BedMapResponse
from app.services.bed_map_service import get_bed_map

router = APIRouter(tags=["bed-map"])
BedMapReader = Annotated[
    CurrentSession,
    Depends(require_roles("administrador", "jefatura", "nutricionista", "alimentacion")),
]


@router.get("/bed-map", response_model=BedMapResponse)
def read_bed_map(
    _: BedMapReader,
    session: DatabaseSession,
    service_id: uuid.UUID = Query(),
) -> BedMapResponse:
    return get_bed_map(session, service_id)
