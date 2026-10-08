"""Versioned ShiftShield configuration; demo thresholds are not field guidance."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

APP_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONFIG_DIR = Path(__file__).resolve().parent


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


THRESHOLDS = _read_json(CONFIG_DIR / "thresholds.v1.json")
SITE_ADJUSTMENTS = _read_json(CONFIG_DIR / "site_adjustments.v1.json")
DEMO_MODE = os.getenv("SHIFTSHIELD_MODE", "demo") != "field"
AWS_REGION = os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
PUBLIC_ORIGIN = os.getenv("PUBLIC_ORIGIN", "")
DB_PATH = os.getenv("SHIFTSHIELD_DB", "/tmp/shiftshield-local.sqlite3")
