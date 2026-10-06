"""Download ERA5 hourly single-level fields over Italy for summer 2026.

This is the ground truth for the evaluation and for checking the direct-fraction
model. It is ERA5 reanalysis from the Copernicus Climate Data Store, licensed
CC BY 4.0, fetched with the user's own CDS key from ~/.cdsapirc.

One request per month keeps each request well inside the CDS size limits, and a
month already on disk is skipped, so the script can be rerun after a failure.
"""

from __future__ import annotations

import sys
from pathlib import Path

import cdsapi

OUT = Path(__file__).resolve().parent.parent / "data" / "era5"

# North, West, South, East. Mainland Italy, Sicily and Sardinia with a margin.
ITALY_BOX = [47.5, 6.0, 36.0, 19.0]

VARIABLES = [
    "2m_temperature",
    "2m_dewpoint_temperature",
    "surface_pressure",
    "10m_u_component_of_wind",
    "10m_v_component_of_wind",
    "surface_solar_radiation_downwards",
    "total_sky_direct_solar_radiation_at_surface",
    "total_cloud_cover",
    "toa_incident_solar_radiation",
]

MONTHS = {"06": 30, "07": 31, "08": 31}


def fetch(year: str, month: str, days: int, client: cdsapi.Client) -> Path:
    target = OUT / f"era5_italy_{year}{month}.nc"
    if target.exists() and target.stat().st_size > 0:
        print(f"skip {target.name}, already on disk")
        return target
    request = {
        "product_type": ["reanalysis"],
        "variable": VARIABLES,
        "year": [year],
        "month": [month],
        "day": [f"{d:02d}" for d in range(1, days + 1)],
        "time": [f"{h:02d}:00" for h in range(24)],
        "area": ITALY_BOX,
        "data_format": "netcdf",
        "download_format": "unarchived",
    }
    print(f"requesting {target.name}", flush=True)
    client.retrieve("reanalysis-era5-single-levels", request, str(target))
    return target


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    client = cdsapi.Client()
    for month, days in MONTHS.items():
        fetch("2026", month, days, client)
    return 0


if __name__ == "__main__":
    sys.exit(main())
