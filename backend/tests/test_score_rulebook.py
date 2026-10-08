"""Behaviour of the rulebook scorer. Run from backend/:  pytest tests/test_score_rulebook.py -v"""
from __future__ import annotations

from pathlib import Path

from evaluation.score_rulebook import load_key, quotes_match, score

KEY = load_key(str(Path(__file__).parent / "data" / "heat_action_plans" / "delhi_hap_2025_obligations.csv"))


def test_perfect_extraction_scores_one():
    candidates = [{"pdf_page_number": int(r["pdf_page"]), "exact_quote": r["exact_text_or_anchor"]} for r in KEY]
    result = score(candidates, KEY)
    assert result["recall"] == 1.0 and result["precision"] == 1.0 and result["missed"] == []


def test_wrong_page_does_not_count():
    row = KEY[0]
    result = score([{"pdf_page_number": int(row["pdf_page"]) + 1, "exact_quote": row["exact_text_or_anchor"]}], KEY)
    assert result["found"] == 0 and result["precision"] == 0.0


def test_invented_rule_lowers_precision():
    row = KEY[0]
    candidates = [{"pdf_page_number": int(row["pdf_page"]), "exact_quote": row["exact_text_or_anchor"]},
                  {"pdf_page_number": 56, "exact_quote": "Workers must stop at 11 AM every day."}]
    result = score(candidates, KEY)
    assert result["precision"] == 0.5 and result["unmatched_candidates"] == [1]


def test_pypdf_hyphen_quirk_still_matches():
    assert quotes_match("afternoon hours (1pm -5pm)", "afternoon hours (1pm-5pm)")
    assert quotes_match("regular health -checkup of", "regular health-checkup of")
