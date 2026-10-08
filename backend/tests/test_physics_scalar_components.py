"""pywbgt returns some components (the minimum-wind floor) as one scalar, not one value per row."""
from __future__ import annotations

import numpy as np
import pytest
from metpy.units import units

from app import physics


def _fake_pywbgt(**kwargs):
    count = len(kwargs["temp_air"])
    row = lambda value, unit: units.Quantity(np.full(count, value), unit)  # noqa: E731
    return (
        row(45.0, "degC"), None, row(26.0, "degC"), None,
        row(600.0, "W/m^2"), row(1.5, "m/s"),
        units.Quantity(np.float64(0.13), "m/s"),  # scalar, as pywbgt 3.0.7 returns it
    )


def _inputs(count: int) -> dict:
    return dict(
        timestamps=[f"2026-05-04T{hour:02d}:00:00+00:00" for hour in range(count)],
        latitude=17.385, longitude=78.4867,
        air_c=[38.0] * count, dewpoint_c=[18.0] * count, pressure_hpa=[1000.0] * count,
        wind_10m_m_s=[2.0] * count, direct_w_m2=[500.0] * count,
        diffuse_w_m2=[100.0] * count, shortwave_w_m2=[600.0] * count,
        profile={"shade": "none", "surface": "light_concrete"},
    )


def test_scalar_component_is_repeated_for_every_row(monkeypatch):
    monkeypatch.setattr(physics, "pywbgt_estimate", _fake_pywbgt)
    rows = physics.calculate_site_wbgt(**_inputs(5))
    assert len(rows) == 5
    assert all(row["model_min_wind_m_s"] == 0.13 for row in rows)


def test_wrong_length_component_is_rejected(monkeypatch):
    def short(**kwargs):
        out = list(_fake_pywbgt(**kwargs))
        out[5] = units.Quantity(np.array([1.0, 2.0]), "m/s")
        return tuple(out)

    monkeypatch.setattr(physics, "pywbgt_estimate", short)
    with pytest.raises(ValueError):
        physics.calculate_site_wbgt(**_inputs(5))


def test_real_library_handles_a_full_day():
    rows = physics.calculate_site_wbgt(**_inputs(24))
    assert len(rows) == 24
