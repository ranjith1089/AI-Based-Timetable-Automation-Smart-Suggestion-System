import re
from collections import defaultdict
from typing import Iterable

from fastapi import HTTPException

from .database import supabase_rest_post
from .schemas import ExtractedSubject, SemesterExtractionSummary

COURSE_ROW_PATTERN = re.compile(
    r"^(?P<course_code>[A-Za-z0-9\-_/]+)\s+"
    r"(?P<course_name>.+?)\s+"
    r"(?P<course_type>[A-Za-z]{1,8})\s+"
    r"(?P<ltp>\d+-\d+-\d+)\s+"
    r"(?P<tcp>\d+)\s+"
    r"(?P<credits>\d+(?:\.\d+)?)$"
)
SEMESTER_PATTERN = re.compile(r"semester\s*[-:]?\s*(\d+)", re.IGNORECASE)

IN_MEMORY_SUBJECTS: list[ExtractedSubject] = []


def _parse_ltp(ltp_text: str) -> tuple[int, int, int]:
    parts = ltp_text.strip().split("-")
    if len(parts) != 3:
        raise ValueError("L-T-P must contain three dash-separated integer values")
    return tuple(int(part) for part in parts)


def _iter_pdf_lines(pdf_bytes: bytes) -> Iterable[str]:
    # Lightweight extraction strategy: decode text-like PDF streams and normalize lines.
    decoded = pdf_bytes.decode("latin-1", errors="ignore")
    for line in decoded.splitlines():
        clean_line = re.sub(r"\s+", " ", line).strip()
        if clean_line:
            yield clean_line


def extract_subjects_from_pdf(pdf_bytes: bytes) -> list[ExtractedSubject]:
    subjects: list[ExtractedSubject] = []
    current_semester: int | None = None

    for line in _iter_pdf_lines(pdf_bytes):
        semester_match = SEMESTER_PATTERN.search(line)
        if semester_match:
            current_semester = int(semester_match.group(1))

        row_match = COURSE_ROW_PATTERN.match(line)
        if not row_match:
            continue

        if current_semester is None:
            raise HTTPException(status_code=422, detail="Unable to map rows to semesters. Add 'Semester N' headings.")

        l_val, t_val, p_val = _parse_ltp(row_match.group("ltp"))
        subjects.append(
            ExtractedSubject(
                semester=current_semester,
                course_code=row_match.group("course_code"),
                course_name=row_match.group("course_name"),
                course_type=row_match.group("course_type"),
                l=l_val,
                t=t_val,
                p=p_val,
                tcp=int(row_match.group("tcp")),
                credits=float(row_match.group("credits")),
            )
        )

    return subjects


def validate_by_semester(subjects: list[ExtractedSubject]) -> list[SemesterExtractionSummary]:
    if not subjects:
        raise HTTPException(status_code=422, detail="No curriculum rows matched expected format")

    grouped: dict[int, list[ExtractedSubject]] = defaultdict(list)
    for subject in subjects:
        grouped[subject.semester].append(subject)

    summaries: list[SemesterExtractionSummary] = []
    for semester, rows in sorted(grouped.items()):
        codes = [row.course_code for row in rows]
        duplicates = sorted({code for code in codes if codes.count(code) > 1})
        if duplicates:
            raise HTTPException(
                status_code=422,
                detail=f"Duplicate course codes in semester {semester}: {', '.join(duplicates)}",
            )

        summaries.append(
            SemesterExtractionSummary(
                semester=semester,
                subject_count=len(rows),
                total_credits=round(sum(row.credits for row in rows), 2),
            )
        )

    return summaries


def persist_subjects(tenant_id: str, subjects: list[ExtractedSubject]) -> int:
    persisted = 0
    for subject in subjects:
        payload = {"tenant_id": tenant_id, **subject.model_dump()}
        try:
            supabase_rest_post("curriculum_subjects", payload)
        except Exception:
            IN_MEMORY_SUBJECTS.append(subject)
        persisted += 1
    return persisted
