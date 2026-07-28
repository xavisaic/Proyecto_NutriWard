from pathlib import Path

import pytest
from openpyxl import Workbook
from sqlmodel import select

from app.models.audit_log import AuditLog
from app.models.care_unit import CareUnit
from app.models.care_unit_layout_position import CareUnitLayoutPosition
from app.models.hospital_service import HospitalService
from app.models.room import Room
from app.services.hospital_structure_import_service import (
    EXPECTED_HEADERS,
    HospitalImportRow,
    HospitalStructureImportError,
    import_hospital_structure,
    read_hospital_workbook,
)


def _save_workbook(path: Path, rows: list[list[object]]) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(list(EXPECTED_HEADERS))
    for row in rows:
        sheet.append(row)
    workbook.save(path)
    workbook.close()


def test_reads_and_normalizes_supported_care_unit_types(tmp_path) -> None:
    path = tmp_path / "estructura.xlsx"
    _save_workbook(
        path,
        [
            ["Servicio A", "Sala 1", "Cama", "1, 2", 2, "—"],
            ["Servicio A", "Sala 2", "Camilla", "1", 1, "Observación"],
            ["Servicio A", "Sala 3", "Puesto", "1", 1, None],
            ["Servicio A", "Sala 4", "Box", "1", 1, "-"],
        ],
    )

    rows = read_hospital_workbook(path)

    assert [row.unit_type for row in rows] == ["bed", "stretcher", "station", "box"]
    assert rows[0].unit_codes == ("1", "2")
    assert rows[0].notes is None
    assert rows[1].notes == "Observación"


def test_rejects_quantity_that_does_not_match_codes(tmp_path) -> None:
    path = tmp_path / "estructura_invalida.xlsx"
    _save_workbook(
        path,
        [["Servicio A", "Sala 1", "Puesto", "1, 2", 1, None]],
    )

    with pytest.raises(HospitalStructureImportError, match="Cantidad indica 1"):
        read_hospital_workbook(path)


def test_import_is_idempotent_and_preserves_room_notes(db_session) -> None:
    rows = [
        HospitalImportRow(
            source_row=2,
            service_name="Servicio de Prueba",
            room_name="Sala Norte",
            unit_type="stretcher",
            unit_codes=("1", "2"),
            quantity=2,
            notes="Sector de observación",
        )
    ]

    first = import_hospital_structure(
        db_session,
        rows,
        source_name="estructura.xlsx",
        source_sha256="a" * 64,
    )
    db_session.commit()

    assert first.services_created == 1
    assert first.rooms_created == 1
    assert first.care_units_created == 2
    assert first.layouts_created == 2

    service = db_session.exec(
        select(HospitalService).where(HospitalService.name == "Servicio de Prueba")
    ).one()
    room = db_session.exec(
        select(Room).where(Room.service_id == service.id, Room.code == "SALA-NORTE")
    ).one()
    care_units = db_session.exec(
        select(CareUnit).where(CareUnit.room_id == room.id).order_by(CareUnit.code)
    ).all()
    layouts = db_session.exec(
        select(CareUnitLayoutPosition).where(
            CareUnitLayoutPosition.care_unit_id.in_([unit.id for unit in care_units])
        )
    ).all()
    assert room.notes == "Sector de observación"
    assert [(unit.code, unit.unit_type) for unit in care_units] == [
        ("1", "stretcher"),
        ("2", "stretcher"),
    ]
    assert len(layouts) == 2

    second = import_hospital_structure(
        db_session,
        rows,
        source_name="estructura.xlsx",
        source_sha256="a" * 64,
    )
    db_session.commit()

    assert second.services_created == 0
    assert second.services_updated == 0
    assert second.rooms_created == 0
    assert second.rooms_updated == 0
    assert second.care_units_created == 0
    assert second.care_units_updated == 0
    assert second.layouts_created == 0
    assert second.layouts_updated == 0
    audits = db_session.exec(
        select(AuditLog).where(
            AuditLog.entity_type == "hospital_structure",
            AuditLog.action == "import",
        )
    ).all()
    assert len(audits) == 2
