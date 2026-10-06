"""One hour of a crew's plan, decided by rules from an ensemble of WBGT values.

The model forecasts. This module decides, and it is deterministic: the same
members in give the same plan out. Three outcomes, as in heatline:

- a fixed number of work minutes, when every member and both ends of the
  workload range agree;
- zero minutes, when an ordinance bans the hour, whatever the forecast says;
- "cannot be determined", when they do not agree. The plan then carries the
  most cautious value and the hour goes to the site supervisor, with the reason.

The legal trigger for Italian ordinances is Worklimate's own "Alto" rating, an
official product. Turno does not compute or imitate it. The supervisor states
whether it applies today, from worklimate.it, and Turno applies the ban.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import numpy as np

from .limits import Workload, WORKLOADS, minutes_band


class Outcome(str, Enum):
    WORK = "work"
    BANNED = "banned"
    UNDETERMINED = "undetermined"


@dataclass(frozen=True)
class HourPlan:
    hour_local: str
    outcome: Outcome
    minutes: int
    minutes_range: tuple[int, int]
    wbgt_members_c: tuple[float, ...]
    reasons: tuple[str, ...] = field(default_factory=tuple)

    @property
    def needs_supervisor(self) -> bool:
        return self.outcome is Outcome.UNDETERMINED

    def as_dict(self) -> dict:
        w = np.asarray(self.wbgt_members_c)
        return {
            "hour": self.hour_local,
            "outcome": self.outcome.value,
            "work_minutes": self.minutes,
            "work_minutes_range": list(self.minutes_range),
            "wbgt_c": {
                "min": round(float(w.min()), 1),
                "median": round(float(np.median(w)), 1),
                "max": round(float(w.max()), 1),
                "members": len(w),
            },
            "needs_supervisor": self.needs_supervisor,
            "reasons": list(self.reasons),
        }


def plan_hour(
    hour_local: str,
    wbgt_members_c,
    workload: Workload | str,
    acclimatized: bool,
    banned_minutes: int = 0,
    ban_reason: str | None = None,
    ban_uncertain: bool = False,
) -> HourPlan:
    """Decide one hour.

    `banned_minutes` is how much of the hour an ordinance bans (60, or 30 for the
    12:00 hour of a 12:30 ban). `ban_uncertain` means a ban could apply but
    something only a person can confirm is missing: the plan then assumes the ban,
    the cautious value, and hands the hour over with `ban_reason`.
    """
    if isinstance(workload, str):
        workload = WORKLOADS[workload]
    members = tuple(float(x) for x in np.asarray(wbgt_members_c, dtype=float).ravel())
    if not members or any(not np.isfinite(x) for x in members):
        raise ValueError("every member must be a finite WBGT value")

    if banned_minutes >= 60 and not ban_uncertain:
        return HourPlan(hour_local, Outcome.BANNED, 0, (0, 0), members, (ban_reason or "Banned by ordinance.",))

    bands = [minutes_band(w, workload, acclimatized) for w in members]
    fewest = min(b.fewest for b in bands)
    most = max(b.most for b in bands)
    cap = 60 - max(0, min(60, banned_minutes))

    if ban_uncertain:
        return HourPlan(hour_local, Outcome.UNDETERMINED, min(fewest, cap), (min(fewest, cap), most), members,
                        (ban_reason or "An ordinance may apply.",))

    if cap < 60:
        fewest, most = min(fewest, cap), min(most, cap)

    # The plan is always made for the hard end of the workload range: NIOSH puts
    # the error of a workload estimate as high as 30%, so the cautious end is the
    # safe reading, not a guess. The range is reported, not handed over. Only
    # forecast members that disagree send the hour to a person, because that is
    # uncertainty a supervisor can act on (look at the sky, call the site).
    notes = [ban_reason] if cap < 60 and ban_reason else []
    if any(not b.determined for b in bands):
        notes.append(
            f"Planned for the hard end of {workload.label} ({workload.m_high_w:.0f} W); lighter work "
            f"within the range ({workload.m_low_w:.0f} W) would allow up to {most} minutes."
        )
    if len({b.fewest for b in bands}) == 1:
        return HourPlan(hour_local, Outcome.WORK, fewest, (fewest, most), members, tuple(notes))

    reasons = notes + [
        f"Forecast members disagree: WBGT from {min(members):.1f} to {max(members):.1f} C "
        f"spans more than one work step."
    ]
    return HourPlan(hour_local, Outcome.UNDETERMINED, fewest, (fewest, most), members, tuple(reasons))
