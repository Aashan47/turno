"""Score the non-AI arms against ERA5, by site and lead day.

Arms:
- persistence: the WBGT observed (in ERA5) at the same hour `lead` days earlier.
  The floor any forecast must beat.
- ecmwf_ifs025 and italia_meteo_arpae_icon_2i from Open-Meteo's archived runs,
  turned into WBGT with each model's own direct radiation.

Truth: WBGT from ERA5 with ERA5's own direct fraction. Every arm goes through the
same `turno.evaluate` functions. Output: results/baselines.md and .json.
"""

from __future__ import annotations

import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import xarray as xr

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from turno.evaluate import decision_score, wbgt_score  # noqa: E402
from turno.grid import load_lsm, nearest_land_cell  # noqa: E402
from turno.sites import SITES  # noqa: E402
from turno.solar import cos_zenith_hour_mean  # noqa: E402
from turno.wbgt import WbgtInputs, wbgt_c  # noqa: E402

LEADS = [1, 2, 3, 4, 5]
MODELS = ["ecmwf_ifs025", "italia_meteo_arpae_icon_2i"]
WORKLOAD, ACCLIMATIZED = "heavy", True


def utc(ts: str) -> datetime:
    return datetime.fromisoformat(ts).replace(tzinfo=timezone.utc)


def truth_for_site(ds: xr.Dataset, lat: float, lon: float) -> dict[str, float]:
    x = ds.sel(latitude=lat, longitude=lon, method="nearest").load()
    times = [datetime.fromtimestamp(int(t) / 1e9, tz=timezone.utc) for t in x.time.values.astype("int64")]
    glat, glon = float(x.latitude), float(x.longitude)
    ssrd = x["ssrd"].values / 3600.0
    fdir = np.where(ssrd > 1.0, (x["fdir"].values / 3600.0) / np.maximum(ssrd, 1e-9), 0.0)
    cz = np.array([float(cos_zenith_hour_mean(t, glat, glon)) for t in times])
    w = wbgt_c(WbgtInputs(x["t2m"].values, x["d2m"].values, x["sp"].values, x["u10"].values,
                          x["v10"].values, ssrd, cz, np.clip(fdir, 0, 1)))
    return {t.strftime("%Y-%m-%dT%H:%M"): float(v) for t, v in zip(times, w)}


def model_wbgt(h: dict, model: str, lead: int, lat: float, lon: float) -> dict[str, float]:
    def col(v):
        return np.array([np.nan if a is None else a for a in h[f"{v}_previous_day{lead}_{model}"]], dtype=float)

    t2 = col("temperature_2m") + 273.15
    td = col("dew_point_2m") + 273.15
    sp = col("surface_pressure") * 100.0
    ws = col("wind_speed_10m")
    sw = col("shortwave_radiation")
    dr = col("direct_radiation")
    fdir = np.where(sw > 1.0, dr / np.maximum(sw, 1e-9), 0.0)
    cz = np.array([float(cos_zenith_hour_mean(utc(t), lat, lon)) for t in h["time"]])
    w = wbgt_c(WbgtInputs(t2, td, sp, ws, np.zeros_like(ws), sw, cz, np.clip(fdir, 0, 1)))
    return {t: float(v) for t, v in zip(h["time"], w)}


def main() -> int:
    files = sorted((ROOT / "data" / "era5").glob("era5_italy_2026*.nc"))
    if not files:
        raise SystemExit("no ERA5 yet")
    ds = xr.open_mfdataset(files, combine="by_coords")
    if "valid_time" in ds.dims:
        ds = ds.rename({"valid_time": "time"})

    lsm = load_lsm(ROOT / "data" / "era5" / "era5_italy_lsm.nc")
    rows, table = [], []
    for s in SITES:
        clat, clon, _ = nearest_land_cell(lsm, s.lat, s.lon)
        truth = truth_for_site(ds, clat, clon)
        h = json.loads((ROOT / "data" / "baselines" / f"{s.key}.json").read_text())["hourly"]
        arms: dict[tuple[str, int], dict[str, float]] = {}
        keys = sorted(truth)
        for lead in LEADS:
            arms[("persistence", lead)] = {
                k: truth[keys[i - 24 * lead]] for i, k in enumerate(keys) if i >= 24 * lead
            }
            for m in MODELS:
                if f"temperature_2m_previous_day{lead}_{m}" in h:
                    arms[(m, lead)] = model_wbgt(h, m, lead, clat, clon)
        for (arm, lead), fc in arms.items():
            common = [k for k in keys if k in fc and np.isfinite(fc[k])]
            if len(common) < 24:
                continue
            ws = wbgt_score([fc[k] for k in common], [truth[k] for k in common])
            dsc = decision_score([[fc[k]] for k in common], [truth[k] for k in common], WORKLOAD, ACCLIMATIZED)
            row = {"site": s.key, "arm": arm, "lead_days": lead, "n": ws.n, "mae_c": round(ws.mae_c, 2),
                   "bias_c": round(ws.bias_c, 2), "restricted_hours": dsc.restricted_truth,
                   "missed": dsc.missed, "miss_rate": round(dsc.miss_rate, 3),
                   "false_restrictions": dsc.false_restrictions}
            rows.append(row)
            table.append(f"| {s.name} | {arm} | {lead} | {ws.n} | {ws.mae_c:.2f} | {ws.bias_c:+.2f} | "
                         f"{dsc.restricted_truth} | {dsc.missed} | {dsc.miss_rate:.1%} | {dsc.false_restrictions} |")

    out = ROOT / "results"
    out.mkdir(exist_ok=True)
    (out / "baselines.json").write_text(json.dumps(rows, indent=1))
    head = [
        "# Non-AI baselines against ERA5 WBGT",
        "",
        f"Run {date.today().isoformat()}. Workload: {WORKLOAD}, acclimatized. A miss is an hour planned as more "
        "work than ERA5 allows. Truth is ERA5, itself a 0.25 degree reanalysis, not a site measurement; every arm "
        "is read at the same ERA5 land cell, at the cell's mean height. Scoring against ERA5 favours models on "
        "ERA5's own grid, so the 2 km ICON-2I is disadvantaged here.",
        "",
        "| Site | Arm | Lead (days) | Hours | WBGT MAE C | Bias C | Restricted hours | Missed | Miss rate | False restrictions |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    (out / "baselines.md").write_text("\n".join(head + table) + "\n")
    print("\n".join(head + table))
    return 0


if __name__ == "__main__":
    sys.exit(main())
