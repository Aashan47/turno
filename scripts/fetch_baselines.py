"""Fetch the non-AI baseline forecasts for every site, summer 2026.

Source: Open-Meteo Previous Runs API, which serves archived runs of operational
models at fixed lead days. Two models:

- ecmwf_ifs025: ECMWF IFS at 0.25 degrees, the operational physics model whose
  grid matches Aurora's, so it is the like-for-like baseline;
- italia_meteo_arpae_icon_2i: the 2 km Italian model, the strongest short-range
  baseline available, and the one Turno should expect to lose to at day 1.

Weather data by Open-Meteo.com, CC BY 4.0. The free API is for non-commercial
use, which a hackathon entry is.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from turno.grid import load_lsm, nearest_land_cell  # noqa: E402
from turno.sites import SITES  # noqa: E402

URL = "https://previous-runs-api.open-meteo.com/v1/forecast"
MODELS = ["ecmwf_ifs025", "italia_meteo_arpae_icon_2i"]
VARS = [
    "temperature_2m",
    "dew_point_2m",
    "surface_pressure",
    "wind_speed_10m",
    "shortwave_radiation",
    "direct_radiation",
]
LEAD_DAYS = [1, 2, 3, 4, 5]
START, END = "2026-06-01", "2026-08-31"


def hourly_fields() -> str:
    names = []
    for v in VARS:
        names.append(v)
        names += [f"{v}_previous_day{d}" for d in LEAD_DAYS]
    return ",".join(names)


def main() -> int:
    # Default: grid-cell mean height (elevation=nan), so forecasts and the ERA5
    # truth describe the same place. ERA5 averages a 0.25 degree cell; a forecast
    # downscaled to a coastal town at 50 m against a cell averaging 544 m (Imperia)
    # showed a +1.9 C WBGT bias that was geography, not forecast skill.
    # Pass --site-height for the town-level forecasts the product displays.
    site_height = "--site-height" in sys.argv
    out_dir = ROOT / "data" / ("baselines_site" if site_height else "baselines")
    out_dir.mkdir(parents=True, exist_ok=True)
    lsm = None if site_height else load_lsm(ROOT / "data" / "era5" / "era5_italy_lsm.nc")
    for s in SITES:
        target = out_dir / f"{s.key}.json"
        if target.exists():
            print(f"skip {s.key}")
            continue
        lat, lon = (s.lat, s.lon) if site_height else nearest_land_cell(lsm, s.lat, s.lon)[:2]
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": START,
            "end_date": END,
            "hourly": hourly_fields(),
            "models": ",".join(MODELS),
            "wind_speed_unit": "ms",
            "timezone": "GMT",
        }
        if not site_height:
            params["elevation"] = "nan"
        r = httpx.get(URL, params=params, timeout=120)
        r.raise_for_status()
        data = r.json()
        data["_fetched"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        data["_source"] = "Open-Meteo Previous Runs API, CC BY 4.0"
        target.write_text(json.dumps(data))
        print(f"{s.key}: {len(data['hourly']['time'])} hours")
        time.sleep(2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
