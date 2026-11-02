"""Download ERA5 hourly single-level fields over Pakistan for May to August 2026.

The truth for results/pk/PREREGISTRATION-PK.md. Same variables, source, licence
(CC BY 4.0) and method as fetch_era5_italy.py; only the box and months differ.
Also fetches the land-sea mask, which picks each site's cell. A file already on
disk is skipped, so the script can be rerun after a failure.
"""

from __future__ import annotations

import sys
from pathlib import Path

import cdsapi

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_era5_italy import OUT, VARIABLES, merge_if_zip  # noqa: E402

# North, West, South, East. Karachi to Lahore with a margin; the same box as fetch_ecmwf_open.py --region pk.
PK_BOX = [32.5, 66.0, 23.5, 75.5]

MONTHS = {"05": 31, "06": 30, "07": 31, "08": 31}


def retrieve(request: dict, target: Path, client: cdsapi.Client) -> None:
    if target.exists() and target.stat().st_size > 0:
        print(f"skip {target.name}, already on disk")
        return
    print(f"requesting {target.name}", flush=True)
    client.retrieve("reanalysis-era5-single-levels", request, str(target))
    merge_if_zip(target)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    client = cdsapi.Client()
    retrieve({
        "product_type": ["reanalysis"], "variable": ["land_sea_mask"],
        "year": ["2026"], "month": ["05"], "day": ["01"], "time": ["00:00"],
        "area": PK_BOX, "data_format": "netcdf", "download_format": "unarchived",
    }, OUT / "era5_pk_lsm.nc", client)
    for month, days in MONTHS.items():
        retrieve({
            "product_type": ["reanalysis"], "variable": VARIABLES,
            "year": ["2026"], "month": [month],
            "day": [f"{d:02d}" for d in range(1, days + 1)],
            "time": [f"{h:02d}:00" for h in range(24)],
            "area": PK_BOX, "data_format": "netcdf", "download_format": "unarchived",
        }, OUT / f"era5_pk_2026{month}.nc", client)
    return 0


if __name__ == "__main__":
    sys.exit(main())
