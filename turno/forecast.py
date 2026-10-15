"""Hourly WBGT, one value per ensemble member, for a site's working day.

Source: ECMWF's open-data ensemble on the 0.25 degree grid (scripts/fetch_ecmwf_open.py),
read at the site's ERA5 land cell. ECMWF open data comes every 3 hours, and a
crew is planned hour by hour, so each member's WBGT is computed at the 3-hourly
steps (radiation as the 3-hour mean, as in the evaluation) and interpolated in
time to the hours between. The interpolation is linear and is stated wherever
the plan is shown. The evaluation itself is done at the 3-hourly steps only.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import numpy as np
import xarray as xr

from .solar import cos_zenith_hour_mean, direct_fraction, toa_hour_mean
from .wbgt import WbgtInputs, wbgt_c

WINDOW_H = 3
# Italy in summer is UTC+2 (CEST). Working day 07:00 to 19:00 local.
LOCAL_OFFSET_H = 2
WORK_HOURS_LOCAL = list(range(7, 20))


def _window_mean(fn, t_end: datetime, lat: float, lon: float) -> float:
    return float(np.mean([fn(t_end - timedelta(hours=k), lat, lon) for k in range(WINDOW_H)]))


def member_wbgt_steps(fc: xr.Dataset, lat: float, lon: float) -> dict[datetime, np.ndarray]:
    """WBGT per member at each 3-hourly valid time of one forecast file."""
    init = datetime.fromisoformat(fc.attrs["init"].replace("Z", "+00:00"))
    x = fc.sel(latitude=lat, longitude=lon).load()
    steps = [int(s) for s in x.step.values]
    out: dict[datetime, np.ndarray] = {}
    for k, step in enumerate(steps):
        if step < WINDOW_H:
            continue
        prev = steps.index(step - WINDOW_H) if (step - WINDOW_H) in steps else None
        acc_prev = x["ssrd"].values[prev] if prev is not None else (0.0 if step == WINDOW_H else None)
        if acc_prev is None:
            continue
        sw = np.maximum((x["ssrd"].values[k] - acc_prev) / (WINDOW_H * 3600.0), 0.0)
        t = init + timedelta(hours=step)
        toa = _window_mean(toa_hour_mean, t, lat, lon)
        cz = _window_mean(cos_zenith_hour_mean, t, lat, lon)
        fd = direct_fraction(sw, np.full_like(sw, toa))
        out[t] = np.asarray(wbgt_c(WbgtInputs(x["2t"].values[k], x["2d"].values[k], x["sp"].values[k],
                                              x["10u"].values[k], x["10v"].values[k], sw,
                                              np.full_like(sw, cz), fd)), dtype=float)
    return out


def hourly_members(steps: dict[datetime, np.ndarray], day: date) -> dict[int, np.ndarray]:
    """Members' WBGT for each local working hour of `day`, interpolated linearly in time."""
    times = sorted(steps)
    if not times:
        return {}
    ts = np.array([t.timestamp() for t in times])
    vals = np.stack([steps[t] for t in times])  # (time, member)
    out = {}
    for h in WORK_HOURS_LOCAL:
        t = datetime(day.year, day.month, day.day, h, tzinfo=timezone.utc) - timedelta(hours=LOCAL_OFFSET_H)
        u = t.timestamp()
        if u < ts[0] or u > ts[-1]:
            continue
        out[h] = np.array([np.interp(u, ts, vals[:, m]) for m in range(vals.shape[1])])
    return out
