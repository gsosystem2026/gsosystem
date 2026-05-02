"""Detect legacy migration workbook shapes (WAR vs IPMT) for validation."""

from __future__ import annotations

BASE_HEADER_TOKENS = {
    "date started",
    "description",
    "requesting office",
    "assigned personnel",
    "status",
}
ACTIVITY_HEADER_TOKENS = {"name of activity", "name of project"}
DATE_COMPLETED_TOKENS = {"date completed", "date complete"}


def _norm(value) -> str:
    return str(value or "").strip()


def find_war_header_row(sheet) -> int | None:
    """Return 1-based row index if this sheet matches a legacy WAR table header."""
    for idx, row in enumerate(sheet.iter_rows(min_row=1, max_row=min(40, sheet.max_row), values_only=True), start=1):
        tokens = {_norm(v).lower().rstrip(":").rstrip() for v in row if _norm(v)}
        normalized = {t.replace("  ", " ") for t in tokens}
        if (
            BASE_HEADER_TOKENS.issubset(normalized)
            and normalized.intersection(ACTIVITY_HEADER_TOKENS)
            and normalized.intersection(DATE_COMPLETED_TOKENS)
        ):
            return idx
    return None


def workbook_has_war_header(wb) -> bool:
    return any(find_war_header_row(sheet) is not None for sheet in wb.worksheets)


def workbook_has_ipmt_fingerprint(wb) -> bool:
    """
    Matches official IPMT sheets (College/Unit block + Success Indicators table),
    including templates that only differ by unit / employee labels.
    """
    if not wb.worksheets:
        return False
    ws = wb.worksheets[0]

    blob = ""
    for r in range(1, min(16, ws.max_row + 1)):
        for c in range(1, min(8, ws.max_column + 1)):
            v = ws.cell(row=r, column=c).value
            if v:
                blob += " " + str(v).lower().replace("\n", " ").replace("\r", " ")
    if "individual performance" in blob and "monitoring" in blob:
        return True

    for idx in range(1, min(30, ws.max_row + 1)):
        left = _norm(ws.cell(row=idx, column=1).value).lower().replace("\n", " ").replace("\r", " ")
        mid = _norm(ws.cell(row=idx, column=2).value).lower().replace("\n", " ").replace("\r", " ")
        if "success indicators" in left and "actual accomplishments" in mid:
            return True

    return False
