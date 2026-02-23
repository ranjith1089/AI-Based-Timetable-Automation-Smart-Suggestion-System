from __future__ import annotations

import re

from .validator import validate_subject_record


def _to_int(value: object, fallback: int = 0) -> int:
    if isinstance(value, int):
        return value
    if value is None:
        return fallback
    text = str(value).strip()
    if not text:
        return fallback
    digits = re.sub(r"[^0-9]", "", text)
    return int(digits) if digits else fallback


def parse_ltp(value: object) -> tuple[int, int, int]:
    """Parse L-T-P values from strings like '3-1-0', '2:0:2', or '0 0 4'."""
    if value is None:
        raise ValueError("L-T-P value is missing")

    text = str(value).strip()
    if not text:
        raise ValueError("L-T-P value is empty")

    if re.fullmatch(r"\d+", text):
        raise ValueError("L-T-P must include three components")

    parts = [part for part in re.split(r"[^0-9]+", text) if part != ""]
    if len(parts) != 3:
        raise ValueError(f"Could not parse L-T-P value: '{text}'")

    return int(parts[0]), int(parts[1]), int(parts[2])


SEMESTER_PATTERN = re.compile(r"semester\s*[-:]?\s*([ivx0-9]+)", re.IGNORECASE)


def _clean(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def normalize_subject_rows(rows: list[list[object]]) -> tuple[dict[str, list[dict]], list[dict]]:
    """Normalize extracted table rows into semester keyed subject records.

    Returns: (semester_wise_subjects, errors)
    """
    semester_wise: dict[str, list[dict]] = {}
    errors: list[dict] = []

    current_semester = "Unknown"

    for row_index, row in enumerate(rows, start=1):
        cleaned = [_clean(cell) for cell in row]
        meaningful_cells = [cell for cell in cleaned if cell]
        if not meaningful_cells:
            continue

        row_text = " ".join(meaningful_cells)
        semester_match = SEMESTER_PATTERN.search(row_text)
        if semester_match and len(meaningful_cells) <= 3:
            current_semester = f"Semester {semester_match.group(1).upper()}"
            semester_wise.setdefault(current_semester, [])
            continue

        if any(
            token in row_text.lower()
            for token in ("course code", "subject code", "course name", "l-t-p", "credits", "tcp")
        ):
            continue

        if len(cleaned) < 5:
            errors.append({"row": row_index, "error": "Row has too few columns", "data": cleaned})
            continue

        code = cleaned[0]
        name = cleaned[1]
        course_type = cleaned[2]
        ltp_raw = cleaned[3]
        tcp_raw = cleaned[4] if len(cleaned) > 4 else ""
        credits_raw = cleaned[5] if len(cleaned) > 5 else ""

        try:
            l_value, t_value, p_value = parse_ltp(ltp_raw)
        except ValueError as exc:
            errors.append({"row": row_index, "error": str(exc), "data": cleaned})
            continue

        record = {
            "semester": current_semester,
            "code": code,
            "name": name,
            "course_type": course_type,
            "L": l_value,
            "T": t_value,
            "P": p_value,
            "TCP": _to_int(tcp_raw),
            "credits": _to_int(credits_raw),
        }

        validation_errors = validate_subject_record(record)
        if validation_errors:
            errors.append({"row": row_index, "error": validation_errors, "data": cleaned})
            continue

        semester_wise.setdefault(current_semester, []).append(record)

    # keep Unknown key only when it has records
    semester_wise = {semester: subjects for semester, subjects in semester_wise.items() if subjects}
    return semester_wise, errors
