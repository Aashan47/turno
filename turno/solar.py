"""Sun geometry and the split of sunlight into direct and diffuse.

The Liljegren WBGT needs three solar inputs: downward shortwave at the surface,
the cosine of the solar zenith angle, and the fraction of the shortwave that
arrives as a direct beam. ERA5 provides the first and the third. Aurora 1.5
predicts only the first (`ssrd_1h`). So the other two are computed here, and the
direct fraction is estimated with a published decomposition model whose error
we measure against ERA5 rather than assume. See SOURCES.md.

All radiation in this module is an hourly mean in W m-2, for the hour ending at
the stated time, because that is how ERA5 and Aurora accumulate it.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np

# Sub-steps per hour when averaging the solar zenith angle over an hour.
# 12 five-minute steps keep the error from the sunrise and sunset hours small
# without needing an analytic integral.
SUBSTEPS = 12


def _fractional_year(t: datetime) -> float:
    """NOAA "General Solar Position Calculations": gamma, in radians."""
    year_days = 366 if (t.year % 4 == 0 and (t.year % 100 != 0 or t.year % 400 == 0)) else 365
    day_of_year = t.timetuple().tm_yday
    hour = t.hour + t.minute / 60 + t.second / 3600
    return 2 * np.pi / year_days * (day_of_year - 1 + (hour - 12) / 24)


def _eqtime_minutes(gamma: float) -> float:
    """NOAA equation of time, minutes."""
    return 229.18 * (
        0.000075
        + 0.001868 * np.cos(gamma)
        - 0.032077 * np.sin(gamma)
        - 0.014615 * np.cos(2 * gamma)
        - 0.040849 * np.sin(2 * gamma)
    )


def _declination(gamma: float) -> float:
    """NOAA solar declination, radians."""
    return (
        0.006918
        - 0.399912 * np.cos(gamma)
        + 0.070257 * np.sin(gamma)
        - 0.006758 * np.cos(2 * gamma)
        + 0.000907 * np.sin(2 * gamma)
        - 0.002697 * np.cos(3 * gamma)
        + 0.00148 * np.sin(3 * gamma)
    )


def eccentricity_factor(t: datetime) -> float:
    """(r0/r)^2, the Earth-Sun distance correction to the solar constant.

    The same Fourier form and gamma as the NOAA equations. Its coefficients are
    not on the NOAA page, so this function is checked empirically instead: the
    top-of-atmosphere irradiance it implies is compared against ERA5's own
    `tisr` field in tests and in `scripts/validate_solar.py`.
    """
    g = _fractional_year(t)
    return (
        1.000110
        + 0.034221 * np.cos(g)
        + 0.001280 * np.sin(g)
        + 0.000719 * np.cos(2 * g)
        + 0.000077 * np.sin(2 * g)
    )


def cos_zenith(t_utc: datetime, lat: np.ndarray | float, lon: np.ndarray | float) -> np.ndarray:
    """Instantaneous cosine of the solar zenith angle, clipped at zero.

    NOAA: time_offset = eqtime + 4*longitude (timezone 0, since t is UTC),
    tst = minutes past midnight + time_offset, ha = tst/4 - 180.
    """
    lat_r = np.radians(np.asarray(lat, dtype=float))
    lon_d = np.asarray(lon, dtype=float)
    gamma = _fractional_year(t_utc)
    decl = _declination(gamma)
    minutes = t_utc.hour * 60 + t_utc.minute + t_utc.second / 60
    tst = minutes + _eqtime_minutes(gamma) + 4 * lon_d
    ha = np.radians(tst / 4 - 180)
    c = np.sin(lat_r) * np.sin(decl) + np.cos(lat_r) * np.cos(decl) * np.cos(ha)
    return np.clip(c, 0.0, 1.0)


def cos_zenith_hour_mean(
    t_end_utc: datetime, lat: np.ndarray | float, lon: np.ndarray | float
) -> np.ndarray:
    """Mean of the clipped cosine over the hour ending at t_end_utc."""
    start = t_end_utc - timedelta(hours=1)
    acc = 0.0
    for k in range(SUBSTEPS):
        acc = acc + cos_zenith(start + timedelta(hours=(k + 0.5) / SUBSTEPS), lat, lon)
    return np.asarray(acc / SUBSTEPS)


# Total solar irradiance at 1 AU, W m-2. The value is the commonly used modern
# figure; the code does not rely on its last digit, and the end-to-end check
# against ERA5 `tisr` catches any error in it together with the geometry.
SOLAR_CONSTANT_WM2 = 1361.0


def toa_hour_mean(t_end_utc: datetime, lat, lon) -> np.ndarray:
    """Top-of-atmosphere irradiance on a horizontal surface, hourly mean, W m-2."""
    mid = t_end_utc - timedelta(minutes=30)
    return SOLAR_CONSTANT_WM2 * eccentricity_factor(mid) * cos_zenith_hour_mean(t_end_utc, lat, lon)


def erbs_diffuse_fraction(kt: np.ndarray) -> np.ndarray:
    """Erbs, Klein and Duffie (1982), hourly correlation, Solar Energy 28(4):293-302.

    kd = 1 - 0.09 kt                                              for kt <= 0.22
    kd = 0.9511 - 0.1604 kt + 4.388 kt^2 - 16.638 kt^3 + 12.336 kt^4  for 0.22 < kt <= 0.80
    kd = 0.165                                                    for kt > 0.80
    """
    kt = np.clip(np.asarray(kt, dtype=float), 0.0, 1.0)
    mid = 0.9511 - 0.1604 * kt + 4.388 * kt**2 - 16.638 * kt**3 + 12.336 * kt**4
    return np.where(kt <= 0.22, 1.0 - 0.09 * kt, np.where(kt <= 0.80, mid, 0.165))


def direct_fraction(ssrd_wm2, toa_wm2) -> np.ndarray:
    """Direct-beam fraction of surface shortwave, estimated from the clearness index.

    Zero whenever there is no sunlight to split, so night hours never divide by
    zero and never claim a direct beam.
    """
    ssrd = np.asarray(ssrd_wm2, dtype=float)
    toa = np.asarray(toa_wm2, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        kt = np.where(toa > 1.0, ssrd / toa, 0.0)
    fdir = 1.0 - erbs_diffuse_fraction(kt)
    return np.where((ssrd > 0.0) & (toa > 1.0), np.clip(fdir, 0.0, 1.0), 0.0)
