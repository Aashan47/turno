"""Measure the two solar approximations against ERA5, before any model is involved.

Aurora predicts surface shortwave but not its direct fraction, so Turno estimates
the fraction with the Erbs correlation and computes top-of-atmosphere irradiance
itself. This script measures what those two choices cost, on real Italian
summer hours, by comparing them with ERA5's own fields:

1. our top-of-atmosphere irradiance against ERA5 `tisr`;
2. the Erbs direct fraction against ERA5 `fdir / ssrd`;
3. WBGT computed with the Erbs fraction against WBGT computed with ERA5's.

Output: results/solar-validation.md, with the date it was run.
"""

from __future__ import annotations

import sys
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import xarray as xr

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from turno.grid import load_lsm, nearest_land_cell  # noqa: E402
from turno.sites import SITES  # noqa: E402
from turno.solar import cos_zenith_hour_mean, direct_fraction, toa_hour_mean  # noqa: E402
from turno.wbgt import WbgtInputs, wbgt_c  # noqa: E402


def load() -> xr.Dataset:
    files = sorted((ROOT / "data" / "era5").glob("era5_italy_2026*.nc"))
    if not files:
        raise SystemExit("no ERA5 files yet in data/era5")
    ds = xr.open_mfdataset(files, combine="by_coords")
    if "valid_time" in ds.dims:
        ds = ds.rename({"valid_time": "time"})
    return ds


def site_series(ds: xr.Dataset, lat: float, lon: float) -> xr.Dataset:
    return ds.sel(latitude=lat, longitude=lon, method="nearest").load()


def main() -> int:
    ds = load()
    lines = [
        "# Solar approximations against ERA5",
        "",
        f"Run {date.today().isoformat()} on ERA5 hourly fields, "
        f"{str(ds.time.values[0])[:10]} to {str(ds.time.values[-1])[:10]}, nearest mostly-land grid cell to each site.",
        "",
        "| Site | Daylight hours | TOA error vs `tisr`, mean abs % | fdir, Erbs minus ERA5, mean abs | WBGT, Erbs minus ERA5 fdir, mean abs C | worst C |",
        "|---|---|---|---|---|---|",
    ]
    lsm = load_lsm(ROOT / "data" / "era5" / "era5_italy_lsm.nc")
    for s in SITES:
        x = site_series(ds, *nearest_land_cell(lsm, s.lat, s.lon)[:2])
        times = [datetime.fromtimestamp(int(t) / 1e9, tz=timezone.utc) for t in x.time.values.astype("int64")]
        lat, lon = float(x.latitude), float(x.longitude)
        ssrd = x["ssrd"].values / 3600.0
        tisr = x["tisr"].values / 3600.0
        fdir_era = np.where(ssrd > 1.0, (x["fdir"].values / 3600.0) / np.maximum(ssrd, 1e-9), 0.0)
        toa = np.array([float(toa_hour_mean(t, lat, lon)) for t in times])
        cz = np.array([float(cos_zenith_hour_mean(t, lat, lon)) for t in times])
        fdir_erbs = direct_fraction(ssrd, toa)

        day = (tisr > 50.0) & (ssrd > 20.0)
        toa_err = np.mean(np.abs(toa[day] - tisr[day]) / tisr[day]) * 100

        def w(fd):
            return wbgt_c(WbgtInputs(x["t2m"].values, x["d2m"].values, x["sp"].values,
                                     x["u10"].values, x["v10"].values, ssrd, cz, fd))

        dw = (w(fdir_erbs) - w(np.clip(fdir_era, 0, 1)))[day]
        lines.append(
            f"| {s.name} | {int(day.sum())} | {toa_err:.2f} | "
            f"{np.mean(np.abs(fdir_erbs[day] - fdir_era[day])):.3f} | {np.mean(np.abs(dw)):.2f} | {np.max(np.abs(dw)):.2f} |"
        )
    out = ROOT / "results" / "solar-validation.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
