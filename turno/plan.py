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
    banned_by: str | None = None,
) -> HourPlan:
    """Decide one hour. `banned_by` names the ordinance when one applies."""
    if isinstance(workload, str):
        workload = WORKLOADS[workload]
    members = tuple(float(x) for x in np.asarray(wbgt_members_c, dtype=float).ravel())
    if not members or any(not np.isfinite(x) for x in members):
        raise ValueError("every member must be a finite WBGT value")

    if banned_by:
        return HourPlan(hour_local, Outcome.BANNED, 0, (0, 0), members, (f"Banned by {banned_by}.",))

    bands = [minutes_band(w, workload, acclimatized) for w in members]
    fewest = min(b.fewest for b in bands)
    most = max(b.most for b in bands)

    if fewest == most:
        return HourPlan(hour_local, Outcome.WORK, fewest, (fewest, most), members)

    reasons = []
    if len({b.fewest for b in bands}) > 1:
        reasons.append(
            f"Forecast members disagree: WBGT from {min(members):.1f} to {max(members):.1f} C "
            f"spans more than one work step."
        )
    if any(not b.determined for b in bands):
        reasons.append(
            f"The answer depends on how hard the crew works within {workload.label} "
            f"({workload.m_low_w:.0f} to {workload.m_high_w:.0f} W), which a forecast cannot know."
        )
    return HourPlan(hour_local, Outcome.UNDETERMINED, fewest, (fewest, most), members, tuple(reasons))
