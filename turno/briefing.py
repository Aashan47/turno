"""The crew briefing: written by Gemma, checked by code, replaced if it fails.

Gemma turns the day's plan into a short briefing a foreman can read out. It
never computes anything. Every time and number in its text must already be in
the plan; otherwise the briefing is rejected, the reason recorded, and a fixed
template built from the plan is used instead.

Where Gemma runs is one setting, GEMMA_BACKEND:
- "vllm": an OpenAI-compatible Gemma endpoint, e.g. vLLM on an AMD GPU
  (GEMMA_BASE_URL, GEMMA_MODEL);
- "google" (default today): Google's Gemini API with the GEMENI_KEY in .env.
  This runs on Google's servers, not AMD, and the README says so.
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path

import httpx

ENV = Path(__file__).resolve().parents[5] / ".env"
LOG = Path(__file__).resolve().parent.parent / "results" / "gemma_calls.jsonl"

SYSTEM = (
    "You write a short heat-safety briefing for an outdoor work crew, from a plan you are given as JSON. "
    "Use only the times and numbers in the plan. Do not add advice the plan does not contain. Say plainly "
    "which hours are banned, which need the supervisor's decision and why, and how many minutes per hour "
    "the crew may work. Write the Italian version first, then the English version, under the headings "
    "ITALIANO and ENGLISH. At most 120 words per language."
)


def _env(name: str) -> str | None:
    if os.environ.get(name):
        return os.environ[name]
    if ENV.exists():
        for line in ENV.read_text().splitlines():
            k, _, v = line.partition("=")
            if k.strip().removeprefix("export ").strip() == name and v:
                return v.strip().strip('"').strip("'")
    return None


def _call_google(plan_json: str, model: str) -> tuple[str, dict]:
    key = _env("GEMENI_KEY") or _env("GEMINI_API_KEY")
    r = httpx.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        headers={"x-goog-api-key": key or "", "Content-Type": "application/json"},
        json={"systemInstruction": {"parts": [{"text": SYSTEM}]},
              "contents": [{"parts": [{"text": plan_json}]}],
              "generationConfig": {"maxOutputTokens": 4000, "temperature": 0.2}},
        timeout=180,
    )
    r.raise_for_status()
    d = r.json()
    parts = d["candidates"][0]["content"]["parts"]
    text = "\n".join(p.get("text", "") for p in parts if not p.get("thought"))
    return text, d.get("usageMetadata", {})


def _call_vllm(plan_json: str, model: str) -> tuple[str, dict]:
    base = _env("GEMMA_BASE_URL")
    r = httpx.post(f"{base}/chat/completions", json={
        "model": model, "max_tokens": 1200, "temperature": 0.2,
        "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": plan_json}]}, timeout=180)
    r.raise_for_status()
    d = r.json()
    return d["choices"][0]["message"]["content"], d.get("usage", {})


@dataclass
class Briefing:
    text: str
    by_model: bool
    backend: str
    model: str
    problems: list[str]


def allowed_tokens(plan: dict) -> set[str]:
    """Every number a briefing may mention, as it could appear in text."""
    out: set[str] = set()
    for h in plan.get("hours", []):
        out.add(str(int(h["hour"][:2])))
        out.add(h["hour"][:2])
        out.add(h["hour"])
        out.add(h["hour"].replace(":", "."))
        for m in (h["work_minutes"], *h.get("work_minutes_range", [])):
            out.add(str(m))
            out.add(str(60 - int(m)))
        w = h.get("wbgt_c", {})
        for k in ("min", "median", "max"):
            if k in w:
                out.add(f"{w[k]:.1f}")
                out.add(str(round(w[k])))
    for t in plan.get("ban_window", []):
        out.update({t, t.replace(":", "."), str(int(t[:2]))})
    d = plan.get("date", "")
    if d:
        y, mo, dd = d.split("-")
        out.update({y, mo, dd, str(int(mo)), str(int(dd)), d})
    return out


def check(text: str, plan: dict) -> list[str]:
    allowed = allowed_tokens(plan)
    problems = []
    for tok in re.findall(r"\d{1,2}[:.]\d{2}|\d+(?:[.,]\d+)?", text):
        t = tok.replace(",", ".")
        if t not in allowed and t.rstrip("0").rstrip(".") not in allowed:
            problems.append(f"number not in the plan: {tok}")
    if "ITALIANO" not in text.upper() or "ENGLISH" not in text.upper():
        problems.append("missing the Italian or English section")
    return problems


def template(plan: dict) -> str:
    lines_it, lines_en = [], []
    for h in plan["hours"]:
        if h["outcome"] == "banned":
            lines_it.append(f"{h['hour']}: lavoro vietato (ordinanza).")
            lines_en.append(f"{h['hour']}: no work (ordinance).")
        elif h["outcome"] == "undetermined":
            lines_it.append(f"{h['hour']}: decide il preposto; al massimo {h['work_minutes']} minuti.")
            lines_en.append(f"{h['hour']}: supervisor decides; at most {h['work_minutes']} minutes.")
        elif h["work_minutes"] < 60:
            lines_it.append(f"{h['hour']}: {h['work_minutes']} minuti di lavoro, il resto pausa all'ombra.")
            lines_en.append(f"{h['hour']}: {h['work_minutes']} minutes of work, the rest a break in shade.")
    return "ITALIANO\n" + "\n".join(lines_it) + "\n\nENGLISH\n" + "\n".join(lines_en)


def write(plan: dict) -> Briefing:
    backend = (_env("GEMMA_BACKEND") or "google").lower()
    model = _env("GEMMA_MODEL") or "gemma-4-31b-it"
    plan_json = json.dumps(plan, ensure_ascii=False)
    t0 = time.perf_counter()
    try:
        text, usage = (_call_vllm if backend == "vllm" else _call_google)(plan_json, model)
    except Exception as e:  # recorded, and the template still serves the crew
        return Briefing(template(plan), False, backend, model, [f"model call failed: {str(e)[:120]}"])
    problems = check(text, plan)
    LOG.parent.mkdir(exist_ok=True)
    with LOG.open("a") as f:
        f.write(json.dumps({"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "backend": backend,
                            "model": model, "latency_s": round(time.perf_counter() - t0, 3),
                            "usage": usage, "problems": problems}) + "\n")
    if problems:
        return Briefing(template(plan), False, backend, model, problems)
    return Briefing(text, True, backend, model, [])
