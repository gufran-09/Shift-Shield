"""The Telangana answer key must agree with the PDF, using the app's own quote check.

Run from backend/:  pytest tests/test_rulebook_answer_key_telangana.py -v
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

import pytest
from pypdf import PdfReader

from app.rulebook import verify_quote

DATA = Path(__file__).parent / "data" / "heat_action_plans"
PDF = DATA / "telangana_hap_2021.pdf"
KEY = DATA / "telangana_hap_2021_obligations.csv"
# pypdf 6.x inserts spaces inside some words on these pages ("drink ing", "work ers", "constructi on");
# pypdf 5.x does not. The app's whitespace-only verify_quote then rejects a correct quote.
KNOWN_EXTRACTION_QUIRKS = {"T08", "T09", "T17"}


def _no_spaces(text: str) -> str:
    return re.sub(r"\s+", "", text)


@pytest.fixture(scope="module")
def pages() -> dict[int, str]:
    reader = PdfReader(str(PDF))
    return {index + 1: (page.extract_text() or "") for index, page in enumerate(reader.pages)}


@pytest.fixture(scope="module")
def key() -> list[dict[str, str]]:
    with KEY.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_answer_key_is_complete_and_verified(key):
    assert len(key) == 26
    assert all(row["verified_by_human"].startswith("yes") for row in key)


def test_every_row_passes_the_app_quote_check(pages, key):
    failures = [row["id"] for row in key if not verify_quote(pages, int(row["pdf_page"]), row["exact_text_or_anchor"])]
    assert set(failures) <= KNOWN_EXTRACTION_QUIRKS, failures


def test_every_row_matches_when_spaces_are_ignored(pages, key):
    for row in key:
        assert _no_spaces(row["exact_text_or_anchor"]) in _no_spaces(pages[int(row["pdf_page"])]), row["id"]


def test_plan_gives_conflicting_peak_windows(pages):
    # The labour rules name two different windows; the second is printed as "11pm – 3pm".
    assert "(12 Noon to 3 PM)" in pages[35]
    assert "(11pm – 3pm)" in pages[59]
