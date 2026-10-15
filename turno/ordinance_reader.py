"""Read a regional heat ordinance and propose a rule, which code then checks.

Sixteen Italian regions issue these every summer and amend them (Lazio three
times in 2026). Keeping the rules current by hand is the maintenance job this
automates, under one constraint: the model may propose, never decide.

1. The signed PDF is read by MinerU2.5-Pro on AMD (Token Factory OCR).
2. A chat model on AMD proposes each field together with a verbatim quote from
   the text that supports it.
3. Deterministic checks accept a field only if its quote is really in the
   document and actually contains the value. Anything else is marked for a
   person, with the reason. Nothing reaches `ordinances.py` without that.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from .amd_llm import BASE_URL, DEFAULT_MODEL, api_key, chat

OCR_CACHE = Path(__file__).resolve().parent.parent / "data" / "ocr"

MONTHS_IT = {
    "gennaio": 1, "febbraio": 2, "marzo": 3, "aprile": 4, "maggio": 5, "giugno": 6, "luglio": 7,
    "agosto": 8, "settembre": 9, "ottobre": 10, "novembre": 11, "dicembre": 12,
}

FIELDS = ("valid_from", "valid_to", "ban_start", "ban_end", "trigger", "sectors", "exemptions")

PROMPT = """You read an Italian regional ordinance on heat and outdoor work. Return JSON with these keys.
For every key give {"value": ..., "quote": ...} where "quote" is copied character for character from the
text and contains the value. If the text does not state it, use {"value": null, "quote": null}.

- valid_from: first day the ban applies, as YYYY-MM-DD
- valid_to: last day the ban applies, as YYYY-MM-DD
- ban_start: daily start of the ban, as HH:MM
- ban_end: daily end of the ban, as HH:MM
- trigger: the condition that activates the ban (value: one sentence in English; quote: the Italian wording)
- sectors: which work is covered (value: short English list; quote: the Italian wording)
- exemptions: who is exempt (value: short English list; quote: the Italian wording)

Also return "amends_or_extends": true if this act extends or changes an earlier ordinance, else false,
with its own "quote". Copy quotes exactly; do not translate or tidy them."""


def ocr_pdf(url: str, key: str, pages: str = "0-5") -> str:
    """Markdown of a PDF, read on AMD by MinerU2.5-Pro, cached by key."""
    OCR_CACHE.mkdir(parents=True, exist_ok=True)
    cached = OCR_CACHE / f"{key}.md"
    if cached.exists():
        return cached.read_text()
    r = httpx.post(
        f"{BASE_URL}/ocr",
        headers={"Authorization": f"Bearer {api_key()}"},
        json={"model": "MinerU2.5-Pro", "document": {"type": "document_url", "document_url": url}, "pages": pages},
        timeout=900,
    )
    r.raise_for_status()
    md = "\n\n".join(p.get("markdown", "") for p in r.json().get("pages", []))
    cached.write_text(md)
    return md


def _norm(s: str) -> str:
    """Letters and digits only, lower case, accents folded: survives OCR line breaks,
    hyphenation, curly quotes and spacing, and nothing else."""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _time_forms(hhmm: str) -> list[str]:
    h, m = hhmm.split(":")
    hs = str(int(h))
    return [f"{h}{m}", f"{hs}{m}"] if m != "00" else [f"{h}00", f"{hs}00", f"ore{hs}"]


def _date_in(quote: str, iso: str) -> bool:
    y, mo, d = (int(x) for x in iso.split("-"))
    q = quote.lower()
    numeric = re.search(rf"\b0?{d}\s*[/.\-]\s*0?{mo}\s*[/.\-]\s*(?:{y}|{y % 100})\b", q)
    named = any(
        re.search(rf"\b0?{d}\s*(?:°|º)?\s*{name}\b", q) for name, n in MONTHS_IT.items() if n == mo
    )
    return bool(numeric or named)


@dataclass
class FieldCheck:
    name: str
    value: object
    quote: str | None
    accepted: bool
    reason: str


@dataclass
class Reading:
    region: str
    model: str
    checks: dict[str, FieldCheck]
    amends: bool | None
    cost_usd: float
    latency_s: float
    raw: dict = field(repr=False, default_factory=dict)

    @property
    def needs_person(self) -> list[str]:
        return [n for n, c in self.checks.items() if not c.accepted]


def check_field(name: str, item: dict | None, source: str) -> FieldCheck:
    item = item or {}
    value, quote = item.get("value"), item.get("quote")
    if value in (None, "") or not quote:
        return FieldCheck(name, value, quote, False, "not found in the text")
    if _norm(quote) not in _norm(source):
        return FieldCheck(name, value, quote, False, "quote is not in the document")
    if name in ("valid_from", "valid_to"):
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(value)) or not _date_in(quote, str(value)):
            return FieldCheck(name, value, quote, False, "date does not appear in its quote")
    if name in ("ban_start", "ban_end"):
        if not re.fullmatch(r"\d{2}:\d{2}", str(value)) or not any(f in _norm(quote) for f in _time_forms(str(value))):
            return FieldCheck(name, value, quote, False, "time does not appear in its quote")
    return FieldCheck(name, value, quote, True, "quote found in the document and contains the value")


def read(region: str, text: str, model: str = DEFAULT_MODEL) -> Reading:
    r = chat(
        [{"role": "system", "content": PROMPT}, {"role": "user", "content": text[:120_000]}],
        model=model, max_tokens=2500, json_mode=True, task=f"ordinance:{region}",
    )
    try:
        d = json.loads(r.text)
    except json.JSONDecodeError:
        d = {}
    checks = {n: check_field(n, d.get(n), text) for n in FIELDS}
    am = d.get("amends_or_extends")
    amends = am.get("value") if isinstance(am, dict) else am if isinstance(am, bool) else None
    return Reading(region, model, checks, amends, r.cost_usd, r.latency_s, d)
