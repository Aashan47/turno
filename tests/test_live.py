"""Live forecast parsing: Rome local hours, member count, missing values. No network."""

from datetime import date

from turno.live import members_for_day
from turno.rules import ENSEMBLE_MEMBERS


def _payload(n_members=ENSEMBLE_MEMBERS, drop=None):
    times = [f"2026-10-16T{h:02d}:00" for h in range(24)]
    h = {"time": times}
    for m in range(1, n_members + 1):
        for v, val in [("temperature_2m", 24.0), ("dew_point_2m", 14.0), ("surface_pressure", 1012.0),
                       ("wind_speed_10m", 2.0), ("shortwave_radiation", 500.0), ("direct_radiation", 350.0)]:
            series = [val] * 24
            if drop == (v, m):
                series[10] = None
            h[f"{v}_member{m:02d}"] = series
    return {"hourly": h}


def test_rome_local_hours_map_to_utc_in_summer_time():
    """16 Oct 2026 is CEST (UTC+2): local 07:00 is 05:00 UTC, local 19:00 is 17:00 UTC."""
    out = members_for_day(_payload(), 42.0, 12.5, date(2026, 10, 16))
    assert min(out) == 7 and max(out) == 19
    assert all(len(v) == ENSEMBLE_MEMBERS for v in out.values())


def test_an_hour_with_a_missing_member_is_dropped_not_padded():
    out = members_for_day(_payload(drop=("temperature_2m", 3)), 42.0, 12.5, date(2026, 10, 16))
    assert 12 not in out  # 10:00 UTC is 12:00 local
    assert 11 in out and 13 in out
