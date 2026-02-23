from __future__ import annotations

REQUIRED_FIELDS = ("semester", "code", "name", "course_type", "L", "T", "P", "TCP", "credits")


def validate_subject_record(record: dict) -> list[str]:
    errors: list[str] = []

    for field in REQUIRED_FIELDS:
        value = record.get(field)
        if value is None or value == "":
            errors.append(f"Missing required field: {field}")

    for numeric_field in ("L", "T", "P", "TCP", "credits"):
        value = record.get(numeric_field)
        if value is None:
            continue
        if not isinstance(value, int):
            errors.append(f"Field '{numeric_field}' must be an integer")
            continue
        if value < 0:
            errors.append(f"Field '{numeric_field}' must be >= 0")

    return errors
