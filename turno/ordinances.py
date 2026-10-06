"""Italian regional heat ordinances as rules, read only from their own texts.

Every 2026 ordinance found bans manual outdoor work under prolonged sun from
12:30 to 16:00 (Veneto later narrowed to 14:00 to 16:00), on days and in areas
where Worklimate's map for "lavoratori esposti al sole" with "attivita fisica
intensa" at 12:00 shows "ALTO". The records, with verbatim text and URLs, are in
data/ordinances_2026.json; the source texts in sources/ordinances/.

What this module will and will not do:
- It decides alone only from a record that is VERIFIED_PRIMARY and has both
  validity dates. Anything else gives CANNOT_DETERMINE with the reason.
- It never decides whether today is an "ALTO" day. That is Worklimate's official
  rating, and the supervisor states it. Until they do, a ban that could apply
  is CANNOT_DETERMINE, not a guess either way.
- It never interprets which sectors are covered. It returns the ordinance's own
  words and the supervisor confirms the crew's work is among them.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, time
from enum import Enum
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data" / "ordinances_2026.json"

# Sardegna: order n. 3 ran to 31 Aug 2026 and order n. 4 re-adopted the ban from
# 7 Sep 2026. Order n. 4 states that n. 3 "cessata di produrre effetti il 31
# agosto 2026", so there was no ban from 1 to 6 September. The JSON record keeps
# one row spanning both; the windows are split here, from that text.
WINDOW_OVERRIDES = {
    ("Sardegna", "3"): [(date(2026, 6, 17), date(2026, 8, 31)), (date(2026, 9, 7), date(2026, 9, 30))],
}


class BanStatus(str, Enum):
    APPLIES = "applies"
    DOES_NOT_APPLY = "does_not_apply"
    CANNOT_DETERMINE = "cannot_determine"


@dataclass(frozen=True)
class Ordinance:
    region: str
    number: str
    status: str
    windows: tuple[tuple[date, date], ...] | None
    ban_start: time
    ban_end: time
    url: str
    trigger_verbatim: str
    sectors_verbatim: str

    @property
    def decidable(self) -> bool:
        return self.status == "VERIFIED_PRIMARY" and self.windows is not None


@dataclass(frozen=True)
class BanResult:
    """`banned_minutes` is what the ban covers if it applies. For CANNOT_DETERMINE
    it is the minutes it would cover, so a caller that assumes the ban, the
    cautious reading, has the right number."""

    status: BanStatus
    banned_minutes: int
    reason: str
    ordinance: Ordinance | None = None


def _d(s: str | None) -> date | None:
    return date.fromisoformat(s) if s else None


def _t(s: str) -> time:
    h, m = s.split(":")
    return time(int(h), int(m))


def load(path: Path = DATA) -> dict[str, list[Ordinance]]:
    by_region: dict[str, list[Ordinance]] = {}
    for r in json.loads(path.read_text()):
        number = str(r.get("number") or "")
        key = (r["region"], number)
        if key in WINDOW_OVERRIDES:
            windows = tuple(WINDOW_OVERRIDES[key])
        else:
            a, b = _d(r.get("valid_from")), _d(r.get("valid_to"))
            windows = ((a, b),) if a and b else None
        by_region.setdefault(r["region"], []).append(
            Ordinance(
                region=r["region"],
                number=number or "unknown",
                status=r["status"],
                windows=windows,
                ban_start=_t(r["ban_start"]),
                ban_end=_t(r["ban_end"]),
                url=r.get("url") or "",
                trigger_verbatim=r.get("trigger_profile_verbatim") or "",
                sectors_verbatim=r.get("sectors_verbatim") or "",
            )
        )
    return by_region


def minutes_in_window(hour: int, start: time, end: time) -> int:
    """How many minutes of the clock hour [hour:00, hour+1:00) fall in [start, end)."""
    h0, h1 = hour * 60, (hour + 1) * 60
    s, e = start.hour * 60 + start.minute, end.hour * 60 + end.minute
    return max(0, min(h1, e) - max(h0, s))


def ban_for_hour(
    ordinances: dict[str, list[Ordinance]],
    region: str,
    day: date,
    hour_local: int,
    worklimate_alto: bool | None,
    sector_confirmed: bool,
) -> BanResult:
    """Whether a regional ban covers this local clock hour, and for how many minutes."""
    candidates = ordinances.get(region, [])
    in_clock = [o for o in candidates if minutes_in_window(hour_local, o.ban_start, o.ban_end) > 0]
    if not in_clock:
        return BanResult(BanStatus.DOES_NOT_APPLY, 0, "Outside every ban window for this region.")

    undecidable = [o for o in in_clock if not o.decidable]
    live = [o for o in in_clock if o.decidable and any(a <= day <= b for a, b in o.windows)]

    if undecidable and not live:
        o = undecidable[0]
        return BanResult(
            BanStatus.CANNOT_DETERMINE, minutes_in_window(hour_local, o.ban_start, o.ban_end),
            f"{region} ordinance {o.number} is {o.status.lower().replace('_', ' ')} or has no confirmed "
            f"dates. Check the region's official text before planning this hour.", o,
        )
    if not live:
        return BanResult(BanStatus.DOES_NOT_APPLY, 0, f"No {region} ordinance in force on {day.isoformat()}.")

    o = live[0]
    minutes = minutes_in_window(hour_local, o.ban_start, o.ban_end)
    if not sector_confirmed:
        return BanResult(BanStatus.CANNOT_DETERMINE, minutes,
                         f"Confirm the crew's work is covered by {region} ordinance {o.number}: "
                         f"\"{o.sectors_verbatim[:160]}\"", o)
    if worklimate_alto is None:
        return BanResult(BanStatus.CANNOT_DETERMINE, minutes,
                         f"{region} ordinance {o.number} bans {o.ban_start:%H:%M} to {o.ban_end:%H:%M} on "
                         f"Worklimate \"ALTO\" days. Confirm today's official rating at worklimate.it.", o)
    if not worklimate_alto:
        return BanResult(BanStatus.DOES_NOT_APPLY, 0,
                         f"Supervisor confirmed Worklimate is not \"ALTO\" today; {region} ordinance {o.number} "
                         f"does not apply.", o)
    return BanResult(BanStatus.APPLIES, minutes,
                     f"{region} ordinance {o.number}: no work {o.ban_start:%H:%M} to {o.ban_end:%H:%M} "
                     f"on a Worklimate \"ALTO\" day.", o)
