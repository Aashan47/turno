"""Sun geometry and the direct-diffuse split: geometry, edges and continuity."""

from datetime import datetime, timezone

import numpy as np
import pytest

from turno.solar import (
    cos_zenith,
    cos_zenith_hour_mean,
    direct_fraction,
    eccentricity_factor,
    erbs_diffuse_fraction,
    toa_hour_mean,
)

ROME = (41.9, 12.5)


def _utc(*args):
    return datetime(*args, tzinfo=timezone.utc)


def test_night_is_zero_not_negative():
    assert cos_zenith(_utc(2026, 7, 30, 0, 0), *ROME) == 0.0
    assert cos_zenith_hour_mean(_utc(2026, 7, 30, 1, 0), *ROME) == 0.0


def test_solstice_noon_elevation_matches_latitude_minus_tilt():
    """At the June solstice the noon zenith angle is latitude minus the axial
    tilt, about 41.9 - 23.44 = 18.46 degrees for Rome."""
    best = max(cos_zenith(_utc(2026, 6, 21, 10, m), *ROME) for m in range(0, 60, 1))
    best = max(best, max(cos_zenith(_utc(2026, 6, 21, 11, m), *ROME) for m in range(0, 60, 1)))
    assert float(best) == pytest.approx(np.cos(np.radians(18.46)), abs=0.002)


def test_solar_noon_in_rome_falls_near_eleven_utc_in_summer():
    """Longitude 12.5 E puts local solar noon about 50 minutes before 12:00 UTC,
    shifted a few minutes by the equation of time."""
    minutes = [(h, m) for h in (10, 11, 12) for m in range(60)]
    peak = max(minutes, key=lambda hm: float(cos_zenith(_utc(2026, 7, 30, *hm), *ROME)))
    assert (10, 55) <= peak <= (11, 20)


def test_eccentricity_is_smallest_near_july_aphelion():
    assert eccentricity_factor(_utc(2026, 7, 4, 12)) < 1.0 < eccentricity_factor(_utc(2026, 1, 3, 12))


def test_toa_is_zero_at_night_and_positive_at_noon():
    assert toa_hour_mean(_utc(2026, 7, 30, 1, 0), *ROME) == 0.0
    assert toa_hour_mean(_utc(2026, 7, 30, 12, 0), *ROME) > 1000.0


@pytest.mark.parametrize("edge", [0.22, 0.80])
def test_erbs_is_nearly_continuous_at_its_breakpoints(edge):
    lo = float(erbs_diffuse_fraction(edge - 1e-9))
    hi = float(erbs_diffuse_fraction(edge + 1e-9))
    assert abs(lo - hi) < 0.01


def test_direct_fraction_is_bounded_and_zero_without_sun():
    ssrd = np.array([0.0, 50.0, 400.0, 900.0])
    toa = np.array([0.0, 400.0, 800.0, 1100.0])
    f = direct_fraction(ssrd, toa)
    assert f[0] == 0.0
    assert np.all((f >= 0.0) & (f <= 1.0))
    assert f[3] > f[1], "a clearer sky should give a larger direct share"
