"""Every threshold in the config must equal NIOSH 2016-106 section 8.1 (printed p.93), rounded down."""
from __future__ import annotations

import math

import pytest

from app.config import THRESHOLDS
from app.scheduling import select_band

KCAL_PER_HOUR_TO_W = 1.163
REST_W = 117.0  # NIOSH Table 5-1, printed p.70


def niosh_limit(curve: str, workload_kcal_per_hour: float, work_minutes: int) -> float:
    task_w = workload_kcal_per_hour * KCAL_PER_HOUR_TO_W
    hourly_w = (work_minutes * task_w + (60 - work_minutes) * REST_W) / 60
    if curve == "RAL":
        return 59.9 - 14.1 * math.log10(hourly_w)
    return 56.7 - 11.5 * math.log10(hourly_w)


ROWS = [
    (group_key, group["curve"], class_key, row)
    for group_key, group in THRESHOLDS["curves_by_acclimatization"].items()
    for class_key, row in group["class_rows"].items()
]


@pytest.mark.parametrize("group_key,curve,class_key,row", ROWS, ids=[f"{r[0]}-{r[2]}" for r in ROWS])
def test_config_matches_niosh_equation_rounded_down(group_key, curve, class_key, row) -> None:
    for minutes, value in row["wbgt_c_at_work_minutes_per_hour"].items():
        exact = niosh_limit(curve, row["workload_kcal_per_hour"], int(minutes))
        assert value <= exact + 1e-9, f"{group_key}/{class_key}/{minutes} is less strict than the equation"
        assert exact - value < 0.1, f"{group_key}/{class_key}/{minutes} is off by more than rounding"


def test_unacclimatized_is_never_less_strict_than_acclimatized() -> None:
    groups = THRESHOLDS["curves_by_acclimatization"]
    for class_key, ral_row in groups["unacclimatized"]["class_rows"].items():
        rel_row = groups["acclimatized"]["class_rows"][class_key]
        for minutes, ral in ral_row["wbgt_c_at_work_minutes_per_hour"].items():
            assert ral <= rel_row["wbgt_c_at_work_minutes_per_hour"][minutes]


def test_live_hyderabad_reading_gets_the_stricter_schedule() -> None:
    # 2026-10-08 17:30 IST public check: conservative WBGT 27.5 C, moderate work, unknown acclimatisation.
    # The old chart readings gave 30/30; the equation's 30-minute limit is 26.5 C, so the schedule is 15/45.
    assert select_band(27.5, "moderate", "unknown")["band"] == "very_high"
