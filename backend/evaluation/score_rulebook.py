"""Score rulebook extraction against the hand-verified answer key.

    cd backend && python -m evaluation.score_rulebook candidates.json tests/data/heat_action_plans/delhi_hap_2025_obligations.csv

`candidates.json` is a list of objects with at least `pdf_page_number` and `exact_quote`
(the ObligationCandidate fields in backend/app/rulebook.py).

Recall    = answer-key rows found by at least one candidate on the same page.
Precision = candidates that match at least one answer-key row.
A match is: same page, and one quote contains the other after normalisation, or their
word overlap (Jaccard) is at least 0.6. Normalisation collapses whitespace, removes
whitespace next to hyphens (a pypdf table-cell quirk), and unifies curly quotes and dashes.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from typing import Any


def normalise(text: str) -> str:
    text = (text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
            .replace("–", "-").replace("—", "-"))
    text = re.sub(r"\s+", " ", text).strip().lower()
    return re.sub(r"\s*-\s*", "-", text)


def _words(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", normalise(text)))


def quotes_match(a: str, b: str, threshold: float = 0.6) -> bool:
    na, nb = normalise(a), normalise(b)
    if not na or not nb:
        return False
    if na in nb or nb in na:
        return True
    wa, wb = _words(a), _words(b)
    return bool(wa and wb) and len(wa & wb) / len(wa | wb) >= threshold


def load_key(path: str) -> list[dict[str, Any]]:
    with open(path, encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def score(candidates: list[dict[str, Any]], key: list[dict[str, Any]]) -> dict[str, Any]:
    found_rows, matched_candidates = set(), set()
    for ci, cand in enumerate(candidates):
        page = int(cand.get("pdf_page_number", 0))
        quote = str(cand.get("exact_quote", ""))
        for row in key:
            if int(row["pdf_page"]) == page and quotes_match(quote, row["exact_text_or_anchor"]):
                found_rows.add(row["id"])
                matched_candidates.add(ci)
    total = len(key)
    recall = len(found_rows) / total if total else 0.0
    precision = len(matched_candidates) / len(candidates) if candidates else 0.0
    by_layer = {}
    for layer in sorted({r["text_layer"] for r in key}):
        rows = [r for r in key if r["text_layer"] == layer]
        by_layer[layer] = {"rows": len(rows), "found": sum(1 for r in rows if r["id"] in found_rows)}
    return {
        "recall": round(recall, 3), "precision": round(precision, 3),
        "found": len(found_rows), "key_rows": total, "candidates": len(candidates),
        "by_text_layer": by_layer,
        "missed": [r["id"] for r in key if r["id"] not in found_rows],
        "unmatched_candidates": [i for i in range(len(candidates)) if i not in matched_candidates],
    }


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 2:
        print(__doc__)
        return 2
    with open(args[0], encoding="utf-8") as handle:
        candidates = json.load(handle)
    if isinstance(candidates, dict):
        candidates = candidates.get("candidates", [])
    print(json.dumps(score(candidates, load_key(args[1])), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
