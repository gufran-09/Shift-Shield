"""Run the app's own Bedrock rulebook extractor over a heat action plan PDF and save the candidates.

    cd backend
    export AWS_REGION=ap-south-1 BEDROCK_MODEL_ID=<inference profile id>
    python -m evaluation.run_rulebook_extraction tests/data/heat_action_plans/delhi_hap_2025.pdf delhi_candidates.json
    python -m evaluation.score_rulebook delhi_candidates.json tests/data/heat_action_plans/delhi_hap_2025_obligations.csv

Runs one page at a time and saves after every page, so a rerun resumes where it stopped.
Use --pages 40-60 to try a small range first.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from pypdf import PdfReader

from app.rulebook import BedrockUnavailable, invoke_candidates


def parse_range(text: str | None, last: int) -> range:
    if not text:
        return range(1, last + 1)
    start, _, end = text.partition("-")
    return range(int(start), int(end or start) + 1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf")
    parser.add_argument("out")
    parser.add_argument("--pages", default=None, help="e.g. 40-60")
    parser.add_argument("--plan-version", default=None)
    args = parser.parse_args()
    if not os.getenv("BEDROCK_MODEL_ID"):
        raise SystemExit("Set BEDROCK_MODEL_ID first (see the docstring).")

    reader = PdfReader(args.pdf)
    pages = {i + 1: (p.extract_text() or "") for i, p in enumerate(reader.pages)}
    plan_version = args.plan_version or Path(args.pdf).stem
    out = Path(args.out)
    state = json.loads(out.read_text()) if out.exists() else {"model": os.getenv("BEDROCK_MODEL_ID"), "done_pages": [], "candidates": []}

    todo = [n for n in parse_range(args.pages, len(pages)) if n not in state["done_pages"]]
    print(f"{len(todo)} pages to run with {state['model']}")
    started = time.time()
    for n in todo:
        if not pages[n].strip():
            state["done_pages"].append(n)
            print(f"p{n}: no text layer, skipped")
            continue
        try:
            # invoke_candidates verifies each quote against the given pages, so pass every page.
            found = [c for c in invoke_candidates({n: pages[n]}, plan_version=plan_version)]
        except BedrockUnavailable as exc:
            print(f"p{n}: FAILED - {exc.__cause__!r}")
            out.write_text(json.dumps(state, indent=1))
            raise SystemExit(1)
        state["candidates"].extend(found)
        state["done_pages"].append(n)
        out.write_text(json.dumps(state, indent=1))
        verified = sum(c["quote_verified"] for c in found)
        print(f"p{n}: {len(found)} candidates ({verified} quote-verified)")
    total = state["candidates"]
    print(f"\nDone in {time.time() - started:.0f}s. {len(total)} candidates, "
          f"{sum(c['quote_verified'] for c in total)} with verified quotes. Saved {out}")


if __name__ == "__main__":
    main()
