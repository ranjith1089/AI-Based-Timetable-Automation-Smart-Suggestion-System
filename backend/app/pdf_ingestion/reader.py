from __future__ import annotations

from pathlib import Path


def extract_raw_tables(pdf_path: str) -> list[list[object]]:
    """Read tables from a PDF and return rows.

    Uses pdfplumber when available.
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    try:
        import pdfplumber  # type: ignore
    except ImportError as exc:
        raise RuntimeError("pdfplumber is required for PDF ingestion") from exc

    rows: list[list[object]] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables() or []
            for table in tables:
                for row in table:
                    if row:
                        rows.append(row)

    return rows
