"""Turno web server: static replay data plus two live model calls.

The science is precomputed (scripts/build_site_data.py), so this process only
serves files and makes two kinds of model call, each checked before it is shown:
- POST /api/briefing: Gemma 4 writes the crew briefing (turno/briefing.py);
- POST /api/explain: a model on AMD Token Factory explains a hand-off (turno/explain.py).
Answers are cached by their input, so a judge replaying a day gets the same text
and the shared rate limits are respected.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from turno.briefing import write as write_briefing  # noqa: E402
from turno.explain import explain  # noqa: E402
from turno.ordinance_reader import ocr_pdf, read as read_ordinance  # noqa: E402

WEB = Path(__file__).resolve().parent
CACHE = ROOT / "results" / "live_cache"
CACHE.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Turno")


def _cached(kind: str, payload: dict, fn):
    key = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:24]
    f = CACHE / f"{kind}-{key}.json"
    if f.exists():
        return json.loads(f.read_text())
    out = fn()
    f.write_text(json.dumps(out, ensure_ascii=False))
    return out


@app.post("/api/briefing")
def briefing(body: dict):
    plan = body.get("plan")
    if not isinstance(plan, dict) or not plan.get("hours"):
        raise HTTPException(400, "plan with hours required")

    def run():
        b = write_briefing(plan)
        return {"text": b.text, "by_model": b.by_model, "backend": b.backend, "model": b.model,
                "problems": b.problems}

    return JSONResponse(_cached("briefing", plan, run))


@app.post("/api/explain")
def explain_hour(body: dict):
    hour, site, day = body.get("hour"), body.get("site", ""), body.get("date", "")
    if not isinstance(hour, dict):
        raise HTTPException(400, "hour required")
    return JSONResponse(_cached("explain", {"hour": hour, "site": site, "date": day},
                                lambda: explain(hour, site, day)))


@app.post("/api/reread")
def reread(body: dict):
    """Re-read a region's signed ordinance PDF now, on AMD: MinerU OCR, then the
    chat model, then the quote checks. Only regions in the fixed source list."""
    region = str(body.get("region", ""))
    sources = json.loads((WEB / "data" / "ordinance_sources.json").read_text())
    if region not in sources:
        raise HTTPException(404, "no signed PDF on record for this region")

    def run():
        import time
        t0 = time.perf_counter()
        text = ocr_pdf(sources[region], region.lower().replace("-", ""))
        t_ocr = round(time.perf_counter() - t0, 1)
        rd = read_ordinance(region, text)
        return {"region": region, "at": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()), "model": rd.model, "ocr": "MinerU2.5-Pro on AMD Token Factory",
                "ocr_seconds": t_ocr, "read_seconds": rd.latency_s, "cost_usd": rd.cost_usd,
                "chars": len(text), "amends": rd.amends,
                "fields": {n: {"value": c.value, "quote": c.quote, "accepted": c.accepted, "reason": c.reason}
                           for n, c in rd.checks.items()}}

    return JSONResponse(_cached("reread", {"region": region}, run))


@app.get("/api/health")
def health():
    return {"ok": True}


app.mount("/data", StaticFiles(directory=WEB / "data"), name="data")
app.mount("/evidence", StaticFiles(directory=ROOT / "results"), name="evidence")
app.mount("/static", StaticFiles(directory=WEB / "static"), name="static")


@app.get("/")
def index():
    return FileResponse(WEB / "static" / "index.html")
