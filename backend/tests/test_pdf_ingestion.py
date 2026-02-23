from fastapi.testclient import TestClient

from app.main import app
from app.pdf_ingestion.normalizer import normalize_subject_rows, parse_ltp

client = TestClient(app)


def test_successful_extraction_semester_i_sample_rows() -> None:
    rows = [
        ["Semester I"],
        ["Course Code", "Course Name", "Course Type", "L-T-P", "TCP", "Credits"],
        ["CS101", "Programming Fundamentals", "Theory", "3-1-0", "4", "4"],
        ["CS102", "Programming Lab", "Lab", "0-0-4", "4", "2"],
    ]

    semesters, errors = normalize_subject_rows(rows)

    assert errors == []
    assert "Semester I" in semesters
    assert len(semesters["Semester I"]) == 2
    assert semesters["Semester I"][0]["L"] == 3
    assert semesters["Semester I"][0]["T"] == 1
    assert semesters["Semester I"][0]["P"] == 0


def test_malformed_or_missing_table_cells_are_reported() -> None:
    rows = [
        ["Semester I"],
        ["CS101", "", "Theory", "3-1-0", "4", "4"],
        ["CS103", "Discrete Mathematics", "Theory", "bad-value", "4", "4"],
        ["only", "two"],
    ]

    semesters, errors = normalize_subject_rows(rows)

    assert semesters == {}
    assert len(errors) == 3


def test_parse_ltp_lit_and_lab_only_formats() -> None:
    assert parse_ltp("3-1-0") == (3, 1, 0)
    assert parse_ltp("2-0-2") == (2, 0, 2)
    assert parse_ltp("0-0-4") == (0, 0, 4)


def test_import_pdf_endpoint_returns_semester_wise_json(monkeypatch) -> None:
    sample_rows = [
        ["Semester I"],
        ["CS101", "Programming Fundamentals", "Theory", "3-1-0", "4", "4"],
    ]

    def _fake_extract(_: str):
        return sample_rows

    monkeypatch.setattr("app.main.extract_raw_tables", _fake_extract)

    response = client.post(
        "/subjects/import-pdf",
        content=b"%PDF-1.4 fake",
        headers={"content-type": "application/pdf"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_subjects"] == 1
    assert "Semester I" in payload["semesters"]
