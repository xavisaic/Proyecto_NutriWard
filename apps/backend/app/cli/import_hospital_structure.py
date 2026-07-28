import argparse
import json
from pathlib import Path

from sqlmodel import Session

from app.db.base import get_metadata
from app.db.session import engine
from app.services.hospital_structure_import_service import (
    HospitalStructureImportError,
    import_hospital_structure,
    read_hospital_workbook,
    workbook_sha256,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Valida e importa la estructura hospitalaria desde un archivo Excel."
    )
    parser.add_argument("workbook", type=Path, help="Ruta al archivo .xlsx.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Confirma los cambios. Sin esta opción se ejecuta una simulación con rollback.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    workbook_path = args.workbook.resolve()
    get_metadata()
    try:
        rows = read_hospital_workbook(workbook_path)
        checksum = workbook_sha256(workbook_path)
        with Session(engine) as session:
            report = import_hospital_structure(
                session,
                rows,
                source_name=workbook_path.name,
                source_sha256=checksum,
            )
            if args.apply:
                session.commit()
            else:
                session.rollback()
    except HospitalStructureImportError as error:
        print(json.dumps({"status": "error", "detail": str(error)}, ensure_ascii=False))
        return 2

    result = {
        "status": "applied" if args.apply else "dry-run",
        **report.as_dict(),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
