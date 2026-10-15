"""Proof of value from the data: what the ordinance alone leaves exposed, and what Turno adds.

1. Exposure outside the ban (ERA5, every hour of June to August 2026, 5 sites,
   working hours 07:00 to 19:00 local): of the working hours in which NIOSH
   limits allowed less than a full hour of work, how many fall outside the
   12:30 to 16:00 ban window. The count assumes the ban applied every day, which
   it did not (only on Worklimate "ALTO" days), so the true exposure outside any
   ban is at least this large.
2. Turno against the single ECMWF forecast on the July and August test set:
   restricted times missed and minutes over-planned, from results/grid_scores.jsonl.

Output: results/value.md and results/value.json
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import xarray as xr

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from turno.forecast import LOCAL_OFFSET_H  # noqa: E402
from turno.grid import load_lsm, nearest_land_cell  # noqa: E402
from turno.limits import minutes_band  # noqa: E402
from turno.sites import SITES  # noqa: E402
from turno.solar import cos_zenith_hour_mean  # noqa: E402
from turno.wbgt import WbgtInputs, wbgt_c  # noqa: E402

BAN_MINUTES = {12: 30, 13: 60, 14: 60, 15: 60}  # 12:30 to 16:00, by local clock hour
SETTINGS = [("heavy", False), ("moderate", False), ("heavy", True)]


def truth_wbgt(ds, lat, lon):
    x = ds.sel(latitude=lat, longitude=lon).load()
    times = [datetime.fromtimestamp(int(t) / 1e9, tz=timezone.utc) for t in x.time.values.astype("int64")]
    sw = x["ssrd"].values / 3600.0
    fd = np.where(sw > 1.0, (x["fdir"].values / 3600.0) / np.maximum(sw, 1e-9), 0.0)
    cz = np.array([float(cos_zenith_hour_mean(t, lat, lon)) for t in times])
    w = wbgt_c(WbgtInputs(x["t2m"].values, x["d2m"].values, x["sp"].values, x["u10"].values, x["v10"].values,
                          sw, cz, np.clip(fd, 0, 1)))
    return times, np.asarray(w)


def main() -> int:
    ds = xr.open_mfdataset(sorted((ROOT / "data" / "era5").glob("era5_italy_2026*.nc")), combine="by_coords")
    if "valid_time" in ds.dims:
        ds = ds.rename({"valid_time": "time"})
    lsm = load_lsm(ROOT / "data" / "era5" / "era5_italy_lsm.nc")
    exposure = {}
    for wl, accl in SETTINGS:
        tot = defaultdict(int)
        for s in SITES:
            times, w = truth_wbgt(ds, *nearest_land_cell(lsm, s.lat, s.lon)[:2])
            for t, v in zip(times, w):
                h = (t.hour + LOCAL_OFFSET_H) % 24
                if not 7 <= h <= 19:
                    continue
                m = minutes_band(float(v), wl, accl).fewest
                if m >= 60:
                    continue
                tot["restricted_hours"] += 1
                lost = 60 - m
                tot["restricted_minutes"] += lost
                ban = BAN_MINUTES.get(h, 0)
                if ban == 0:
                    tot["outside_hours"] += 1
                    tot["outside_minutes"] += lost
                else:
                    tot["outside_minutes"] += max(0, lost - ban)
        tot["share_hours_outside"] = round(tot["outside_hours"] / tot["restricted_hours"], 3) if tot["restricted_hours"] else 0
        tot["share_minutes_outside"] = round(tot["outside_minutes"] / tot["restricted_minutes"], 3) if tot["restricted_minutes"] else 0
        exposure[f"{wl}|{'accl' if accl else 'unaccl'}"] = dict(tot)

    rows = [json.loads(l) for l in (ROOT / "results" / "grid_scores.jsonl").read_text().splitlines()]
    cmp = defaultdict(lambda: defaultdict(float))
    for r in rows:
        if r["acclimatized"] or not r["init"].startswith(("2026-07", "2026-08")):
            continue
        a = cmp[(r["arm"], r["lead_days"])]
        for f in ("restricted", "missed", "hours", "minutes_over", "minutes_under", "handed_over"):
            a[f] += r[f]
    gains = []
    for lead in range(1, 6):
        o, e = cmp.get(("oper", lead)), cmp.get(("enfo", lead))
        if not o or not e:
            continue
        gains.append({"lead_days": lead, "times": int(e["hours"]), "restricted": int(e["restricted"]),
                      "missed_single": int(o["missed"]), "missed_turno": int(e["missed"]),
                      "over_minutes_single": int(o["minutes_over"]), "over_minutes_turno": int(e["minutes_over"]),
                      "withheld_minutes_single": int(o["minutes_under"]), "withheld_minutes_turno": int(e["minutes_under"]),
                      "handed_over": int(e["handed_over"])})

    out = {"exposure_outside_ban": exposure, "turno_vs_single_forecast": gains}
    (ROOT / "results" / "value.json").write_text(json.dumps(out, indent=1))
    L = ["# Proof of value", "", f"Run {date.today().isoformat()}. ERA5, June to August 2026, 5 sites, working hours 07:00 to 19:00.", "",
         "## What the 12:30 to 16:00 ban leaves exposed", "",
         "Heat-restricted working hours (NIOSH allows less than a full hour of work), counted as if the ban applied every day.", "",
         "| Work, crew | Restricted hours | Outside the ban window | Share of hours | Share of lost work minutes outside |",
         "|---|---|---|---|---|"]
    for k, t in exposure.items():
        wl, a = k.split("|")
        L.append(f"| {wl}, {'acclimatized' if a == 'accl' else 'not acclimatized'} | {t['restricted_hours']} | "
                 f"{t['outside_hours']} | {t['share_hours_outside']:.0%} | {t['share_minutes_outside']:.0%} |")
    L += ["", "## Turno against the single ECMWF forecast (July and August test set, 3-hourly working times)", "",
          "| Lead (days) | Times | Restricted | Missed: single | **Missed: Turno** | Over-planned min: single | **Over-planned min: Turno** | Withheld min: single | Withheld min: Turno |",
          "|---|---|---|---|---|---|---|---|---|"]
    for g in gains:
        L.append(f"| {g['lead_days']} | {g['times']} | {g['restricted']} | {g['missed_single']} | **{g['missed_turno']}** | "
                 f"{g['over_minutes_single']} | **{g['over_minutes_turno']}** | {g['withheld_minutes_single']} | {g['withheld_minutes_turno']} |")
    (ROOT / "results" / "value.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    sys.exit(main())
