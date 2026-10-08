"""The hand-verified Delhi answer key must agree with the PDF, using the app's own quote check.

Run from backend/:  pytest tests/test_rulebook_answer_key.py -v
"""
from __future__ import annotations

import csv
from pathlib import Path

import pytest
from pypdf import PdfReader

from app.rulebook import verify_quote
from evaluation.score_rulebook import normalise

DATA = Path(__file__).parent / "data" / "heat_action_plans"
PDF = DATA / "delhi_hap_2025.pdf"
KEY = DATA / "delhi_hap_2025_obligations.csv"
# pypdf reads these table-cell phrases with a space before the hyphen ("1pm -5pm").
KNOWN_EXTRACTION_QUIRKS = {"D04", "D08"}


@pytest.fixture(scope="module")
def pages() -> dict[int, str]:
    reader = PdfReader(str(PDF))
    return {index + 1: (page.extract_text() or "") for index, page in enumerate(reader.pages)}


@pytest.fixture(scope="module")
def key() -> list[dict[str, str]]:
    with KEY.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_answer_key_is_complete_and_verified(key):
    assert len(key) == 48
    assert all(row["verified_by_human"].startswith("yes") for row in key)
    assert sum(row["text_layer"] == "text" for row in key) == 33


def test_text_layer_rows_pass_the_app_quote_check(pages, key):
    failures = [row["id"] for row in key if row["text_layer"] == "text"
                and not verify_quote(pages, int(row["pdf_page"]), row["exact_text_or_anchor"])]
    assert set(failures) <= KNOWN_EXTRACTION_QUIRKS, failures


def test_hyphen_tolerant_check_passes_every_text_row(pages, key):
    for row in key:
        if row["text_layer"] == "text":
            assert normalise(row["exact_text_or_anchor"]) in normalise(pages[int(row["pdf_page"])]), row["id"]


def test_scanned_circular_has_no_text_layer(pages, key):
    scanned_pages = {int(row["pdf_page"]) for row in key if row["text_layer"] != "text"}
    assert scanned_pages == {155, 156}
    for page in scanned_pages:
        assert len(pages[page].strip()) < 20, "page now has text; switch these rows to quote checks"
