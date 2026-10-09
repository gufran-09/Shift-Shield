"""Pure-Python Liljegren implementation for platforms where C-extensions are unavailable."""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Tuple

STEFANB = 5.6696e-8
CP = 1003.5
M_AIR = 28.97
M_H2O = 18.015
RATIO = CP * M_AIR / M_H2O
R_GAS = 8314.34
R_AIR = R_GAS / M_AIR
PR = CP / (CP + 1.25 * R_AIR)

EMIS_WICK, ALB_WICK, D_WICK, L_WICK = 0.95, 0.4, 0.007, 0.0254
EMIS_GLOBE, ALB_GLOBE, D_GLOBE = 0.95, 0.05, 0.0508
EMIS_SFC = 0.999
DEFAULT_ALB_SFC = 0.45
MIN_SPEED = 0.13          # m/s, lower bound used by Liljegren
CONVERGENCE = 0.02        # K
MAX_ITER = 200


def cos_zenith(when_utc: datetime, lat_deg: float, lon_deg: float) -> float:
    """Cosine of the solar zenith angle at a UTC time and place. 0 or below means sun is down."""
    if when_utc.tzinfo is None:
        when_utc = when_utc.replace(tzinfo=timezone.utc)
    when_utc = when_utc.astimezone(timezone.utc)
    doy = when_utc.timetuple().tm_yday
    hour = when_utc.hour + when_utc.minute / 60 + when_utc.second / 3600
    g = 2 * math.pi / 365 * (doy - 1 + (hour - 12) / 24)
    eqtime = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g)
                       - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g))
    decl = (0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g) - 0.006758 * math.cos(2 * g)
            + 0.000907 * math.sin(2 * g) - 0.002697 * math.cos(3 * g) + 0.00148 * math.sin(3 * g))
    true_solar_min = hour * 60 + eqtime + 4 * lon_deg
    ha = math.radians(true_solar_min / 4 - 180)
    lat = math.radians(lat_deg)
    return math.sin(lat) * math.sin(decl) + math.cos(lat) * math.cos(decl) * math.cos(ha)


def esat_mb(tk: float, pres_mb: float = 1013.25) -> float:
    y = (tk - 273.15) / (tk - 32.18)
    return (1.0007 + 3.46e-6 * pres_mb) * 6.1121 * math.exp(17.502 * y)


def dew_point_k(e_mb: float, pres_mb: float = 1013.25) -> float:
    z = math.log(max(e_mb, 1e-4) / (6.1121 * (1.0007 + 3.46e-6 * pres_mb)))
    return 273.15 + 240.97 * z / (17.502 - z)


def emis_atm(tk: float, rh: float, pres_mb: float) -> float:
    return 0.575 * (rh * esat_mb(tk, pres_mb)) ** 0.143


def viscosity(tk: float) -> float:
    omega = (tk / 97 - 2.9) / 0.4 * (-0.034) + 1.048
    return 0.0000026693 * (M_AIR * tk) ** 0.5 / (3.617 ** 2 * omega)


def thermal_cond(tk: float) -> float:
    return (CP + 1.25 * R_AIR) * viscosity(tk)


def diffusivity(tk: float, pres_mb: float) -> float:
    pcrit13 = (36.4 * 218) ** (1 / 3)
    tcrit512 = (132 * 647.3) ** (5 / 12)
    tcrit12 = (132 * 647.3) ** 0.5
    mmix = (1 / M_AIR + 1 / M_H2O) ** 0.5
    return 0.000364 * (tk / tcrit12) ** 2.334 * pcrit13 * tcrit512 * mmix / (pres_mb / 1013.25) * 0.0001


def evap_heat(tk: float) -> float:
    return (313.15 - tk) / 30 * (-71100) + 2.4073e6


def h_sphere(diam: float, tk: float, pres_mb: float, speed: float) -> float:
    density = pres_mb * 100 / (R_AIR * tk)
    re = max(speed, MIN_SPEED) * density * diam / viscosity(tk)
    nu = 2 + 0.6 * re ** 0.5 * PR ** 0.3333
    return nu * thermal_cond(tk) / diam


def h_cylinder(diam: float, tk: float, pres_mb: float, speed: float) -> float:
    density = pres_mb * 100 / (R_AIR * tk)
    re = max(speed, MIN_SPEED) * density * diam / viscosity(tk)
    nu = 0.281 * re ** 0.6 * PR ** 0.44
    return nu * thermal_cond(tk) / diam


def _clean_solar(solar: float, fdir: float, cza: float) -> Tuple[float, float, float]:
    if cza <= 0.0 or solar <= 0.0:
        return 0.0, 0.0, max(cza, 0.0)
    solar = min(solar, 1367.0 * cza)
    if cza < math.cos(math.radians(89.5)):
        fdir = 0.0
    return solar, min(max(fdir, 0.0), 0.9), cza


def globe_temp_c(ta_c: float, rh: float, pres_mb: float, speed: float, solar: float, fdir: float, cza: float, alb_sfc: float = DEFAULT_ALB_SFC) -> float:
    solar, fdir, cza = _clean_solar(solar, fdir, cza)
    tair = ta_c + 273.15
    tsfc = tair
    prev = tair
    for _ in range(MAX_ITER):
        tref = 0.5 * (prev + tair)
        h = h_sphere(D_GLOBE, tref, pres_mb, speed)
        rad = 0.0
        if solar > 0:
            rad = solar / (2 * STEFANB * EMIS_GLOBE) * (1 - ALB_GLOBE) * (fdir * (1 / (2 * max(cza, 0.01)) - 1) + 1 + alb_sfc)
        new = (0.5 * (emis_atm(tair, rh, pres_mb) * tair ** 4 + EMIS_SFC * tsfc ** 4)
               - h / (STEFANB * EMIS_GLOBE) * (prev - tair) + rad) ** 0.25
        if abs(new - prev) < CONVERGENCE:
            return new - 273.15
        prev = 0.9 * prev + 0.1 * new
    return prev - 273.15


def natural_wet_bulb_c(ta_c: float, rh: float, pres_mb: float, speed: float, solar: float, fdir: float, cza: float, alb_sfc: float = DEFAULT_ALB_SFC) -> float:
    solar, fdir, cza = _clean_solar(solar, fdir, cza)
    tair = ta_c + 273.15
    tsfc = tair
    eair = rh * esat_mb(tair, pres_mb)
    prev = dew_point_k(eair, pres_mb)
    sza = math.acos(min(max(cza, 0.0), 1.0)) if solar > 0 else math.pi / 2
    for _ in range(MAX_ITER):
        tref = 0.5 * (prev + tair)
        h = h_cylinder(D_WICK, tref, pres_mb, speed)
        fatm = STEFANB * EMIS_WICK * (0.5 * (emis_atm(tair, rh, pres_mb) * tair ** 4 + EMIS_SFC * tsfc ** 4) - prev ** 4)
        if solar > 0:
            fatm += (1 - ALB_WICK) * solar * ((1 - fdir) * (1 + 0.25 * D_WICK / L_WICK)
                                              + fdir * ((math.tan(sza) / math.pi) + 0.25 * D_WICK / L_WICK) + alb_sfc)
        ewick = esat_mb(prev, pres_mb)
        density = pres_mb * 100 / (R_AIR * tref)
        sc = viscosity(tref) / (density * diffusivity(tref, pres_mb))
        new = tair - evap_heat(tref) / RATIO * (ewick - eair) / max(pres_mb - ewick, 1.0) * (PR / sc) ** 0.56 + fatm / h
        if abs(new - prev) < CONVERGENCE:
            return new - 273.15
        prev = 0.9 * prev + 0.1 * new
    return prev - 273.15


def wbgt_outdoor_c(ta_c: float, rh_pct: float, pres_mb: float, speed_2m: float, solar: float, fdir: float, cza: float, alb_sfc: float = DEFAULT_ALB_SFC) -> Tuple[float, float, float]:
    rh = max(min(rh_pct / 100.0, 1.0), 0.01)
    tg = globe_temp_c(ta_c, rh, pres_mb, speed_2m, solar, fdir, cza, alb_sfc)
    tnwb = natural_wet_bulb_c(ta_c, rh, pres_mb, speed_2m, solar, fdir, cza, alb_sfc)
    return 0.7 * tnwb + 0.2 * tg + 0.1 * ta_c, tnwb, tg
