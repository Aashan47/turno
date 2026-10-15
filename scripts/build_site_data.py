"""Precompute every replay day for the web app, so the server needs no science stack.

For each site and each ECMWF ensemble init date, the replayed day is the next
day: Turno plans tomorrow from today's forecast, which is how a supervisor
would use it. For each crew setting (workload, acclimatized, the supervisor's
answer about today's Worklimate rating) the day is planned with the frozen
rules. Each day also carries ERA5's WBGT for the same hours: what actually
happened, so the replay can show the plan against reality.

Output: web/data/index.json and web/data/<site>/<date>.json
"""

from __future__ import annotations

import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import xarray as xr

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from turno.day_plan import plan_day  # noqa: E402
from turno.forecast import LOCAL_OFFSET_H, WORK_HOURS_LOCAL, hourly_members, member_wbgt_steps  # noqa: E402
from turno.grid import load_lsm, nearest_land_cell  # noqa: E402
from turno.ordinances import load as load_ordinances  # noqa: E402
from turno.plan import plan_hour  # noqa: E402
from turno.rules import ENSEMBLE_MEMBERS  # noqa: E402
from turno.sites import SITES  # noqa: E402
from turno.solar import cos_zenith_hour_mean  # noqa: E402
from turno.wbgt import WbgtInputs, wbgt_c  # noqa: E402

OUT = ROOT / "web" / "data"
WORKLOADS = ("moderate", "heavy", "very_heavy")
ALTO = {"unconfirmed": None, "alto": True, "not_alto": False}


def era5_hourly(ds: xr.Dataset, lat: float, lon: float, day: date) -> dict[int, float]:
    out = {}
    for h in WORK_HOURS_LOCAL:
        t = datetime(day.year, day.month, day.day, h, tzinfo=timezone.utc) - timedelta(hours=LOCAL_OFFSET_H)
        try:
            x = ds.sel(time=np.datetime64(t.replace(tzinfo=None)), latitude=lat, longitude=lon).load()
        except KeyError:
            continue
        sw = float(x["ssrd"]) / 3600.0
        fd = (float(x["fdir"]) / 3600.0) / sw if sw > 1.0 else 0.0
        cz = float(cos_zenith_hour_mean(t, lat, lon))
        out[h] = float(wbgt_c(WbgtInputs(np.array([float(x["t2m"])]), np.array([float(x["d2m"])]),
                                         np.array([float(x["sp"])]), np.array([float(x["u10"])]),
                                         np.array([float(x["v10"])]), np.array([sw]), np.array([cz]),
                                         np.array([min(max(fd, 0.0), 1.0)])))[0])
    return out


def main() -> int:
    era = xr.open_mfdataset(sorted((ROOT / "data" / "era5").glob("era5_italy_2026*.nc")), combine="by_coords")
    if "valid_time" in era.dims:
        era = era.rename({"valid_time": "time"})
    lsm = load_lsm(ROOT / "data" / "era5" / "era5_italy_lsm.nc")
    ords = load_ordinances()
    files = sorted((ROOT / "data" / "ecmwf").glob("enfo_*.nc"))
    index = {"sites": [], "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
             "forecast": f"ECMWF open-data ensemble, {ENSEMBLE_MEMBERS} members, 0.25 degrees",
             "truth": "ERA5 hourly reanalysis (Copernicus, CC BY 4.0)"}
    for s in SITES:
        lat, lon, landfrac = nearest_land_cell(lsm, s.lat, s.lon)
        site_days = []
        for f in files:
            fc = xr.open_dataset(f)
            fc = fc.isel(member=slice(0, ENSEMBLE_MEMBERS))
            init = datetime.fromisoformat(fc.attrs["init"].replace("Z", "+00:00"))
            day = (init + timedelta(days=1)).date()
            steps = member_wbgt_steps(fc, lat, lon)
            members = {h: [round(float(v), 2) for v in m] for h, m in hourly_members(steps, day).items()}
            if not members:
                continue
            truth = era5_hourly(era, lat, lon, day)
            plans = {}
            for wl in WORKLOADS:
                for accl in (False, True):
                    for akey, aval in ALTO.items():
                        plans[f"{wl}|{'accl' if accl else 'unaccl'}|{akey}"] = plan_day(
                            ords, s.region, day, members, wl, accl, aval)
            truth_minutes = {wl: {("accl" if a else "unaccl"): {
                str(h): plan_hour(f"{h:02d}:00", [w], wl, a).minutes for h, w in truth.items()}
                for a in (False, True)} for wl in WORKLOADS}
            region_ords = [{"number": o.number, "status": o.status, "url": o.url,
                            "ban": f"{o.ban_start:%H:%M}-{o.ban_end:%H:%M}",
                            "windows": [[a.isoformat(), b.isoformat()] for a, b in (o.windows or [])],
                            "trigger": o.trigger_verbatim, "sectors": o.sectors_verbatim}
                           for o in ords.get(s.region, [])]
            doc = {"site": s.key, "name": s.name, "region": s.region, "work": s.work,
                   "cell": {"lat": lat, "lon": lon, "land_fraction": round(landfrac, 2)},
                   "date": day.isoformat(), "forecast_init": init.strftime("%Y-%m-%d %H:%MZ"), "lead_days": 1,
                   "members_by_hour": {str(h): v for h, v in members.items()},
                   "truth_wbgt_by_hour": {str(h): round(v, 2) for h, v in truth.items()},
                   "truth_minutes": truth_minutes, "ordinances": region_ords, "plans": plans,
                   "interpolation": "ECMWF open data is 3-hourly; hourly values are linear in time between steps."}
            (OUT / s.key).mkdir(parents=True, exist_ok=True)
            (OUT / s.key / f"{day.isoformat()}.json").write_text(json.dumps(doc, ensure_ascii=False))
            site_days.append(day.isoformat())
        index["sites"].append({"key": s.key, "name": s.name, "region": s.region, "work": s.work,
                               "lat": s.lat, "lon": s.lon, "days": sorted(site_days)})
        print(s.key, len(site_days), "days", flush=True)
    (OUT / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1))
    # The only documents the live "re-read on AMD" action may fetch: each region's own
    # signed PDF, from the verified records. The server never takes a URL from a request.
    sys.path.insert(0, str(ROOT / "scripts"))
    from bench_ordinance_reader import OCR_REGIONS
    recs = json.loads((ROOT / "data" / "ordinances_2026.json").read_text())
    pdfs = {r["region"]: r["url"] for r in recs
            if r["region"] in OCR_REGIONS and r["status"] == "VERIFIED_PRIMARY" and r.get("url", "").startswith("http")}
    (OUT / "ordinance_sources.json").write_text(json.dumps(pdfs, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
