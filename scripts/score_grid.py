"""Score gridded forecast arms (ECMWF IFS, ECMWF ENS, Aurora) against ERA5.

Every arm arrives in one layout: a NetCDF with dims (step, member, latitude,
longitude), steps in hours from a 00 UTC init, variables 2t, 2d, 10u, 10v, sp
(instantaneous at the step) and ssrd (accumulated J m-2 since step 0). Aurora's
output is written in this layout too, so all arms meet the same code.

All arms are scored at 3-hourly valid times, because that is ECMWF open data's
resolution. Radiation is the mean over the 3 hours ending at the valid time,
for the forecasts and for the ERA5 truth alike, so Aurora's finer hourly output
gives it no advantage. The direct fraction comes from the Erbs split for every
forecast arm; the truth uses ERA5's own.

Usage: score_grid.py data/ecmwf/oper_2026073000.nc [more files ...]
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import xarray as xr

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from turno.evaluate import decision_score, wbgt_score  # noqa: E402
from turno.grid import load_lsm, nearest_land_cell  # noqa: E402
from turno.sites import SITES  # noqa: E402
from turno.solar import cos_zenith_hour_mean, direct_fraction, toa_hour_mean  # noqa: E402
from turno.wbgt import WbgtInputs, wbgt_c  # noqa: E402

WINDOW_H = 3


def mean_over_window(fn, t_end: datetime, lat: float, lon: float) -> float:
    """Mean of an hourly-mean solar quantity over the WINDOW_H hours ending at t_end."""
    return float(np.mean([fn(t_end - timedelta(hours=k), lat, lon) for k in range(WINDOW_H)]))


def era5_truth(ds: xr.Dataset, lat: float, lon: float) -> dict[datetime, float]:
    """ERA5 WBGT at every hour, with radiation averaged over the trailing 3 hours."""
    x = ds.sel(latitude=lat, longitude=lon).load()
    times = [datetime.fromtimestamp(int(t) / 1e9, tz=timezone.utc) for t in x.time.values.astype("int64")]
    ssrd_h = x["ssrd"].values / 3600.0
    fdir_h = x["fdir"].values / 3600.0
    out = {}
    for i in range(WINDOW_H - 1, len(times)):
        t = times[i]
        sw = float(np.mean(ssrd_h[i - WINDOW_H + 1 : i + 1]))
        dr = float(np.mean(fdir_h[i - WINDOW_H + 1 : i + 1]))
        fd = dr / sw if sw > 1.0 else 0.0
        cz = mean_over_window(cos_zenith_hour_mean, t, lat, lon)
        w = wbgt_c(WbgtInputs(np.array([x["t2m"].values[i]]), np.array([x["d2m"].values[i]]),
                              np.array([x["sp"].values[i]]), np.array([x["u10"].values[i]]),
                              np.array([x["v10"].values[i]]), np.array([sw]), np.array([cz]),
                              np.array([min(max(fd, 0.0), 1.0)])))
        out[t] = float(w[0])
    return out


def arm_members(fc: xr.Dataset, init: datetime, lat: float, lon: float) -> dict[datetime, np.ndarray]:
    """WBGT per member at each valid time, from one forecast file."""
    x = fc.sel(latitude=lat, longitude=lon).load()
    steps = [int(s) for s in x.step.values]
    out = {}
    for k, step in enumerate(steps):
        if step < WINDOW_H:
            continue
        prev = steps.index(step - WINDOW_H) if (step - WINDOW_H) in steps else None
        acc_now = x["ssrd"].values[k]
        acc_prev = x["ssrd"].values[prev] if prev is not None else (0.0 if step == WINDOW_H else None)
        if acc_prev is None:
            continue
        sw = np.maximum((acc_now - acc_prev) / (WINDOW_H * 3600.0), 0.0)
        t = init + timedelta(hours=step)
        toa = mean_over_window(toa_hour_mean, t, lat, lon)
        cz = mean_over_window(cos_zenith_hour_mean, t, lat, lon)
        fd = direct_fraction(sw, np.full_like(sw, toa))
        w = wbgt_c(WbgtInputs(x["2t"].values[k], x["2d"].values[k], x["sp"].values[k], x["10u"].values[k],
                              x["10v"].values[k], sw, np.full_like(sw, cz), fd))
        out[t] = np.asarray(w, dtype=float)
    return out


def main(paths: list[str]) -> int:
    era = sorted((ROOT / "data" / "era5").glob("era5_italy_2026*.nc"))
    ds = xr.open_mfdataset(era, combine="by_coords")
    if "valid_time" in ds.dims:
        ds = ds.rename({"valid_time": "time"})
    lsm = load_lsm(ROOT / "data" / "era5" / "era5_italy_lsm.nc")
    cells = {s.key: nearest_land_cell(lsm, s.lat, s.lon)[:2] for s in SITES}
    truth = {k: era5_truth(ds, *c) for k, c in cells.items()}

    rows = []
    for p in paths:
        fc = xr.open_dataset(p)
        init = datetime.fromisoformat(fc.attrs["init"].replace("Z", "+00:00"))
        arm = fc.attrs.get("arm", fc.attrs.get("stream"))
        for key, (lat, lon) in cells.items():
            members = arm_members(fc, init, lat, lon)
            for lead in range(1, 6):
                lo, hi = init + timedelta(days=lead - 1), init + timedelta(days=lead)
                ts = [t for t in sorted(members) if lo < t <= hi and t in truth[key]]
                if not ts:
                    continue
                med = [float(np.median(members[t])) for t in ts]
                tr = [truth[key][t] for t in ts]
                for accl in (True, False):
                    d = decision_score([members[t] for t in ts], tr, "heavy", accl)
                    w = wbgt_score(med, tr)
                    rows.append({"file": Path(p).name, "arm": arm, "init": init.date().isoformat(),
                                 "site": key, "lead_days": lead, "acclimatized": accl, "n": w.n,
                                 "mae_c": w.mae_c, "bias_c": w.bias_c,
                                 "restricted": d.restricted_truth, "missed": d.missed,
                                 "false_restrictions": d.false_restrictions,
                                 "handed_over": d.handed_to_supervisor, "hours": d.hours})
    out = ROOT / "results" / "grid_scores.jsonl"
    with out.open("a") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(f"{len(rows)} rows appended to {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
