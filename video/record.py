"""Record the demo by driving the real app in a real browser.

Playwright loads http://127.0.0.1:8765/?demo=1 in a chrome-less Chromium page,
the scene in web/static/demo.js clicks through the product, the page makes the
same calls to AMD and to Gemma that any visitor's would, and Chromium's own
screencast captures the frames. No frame is drawn by hand.

Before the camera rolls, the two model answers the scene will ask for are
warmed with the exact payloads the page will send, so the answers are the
model's own and arrive from the cache on camera instead of after thirty
seconds of spinner. The Lombardia re-read is started as a background job
first; it takes 30 to 120 seconds on AMD and is finished by the time the
scene reaches it, and the result shown is that run's.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
OUT = HERE / "turno-demo.mp4"
NARRATION = HERE / "narration.json"
BASE = "http://127.0.0.1:8765"
URL = f"{BASE}/?demo=1"
W, H = 1920, 1080
BEATS = ["title", "open", "verdict", "strip", "toohigh", "alto", "banned", "decide",
         "explain", "briefing", "law", "reread", "live", "evidence", "close"]


def post(path: str, body: dict, timeout: int = 300) -> dict:
    req = urllib.request.Request(f"{BASE}{path}", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def get(path: str, timeout: int = 60) -> dict:
    with urllib.request.urlopen(f"{BASE}{path}", timeout=timeout) as r:
        return json.loads(r.read())


def preflight() -> None:
    get("/api/health")
    doc = get("/data/milano/2026-07-31.json")
    plan = doc["plans"]["heavy|unaccl|unconfirmed"]
    hour = next(h for h in plan["hours"] if h["hour"] == "12:00")
    print("warming the AMD explanation for 12:00", flush=True)
    r = post("/api/explain", {"hour": hour, "site": doc["name"], "date": doc["date"]})
    if not r.get("text"):
        raise SystemExit(f"the AMD explanation failed its check: {r.get('problems')}")
    print("warming the Gemma briefing", flush=True)
    plan_payload = {"site": doc["name"], "date": doc["date"], "crew": "heavy work, not acclimatized",
                    "ban_window": [], "hours": plan["hours"]}
    r = post("/api/briefing", {"plan": plan_payload})
    if not r.get("by_model"):
        raise SystemExit(f"Gemma's briefing failed its check: {r.get('problems')}")
    # Prove AMD's OCR is up before the camera rolls: a forced re-read with the
    # OCR cache cleared must finish. Then the cache is cleared again, so the scene's
    # own re-read, started at its first second, runs OCR and extraction on camera.
    ocr_cache = HERE.parent / "data" / "ocr" / "lombardia.md"
    ocr_cache.unlink(missing_ok=True)
    print("checking AMD OCR with a forced Lombardia re-read", flush=True)
    post("/api/reread", {"region": "Lombardia", "force": True}, timeout=30)
    for _ in range(100):
        time.sleep(3)
        st = get("/api/reread/Lombardia")
        if st.get("status") == "done":
            print(f"  ok: OCR {st['ocr_seconds']} s, extraction {st['read_seconds']} s", flush=True)
            break
        if st.get("status") == "error":
            raise SystemExit(f"AMD OCR failed in preflight: {st.get('message')}")
    else:
        raise SystemExit("AMD re-read did not finish in preflight")
    ocr_cache.unlink(missing_ok=True)


def line_timing() -> tuple[dict, float]:
    """Seconds of every narration line, by beat, from the cached voice clips.
    The scene paces the pointer to the lines and holds each beat for exactly
    as long as its lines need, so the picture and the voice are built from
    the same numbers."""
    import sys
    sys.path.insert(0, str(HERE))
    import narrate
    timing: dict[str, list[float]] = {}
    for beat, text in narrate.CUES:
        clip = narrate.clip_path(text)
        if not clip.exists():
            raise SystemExit(f"no voice clip yet for: {text[:60]}  (run video/synth_all.py first)")
        timing.setdefault(beat, []).append(round(narrate.duration(clip), 3))
    return timing, narrate.BREATH


def record(timing: dict, breath: float) -> Path:
    shutil.rmtree(RAW, ignore_errors=True)
    RAW.mkdir(parents=True)
    problems: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--force-device-scale-factor=1"])
        context = browser.new_context(viewport={"width": W, "height": H}, record_video_dir=str(RAW),
                                      record_video_size={"width": W, "height": H}, device_scale_factor=1)
        page = context.new_page()
        page.on("pageerror", lambda e: problems.append(f"pageerror: {e}"))
        page.on("console", lambda m: problems.append(f"{m.type}: {m.text}") if m.type == "error" else None)
        page.goto(URL, wait_until="networkidle")
        page.wait_for_function("document.fonts.status === 'loaded'", timeout=20000)
        page.wait_for_function("typeof window.__demoPlay === 'function'", timeout=15000)
        page.wait_for_function("document.querySelectorAll('#strip .col').length > 5", timeout=20000)
        lead_in = page.evaluate("performance.now()") / 1000.0
        page.evaluate("([t, b]) => window.__demoPlay(t, b)", [timing, breath])
        page.wait_for_function("window.__demoDone === true", timeout=600_000)
        err = page.evaluate("window.__demoError || null")
        marks = page.evaluate("window.__demoMarks")
        facts = page.evaluate("window.__demoFacts")
        elapsed = page.evaluate("window.__demoElapsed || 0")
        page.wait_for_timeout(400)
        video = page.video
        context.close()
        browser.close()
        path = Path(video.path())
    if err:
        raise SystemExit(f"the scene stopped: {err}")
    ids = [m["id"] for m in marks]
    if ids != BEATS:
        raise SystemExit(f"beats out of order or missing: {ids}")
    NARRATION.write_text(json.dumps({"lead_in": round(lead_in, 3), "elapsed": round(elapsed, 3),
                                     "beats": marks, "facts": facts}, indent=2))
    print(f"lead-in {lead_in:.2f}s, scene {elapsed:.1f}s")
    print("page problems:", problems or "none")
    return path


def main() -> None:
    timing, breath = line_timing()
    print("narration lines:", {b: len(v) for b, v in timing.items()}, flush=True)
    preflight()
    webm = record(timing, breath)
    stale = HERE / "narration.m4a"
    if stale.exists():
        stale.unlink()
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(webm), "-vf", "fps=30,format=yuv420p",
                    "-c:v", "libx264", "-preset", "slow", "-crf", "19", "-movflags", "+faststart", str(OUT)], check=True)
    # This take is the raw the narrator starts from; a stale raw from an earlier
    # take would otherwise be copied over the new recording.
    shutil.copyfile(OUT, HERE / "turno-demo-raw.mp4")
    dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(OUT)],
                         capture_output=True, text=True, check=True).stdout.strip()
    print(f"{OUT.name}  {float(dur):.1f}s  {OUT.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
