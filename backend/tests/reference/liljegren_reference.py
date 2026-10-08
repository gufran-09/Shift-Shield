"""WBGT from standard weather data, after Liljegren et al. (2008).

Liljegren JC, Carhart RA, Lawday P, Tschopp S, Sharp R. "Modeling the wet bulb globe
temperature using standard meteorological measurements." J Occup Environ Hyg 5(10):645-655, 2008.

This is the team's own pure-Python implementation of that published model (natural wet-bulb
and black-globe temperatures solved iteratively from heat balances). It has not been
certified. Cross-check it against an established implementation before relying on it
(for example PyWBGT by Kong and Huber, which wraps the original Liljegren C code).
"""
import math

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


def esat_mb(tk: float, pres_mb: float = 1013.25) -> float:
    """Saturation vapour pressure over water (Buck 1981), hPa, with pressure enhancement."""
    y = (tk - 273.15) / (tk - 32.18)
    return (1.0007 + 3.46e-6 * pres_mb) * 6.1121 * math.exp(17.502 * y)


def dew_point_k(e_mb: float, pres_mb: float = 1013.25) -> float:
    z = math.log(e_mb / (6.1121 * (1.0007 + 3.46e-6 * pres_mb)))
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


def _clean_solar(solar: float, fdir: float, cza: float):
    if cza <= 0.0 or solar <= 0.0:
        return 0.0, 0.0, max(cza, 0.0)
    solar = min(solar, 1367.0 * cza)          # cannot exceed top-of-atmosphere value
    if cza < math.cos(math.radians(89.5)):    # sun on the horizon: treat as diffuse
        fdir = 0.0
    return solar, min(max(fdir, 0.0), 0.9), cza


def globe_temp_c(ta_c, rh, pres_mb, speed, solar, fdir, cza, alb_sfc=DEFAULT_ALB_SFC):
    """Black-globe temperature (C). rh is a fraction 0..1, speed in m/s at about 2 m."""
    solar, fdir, cza = _clean_solar(solar, fdir, cza)
    tair = ta_c + 273.15
    tsfc = tair
    prev = tair
    for _ in range(MAX_ITER):
        tref = 0.5 * (prev + tair)
        h = h_sphere(D_GLOBE, tref, pres_mb, speed)
        rad = 0.0
        if solar > 0:
            rad = solar / (2 * STEFANB * EMIS_GLOBE) * (1 - ALB_GLOBE) * (fdir * (1 / (2 * cza) - 1) + 1 + alb_sfc)
        new = (0.5 * (emis_atm(tair, rh, pres_mb) * tair ** 4 + EMIS_SFC * tsfc ** 4)
               - h / (STEFANB * EMIS_GLOBE) * (prev - tair) + rad) ** 0.25
        if abs(new - prev) < CONVERGENCE:
            return new - 273.15
        prev = 0.9 * prev + 0.1 * new
    raise RuntimeError("globe temperature did not converge")


def natural_wet_bulb_c(ta_c, rh, pres_mb, speed, solar, fdir, cza, alb_sfc=DEFAULT_ALB_SFC):
    """Natural (unventilated, sun-exposed) wet-bulb temperature (C)."""
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
        new = tair - evap_heat(tref) / RATIO * (ewick - eair) / (pres_mb - ewick) * (PR / sc) ** 0.56 + fatm / h
        if abs(new - prev) < CONVERGENCE:
            return new - 273.15
        prev = 0.9 * prev + 0.1 * new
    raise RuntimeError("wet-bulb temperature did not converge")


def wbgt_outdoor_c(ta_c, rh_pct, pres_mb, speed_2m, solar, fdir, cza, alb_sfc=DEFAULT_ALB_SFC):
    """Outdoor WBGT = 0.7 Tnwb + 0.2 Tg + 0.1 Ta. rh_pct in percent. Returns (wbgt, tnwb, tg)."""
    rh = max(min(rh_pct / 100.0, 1.0), 0.01)
    tg = globe_temp_c(ta_c, rh, pres_mb, speed_2m, solar, fdir, cza, alb_sfc)
    tnwb = natural_wet_bulb_c(ta_c, rh, pres_mb, speed_2m, solar, fdir, cza, alb_sfc)
    return 0.7 * tnwb + 0.2 * tg + 0.1 * ta_c, tnwb, tg
