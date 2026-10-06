"""Write the global ERA5 states Aurora 1.5 starts from, for the pre-registered dates.

Source: Google's public ARCO-ERA5 store (gs://gcp-public-data-arco-era5), read
anonymously. Its metadata on 2026-10-06 gave final ERA5 to 2026-06-30 and the
preliminary ERA5T to 2026-09-30, so every pre-registered date is covered (July
and August from ERA5T, which the output records). A value checked against the
Copernicus download matched exactly (Roma cell, 2026-07-30 12Z, 37.84 C).

Aurora takes two input times, init minus 6 hours and init. Each date writes one
NetCDF of about 0.7 GB: 18 surface variables and 5 atmospheric variables on 13
pressure levels, on the full 0.25 degree global grid. Run on the droplet, where
the bandwidth is.

This script only reads and writes data. Building Aurora's Batch from it is done
in the event window.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import xarray as xr

ROOT = Path(__file__).resolve().parent.parent
STORE = "gs://gcp-public-data-arco-era5/ar/full_37-1h-0p25deg-chunk-1.zarr-v3"

DATES = [
    "2026-06-03", "2026-06-10", "2026-06-17", "2026-06-24", "2026-07-01", "2026-07-08", "2026-07-15",
    "2026-07-22", "2026-07-29", "2026-07-30", "2026-08-05", "2026-08-12", "2026-08-19", "2026-08-26",
]
LEVELS = [50, 100, 150, 200, 250, 300, 400, 500, 600, 700, 850, 925, 1000]

SURFACE = {
    "2t": "2m_temperature", "10u": "10m_u_component_of_wind", "10v": "10m_v_component_of_wind",
    "msl": "mean_sea_level_pressure", "2d": "2m_dewpoint_temperature", "tcwv": "total_column_water_vapour",
    "tcc": "total_cloud_cover", "100u": "100m_u_component_of_wind", "100v": "100m_v_component_of_wind",
    "sp": "surface_pressure", "lcc": "low_cloud_cover", "mcc": "medium_cloud_cover", "hcc": "high_cloud_cover",
    "skt": "skin_temperature", "stl1": "soil_temperature_level_1", "swvl1": "volumetric_soil_water_layer_1",
    "ci": "sea_ice_cover", "sd": "snow_depth",
}
ATMOS = {"z": "geopotential", "u": "u_component_of_wind", "v": "v_component_of_wind", "t": "temperature",
         "q": "specific_humidity"}


def main(dates: list[str]) -> int:
    out_dir = ROOT / "data" / "init"
    out_dir.mkdir(parents=True, exist_ok=True)
    ds = xr.open_zarr(STORE, chunks=None, storage_options={"token": "anon"})
    final_end = pd.Timestamp(ds.attrs.get("valid_time_stop", "1900-01-01"))
    for d in dates:
        target = out_dir / f"era5_init_{d.replace('-', '')}00.nc"
        if target.exists():
            print(f"skip {target.name}")
            continue
        init = pd.Timestamp(f"{d}T00:00")
        times = [init - pd.Timedelta(hours=6), init]
        surf = ds[list(SURFACE.values())].sel(time=times).rename({v: k for k, v in SURFACE.items()})
        atmos = ds[list(ATMOS.values())].sel(time=times, level=LEVELS).rename({v: k for k, v in ATMOS.items()})
        out = xr.merge([surf, atmos]).load()
        out.attrs.update({
            "source": f"{STORE}, read anonymously",
            "init": f"{d}T00:00Z",
            "era5_kind": "ERA5 final" if init <= final_end else "ERA5T preliminary",
        })
        out.to_netcdf(target)
        print(f"wrote {target.name} ({out.attrs['era5_kind']}, {target.stat().st_size / 1e9:.2f} GB)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or DATES))
