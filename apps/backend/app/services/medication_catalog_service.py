import re
import unicodedata
from difflib import SequenceMatcher

from sqlmodel import Session, select

from app.models.treatment import MedicationCatalogItem
from app.schemas.treatment import (
    MedicationCatalogItemRead,
    MedicationCatalogList,
    MedicationCatalogMatchItem,
    MedicationCatalogMatchResponse,
)


def normalize_catalog_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    without_marks = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"[^A-Z0-9%]+", " ", without_marks.upper()).strip()


def _catalog_read(row: MedicationCatalogItem) -> MedicationCatalogItemRead:
    return MedicationCatalogItemRead.model_validate(row)


def list_medication_catalog(
    session: Session,
    *,
    query: str | None = None,
    availability: str = "all",
    limit: int = 25,
) -> MedicationCatalogList:
    rows = list(
        session.exec(
            select(MedicationCatalogItem)
            .where(MedicationCatalogItem.is_active.is_(True))
            .order_by(MedicationCatalogItem.display_name, MedicationCatalogItem.code)
        ).all()
    )
    if availability == "inpatient":
        rows = [row for row in rows if row.available_inpatient]
    elif availability == "outpatient":
        rows = [row for row in rows if row.available_outpatient]
    elif availability == "both":
        rows = [
            row
            for row in rows
            if row.available_inpatient and row.available_outpatient
        ]

    normalized_query = normalize_catalog_text(query or "")
    if normalized_query:
        query_tokens = set(normalized_query.split())

        def rank(row: MedicationCatalogItem) -> int:
            code = normalize_catalog_text(row.code)
            alternate = normalize_catalog_text(row.alternate_code or "")
            name = row.normalized_name
            if normalized_query in {code, alternate, name}:
                return 100
            if code.startswith(normalized_query) or alternate.startswith(normalized_query):
                return 95
            if name.startswith(normalized_query):
                return 90
            if query_tokens <= set(name.split()):
                return 80
            if normalized_query in name:
                return 70
            return 0

        ranked = [(rank(row), row) for row in rows]
        rows = [
            row
            for score, row in sorted(
                (item for item in ranked if item[0] > 0),
                key=lambda item: (-item[0], item[1].display_name, item[1].code),
            )
        ]

    total = len(rows)
    return MedicationCatalogList(
        items=[_catalog_read(row) for row in rows[:limit]],
        total=total,
    )


def get_catalog_item(session: Session, code: str) -> MedicationCatalogItem | None:
    row = session.get(MedicationCatalogItem, code.strip())
    if row is None or not row.is_active:
        return None
    return row


def _source_line(value: str) -> str:
    return re.sub(r"^\s*(?:(?:[-*\u2022]+)|(?:\d+[.)-]))\s*", "", value).strip()


def match_medication_lines(
    session: Session, lines: list[str]
) -> MedicationCatalogMatchResponse:
    catalog = list(
        session.exec(
            select(MedicationCatalogItem)
            .where(MedicationCatalogItem.is_active.is_(True))
            .order_by(MedicationCatalogItem.display_name, MedicationCatalogItem.code)
        ).all()
    )
    by_name: dict[str, list[MedicationCatalogItem]] = {}
    by_code: dict[str, MedicationCatalogItem] = {}
    for row in catalog:
        by_name.setdefault(row.normalized_name, []).append(row)
        by_code[normalize_catalog_text(row.code)] = row
        if row.alternate_code:
            by_code[normalize_catalog_text(row.alternate_code)] = row

    results: list[MedicationCatalogMatchItem] = []
    for original in lines:
        source = _source_line(original)
        normalized = normalize_catalog_text(source)
        exact = by_name.get(normalized, [])
        code_match = by_code.get(normalized)
        if code_match is not None:
            exact = [code_match]
        if len(exact) == 1:
            results.append(
                MedicationCatalogMatchItem(
                    source_text=original,
                    status="matched",
                    match=_catalog_read(exact[0]),
                )
            )
            continue

        source_tokens = set(normalized.split())
        scored: list[tuple[float, MedicationCatalogItem]] = []
        for row in catalog:
            name = row.normalized_name
            ratio = SequenceMatcher(None, normalized, name).ratio()
            overlap = len(source_tokens & set(name.split())) / max(len(source_tokens), 1)
            containment = 0.92 if name in normalized or normalized in name else 0.0
            score = max(ratio, overlap, containment)
            if score >= 0.45:
                scored.append((score, row))
        suggestions = [
            _catalog_read(row)
            for _, row in sorted(
                scored,
                key=lambda item: (-item[0], item[1].display_name, item[1].code),
            )[:5]
        ]
        results.append(
            MedicationCatalogMatchItem(
                source_text=original,
                status="ambiguous" if suggestions else "unmatched",
                suggestions=suggestions,
            )
        )
    return MedicationCatalogMatchResponse(items=results)
