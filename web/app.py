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
import threading
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from turno.briefing import write as write_briefing  # noqa: E402
from turno.explain import explain  # noqa: E402
from turno.ordinance_reader import ocr_pdf, read as read_ordinance  # noqa: E402
from turno.ordinances import load as load_ordinances  # noqa: E402

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


# Re-reads take 30 to 120 seconds and AMD's OCR sometimes answers 502, so a re-read
# runs as a background job: POST starts it, GET reports it. One job per region at a
# time; a finished result is kept and shown with the time it ran.
_JOBS: dict[str, dict] = {}
_LOCK = threading.Lock()


def _reread_job(region: str, url: str) -> None:
    t0 = time.perf_counter()
    try:
        text = ocr_pdf(url, region.lower().replace("-", ""))
        t_ocr = round(time.perf_counter() - t0, 1)
        rd = read_ordinance(region, text)
        out = {"status": "done", "region": region, "at": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
               "model": rd.model, "ocr": "MinerU2.5-Pro on AMD Token Factory", "ocr_seconds": t_ocr,
               "read_seconds": rd.latency_s, "cost_usd": rd.cost_usd, "chars": len(text), "amends": rd.amends,
               "fields": {n: {"value": c.value, "quote": c.quote, "accepted": c.accepted, "reason": c.reason}
                          for n, c in rd.checks.items()}, "finished": time.time()}
        (CACHE / f"reread-{region}.json").write_text(json.dumps(out, ensure_ascii=False))
    except Exception as e:  # shown to the user; the stored reading is kept
        out = {"status": "error", "region": region, "message": f"{type(e).__name__}: {str(e)[:160]}"}
    with _LOCK:
        _JOBS[region] = out


@app.post("/api/reread")
def reread_start(body: dict):
    """Re-read a region's signed ordinance PDF now, on AMD. Only regions in the fixed source list."""
    region = str(body.get("region", ""))
    sources = json.loads((WEB / "data" / "ordinance_sources.json").read_text())
    if region not in sources:
        raise HTTPException(404, "no signed PDF on record for this region")
    with _LOCK:
        job = _JOBS.get(region) or {}
        if job.get("status") == "running":
            return JSONResponse(job)
        # A reading finished in the last ten minutes is still that reading; do not
        # spend a second run of AMD's OCR on the same PDF.
        if job.get("status") == "done" and time.time() - job.get("finished", 0) < 600 and not body.get("force"):
            return JSONResponse(job)
        _JOBS[region] = {"status": "running", "region": region, "started": time.time()}
    threading.Thread(target=_reread_job, args=(region, sources[region]), daemon=True).start()
    return JSONResponse(_JOBS[region])


@app.get("/api/reread/{region}")
def reread_status(region: str):
    with _LOCK:
        job = _JOBS.get(region)
    if job:
        return JSONResponse(job)
    f = CACHE / f"reread-{region}.json"
    return JSONResponse(json.loads(f.read_text()) if f.exists() else {"status": "none", "region": region})


_LIVE: dict[str, tuple[float, dict]] = {}


@app.get("/api/live/{site}")
def live(site: str):
    """Tomorrow's plan from the latest ECMWF ensemble, refreshed at most hourly."""
    cached = _LIVE.get(site)
    if cached and time.time() - cached[0] < 3600:
        return JSONResponse(cached[1])
    index = json.loads((WEB / "data" / "index.json").read_text())
    s = next((x for x in index["sites"] if x["key"] == site), None)
    if not s:
        raise HTTPException(404, "unknown site")
    any_day = json.loads((WEB / "data" / site / f"{s['days'][-1]}.json").read_text())
    from turno.live import tomorrow_doc
    doc = tomorrow_doc({**s, "site": site, "cell": any_day["cell"], "ordinances": any_day["ordinances"]},
                       load_ordinances(ROOT / "data" / "ordinances_2026.json"))
    _LIVE[site] = (time.time(), doc)
    return JSONResponse(doc)


@app.get("/api/health")
def health():
    return {"ok": True}


class Fresh(StaticFiles):
    """Static files that proxies and browsers must revalidate. The page links its
    own assets with a content hash, so a deploy is always a new URL; this header
    stops a CDN serving yesterday's script against today's page."""

    async def get_response(self, path, scope):
        r = await super().get_response(path, scope)
        r.headers["Cache-Control"] = "no-cache, must-revalidate"
        return r


app.mount("/data", Fresh(directory=WEB / "data"), name="data")
app.mount("/evidence", Fresh(directory=ROOT / "results"), name="evidence")
app.mount("/static", Fresh(directory=WEB / "static"), name="static")


def _asset_version() -> str:
    h = hashlib.sha256()
    for name in ("app.js", "style.css"):
        h.update((WEB / "static" / name).read_bytes())
    return h.hexdigest()[:10]


@app.get("/")
def index(demo: int = 0):
    html = (WEB / "static" / "index.html").read_text()
    v = _asset_version()
    html = html.replace('/static/style.css"', f'/static/style.css?v={v}"').replace('/static/app.js"', f'/static/app.js?v={v}"')
    if demo:
        # The recording scene drives the real page; it is only ever loaded on request.
        html = html.replace("</body>", f'<script src="/static/demo.js?v={v}"></script></body>')
    return HTMLResponse(html, headers={"Cache-Control": "no-cache, must-revalidate"})
