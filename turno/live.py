"""Tomorrow's plan from the latest ECMWF ensemble run, for the live app.

The replay days use ECMWF open-data GRIB files, which this small server cannot
process. For live use the same ECMWF IFS 0.25 degree ensemble is read from
Open-Meteo's ensemble API, hourly, at the site's ERA5 cell and the cell's mean
height (elevation=nan), so it is the same forecast at the same place. The first
ENSEMBLE_MEMBERS perturbed members are used, the same count the rules were
frozen with. Weather data by Open-Meteo.com (CC BY 4.0).

Local time is Europe/Rome, so the plan follows Italy's clock change.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import httpx
import numpy as np

from .day_plan import plan_day
from .ordinances import Ordinance
from .rules import ENSEMBLE_MEMBERS
from .solar import cos_zenith_hour_mean
from .wbgt import WbgtInputs, wbgt_c

ROME = ZoneInfo("Europe/Rome")
URL = "https://ensemble-api.open-meteo.com/v1/ensemble"
VARS = ["temperature_2m", "dew_point_2m", "surface_pressure", "wind_speed_10m", "shortwave_radiation", "direct_radiation"]
WORK_HOURS = range(7, 20)


def fetch(lat: float, lon: float) -> dict:
    r = httpx.get(URL, params={"latitude": lat, "longitude": lon, "hourly": ",".join(VARS),
                               "models": "ecmwf_ifs025", "forecast_days": 3, "wind_speed_unit": "ms",
                               "timezone": "GMT", "elevation": "nan"}, timeout=60)
    r.raise_for_status()
    return r.json()


def members_for_day(data: dict, lat: float, lon: float, day: date) -> dict[int, list[float]]:
    h = data["hourly"]
    times = [datetime.fromisoformat(t).replace(tzinfo=timezone.utc) for t in h["time"]]
    idx = {t: i for i, t in enumerate(times)}
    out: dict[int, list[float]] = {}
    for hour in WORK_HOURS:
        t = datetime(day.year, day.month, day.day, hour, tzinfo=ROME).astimezone(timezone.utc)
        i = idx.get(t)
        if i is None:
            continue
        cz = float(cos_zenith_hour_mean(t, lat, lon))
        vals = []
        for m in range(1, ENSEMBLE_MEMBERS + 1):
            k = f"_member{m:02d}"
            g = lambda v: h.get(v + k, [None] * len(times))[i]  # noqa: E731
            t2, td, sp, ws, sw, dr = (g(v) for v in VARS)
            if None in (t2, td, sp, ws, sw, dr):
                continue
            fd = dr / sw if sw > 1.0 else 0.0
            vals.append(round(float(wbgt_c(WbgtInputs(np.array([t2 + 273.15]), np.array([td + 273.15]),
                                                      np.array([sp * 100.0]), np.array([ws]), np.array([0.0]),
                                                      np.array([sw]), np.array([cz]),
                                                      np.array([min(max(fd, 0.0), 1.0)])))[0]), 2))
        if len(vals) == ENSEMBLE_MEMBERS:
            out[hour] = vals
    return out


def tomorrow_doc(site: dict, ordinances: dict[str, list[Ordinance]]) -> dict:
    """The same document shape as a replay day, without the truth (it has not happened yet)."""
    lat, lon = site["cell"]["lat"], site["cell"]["lon"]
    data = fetch(lat, lon)
    day = (datetime.now(ROME) + timedelta(days=1)).date()
    members = members_for_day(data, lat, lon, day)
    plans = {}
    for wl in ("moderate", "heavy", "very_heavy"):
        for accl in (False, True):
            for akey, aval in {"unconfirmed": None, "alto": True, "not_alto": False}.items():
                plans[f"{wl}|{'accl' if accl else 'unaccl'}|{akey}"] = plan_day(
                    ordinances, site["region"], day, members, wl, accl, aval)
    return {**{k: site[k] for k in ("site", "name", "region", "work", "cell", "ordinances")},
            "date": day.isoformat(), "live": True,
            "forecast_init": f"latest ECMWF ensemble run via Open-Meteo, fetched {datetime.now(timezone.utc):%Y-%m-%d %H:%MZ}",
            "lead_days": 1, "members_by_hour": {str(k): v for k, v in members.items()},
            "truth_wbgt_by_hour": {}, "truth_minutes": {}, "plans": plans,
            "interpolation": "Hourly forecast values, no interpolation."}
