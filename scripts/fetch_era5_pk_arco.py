"""Download the ERA5 truth over Pakistan, May to August 2026, from Google's ARCO-ERA5 copy.

Amendment 1 of results/pk/PREREGISTRATION-PK.md: the Copernicus queue stalled, and
ARCO-ERA5 holds the same ECMWF fields (checked against the Copernicus Italy files).
Its chunks are one whole-globe field per hour, so only what the truth reads is
fetched: hours 01 to 12 UTC of seven fields, which hold every scored time (03, 06,
09, 12 UTC) and its 3-hour radiation window. Writes data/era5/era5_pk_arco_2026MM.nc
with the Copernicus variable names. A month already on disk is skipped.
"""

from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import xarray as xr

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_era5_pakistan import PK_BOX  # noqa: E402
from fetch_era5_italy import OUT  # noqa: E402

ARCO = "gs://gcp-public-data-arco-era5/ar/full_37-1h-0p25deg-chunk-1.zarr-v3"

# ARCO name -> the Copernicus NetCDF name the scorer reads.
FIELDS = {
    "2m_temperature": "t2m",
    "2m_dewpoint_temperature": "d2m",
    "surface_pressure": "sp",
    "10m_u_component_of_wind": "u10",
    "10m_v_component_of_wind": "v10",
    "surface_solar_radiation_downwards": "ssrd",
    "total_sky_direct_solar_radiation_at_surface": "fdir",
}

MONTHS = ("05", "06", "07", "08")
HOURS_UTC = range(1, 13)


def fetch_month(ds: xr.Dataset, month: str, target: Path) -> None:
    if target.exists() and target.stat().st_size > 0:
        print(f"skip {target.name}, already on disk")
        return
    north, west, south, east = PK_BOX
    days = pd.date_range(f"2026-{month}-01", periods=pd.Period(f"2026-{month}").days_in_month, freq="D")
    times = pd.DatetimeIndex([d + pd.Timedelta(hours=h) for d in days for h in HOURS_UTC])

    def one(arco_name: str) -> xr.DataArray:
        x = ds[arco_name].sel(time=times, latitude=slice(north, south), longitude=slice(west, east)).load()
        print(f"  {month} {FIELDS[arco_name]} done", flush=True)
        return x.rename(FIELDS[arco_name])

    with ThreadPoolExecutor(max_workers=len(FIELDS)) as pool:
        arrays = list(pool.map(one, FIELDS))
    out = xr.merge(arrays).rename({"time": "valid_time"})
    out.attrs.update(source=ARCO, note="hours 01-12 UTC only; PREREGISTRATION-PK.md amendment 1")
    tmp = target.with_suffix(".part.nc")
    out.to_netcdf(tmp)
    tmp.rename(target)
    print(f"wrote {target.name}", flush=True)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    ds = xr.open_zarr(ARCO, chunks=None, storage_options={"token": "anon"})
    for month in MONTHS:
        fetch_month(ds, month, OUT / f"era5_pk_arco_2026{month}.nc")
    return 0


if __name__ == "__main__":
    sys.exit(main())
