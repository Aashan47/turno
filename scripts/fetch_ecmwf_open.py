"""Fetch ECMWF open-data forecasts (IFS and ENS) on the 0.25 degree grid, cropped to Italy.

These are the like-for-like baselines for Aurora: same grid, same cells, same
rules. Source: ECMWF open data on AWS (s3://ecmwf-forecasts), CC BY 4.0.

Each forecast file is global, so this script reads the `.index` next to it,
downloads only the byte ranges of the six fields WBGT needs, crops each message
to the Italy box, and keeps only the crop. Members can be limited to save
bandwidth; the number used is recorded in the output.

Usage:
  fetch_ecmwf_open.py 2026-07-30 --stream oper
  fetch_ecmwf_open.py 2026-07-30 --stream enfo --members 10 --max-step 120
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

import httpx
import numpy as np
import xarray as xr

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://ecmwf-forecasts.s3.eu-central-1.amazonaws.com"
PARAMS = ["2t", "2d", "10u", "10v", "sp", "ssrd"]
# Same box as the ERA5 download: north, west, south, east.
NORTH, WEST, SOUTH, EAST = 47.5, 6.0, 36.0, 19.0


# AWS throttles bursts on this public bucket ("SlowDown"). A short pause between
# requests and an exponential backoff, capped at two minutes, keep a long fetch alive.
PAUSE_S = 0.25


def get(client: httpx.Client, url: str, headers=None) -> bytes:
    for attempt in range(12):
        time.sleep(PAUSE_S)
        r = client.get(url, headers=headers or {})
        if r.status_code in (200, 206):
            return r.content
        if r.status_code in (429, 503) or b"SlowDown" in r.content[:300]:
            time.sleep(min(120, 5 * 2**attempt))
            continue
        r.raise_for_status()
    raise RuntimeError(f"gave up on {url}")


def crop(grib_bytes: bytes) -> xr.DataArray:
    with tempfile.NamedTemporaryFile(suffix=".grib2") as f:
        f.write(grib_bytes)
        f.flush()
        ds = xr.open_dataset(f.name, engine="cfgrib", backend_kwargs={"indexpath": ""})
        da = ds[list(ds.data_vars)[0]]
        lon = da.longitude.values
        if lon.max() > 180:
            da = da.assign_coords(longitude=((lon + 180) % 360) - 180).sortby("longitude")
        return da.sel(latitude=slice(NORTH, SOUTH), longitude=slice(WEST, EAST)).load()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("date")
    ap.add_argument("--stream", choices=["oper", "enfo"], default="oper")
    ap.add_argument("--members", type=int, default=10)
    ap.add_argument("--max-step", type=int, default=120)
    ap.add_argument("--step-every", type=int, default=3)
    a = ap.parse_args()

    ymd = a.date.replace("-", "")
    kind = "fc" if a.stream == "oper" else "ef"
    out = ROOT / "data" / "ecmwf" / f"{a.stream}_{ymd}00.nc"
    if out.exists():
        print(f"skip {out.name}")
        return 0
    out.parent.mkdir(parents=True, exist_ok=True)

    steps = list(range(a.step_every, a.max_step + 1, a.step_every))
    fields: dict[str, list] = {p: [] for p in PARAMS}
    with httpx.Client(timeout=120) as client:
        for step in steps:
            stem = f"{BASE}/{ymd}/00z/ifs/0p25/{a.stream}/{ymd}000000-{step}h-{a.stream}-{kind}"
            index = [json.loads(line) for line in get(client, stem + ".index").decode().splitlines()
                     if line.startswith("{")]
            for p in PARAMS:
                recs = [r for r in index if r.get("param") == p and r.get("levtype") == "sfc"]
                if a.stream == "enfo":
                    recs = [r for r in recs if r.get("type") == "pf" and int(r.get("number", 0)) <= a.members]
                arrays = []
                for r in sorted(recs, key=lambda r: int(r.get("number", 0))):
                    lo, n = int(r["_offset"]), int(r["_length"])
                    da = crop(get(client, stem + ".grib2", {"Range": f"bytes={lo}-{lo + n - 1}"}))
                    arrays.append(da.values)
                fields[p].append(np.stack(arrays))
            print(f"{a.stream} {ymd} step {step}h done", flush=True)
            lat, lon = da.latitude.values, da.longitude.values

    ds = xr.Dataset(
        {p: (("step", "member", "latitude", "longitude"), np.stack(fields[p])) for p in PARAMS},
        coords={"step": steps, "latitude": lat, "longitude": lon},
        attrs={
            "source": "ECMWF open data on AWS, CC BY 4.0",
            "init": f"{a.date}T00:00Z",
            "stream": a.stream,
            "members": a.members if a.stream == "enfo" else 1,
            "ssrd": "accumulated J m-2 since step 0, as ECMWF publishes it",
        },
    )
    ds.to_netcdf(out)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
