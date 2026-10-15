"""A crew's working day: forecast members, the regional ordinance, and the rules.

Everything here is deterministic. It joins three things the rest of the package
already checks on their own: hourly WBGT members (forecast.py), the regional
ban for each hour (ordinances.py) and the hour plan with the frozen settings
(plan.py, rules.py).
"""

from __future__ import annotations

from datetime import date

from .ordinances import BanStatus, Ordinance, ban_for_hour
from .plan import plan_hour
from .rules import HANDOVER_STEPS, PLAN_QUANTILE


def plan_day(
    ordinances: dict[str, list[Ordinance]],
    region: str,
    day: date,
    members_by_hour: dict[int, list[float]],
    workload: str,
    acclimatized: bool,
    worklimate_alto: bool | None,
    sector_confirmed: bool = True,
) -> dict:
    hours = []
    for h in sorted(members_by_hour):
        ban = ban_for_hour(ordinances, region, day, h, worklimate_alto, sector_confirmed)
        p = plan_hour(
            f"{h:02d}:00", members_by_hour[h], workload, acclimatized,
            banned_minutes=ban.banned_minutes if ban.status is not BanStatus.DOES_NOT_APPLY else 0,
            ban_reason=ban.reason if ban.status is not BanStatus.DOES_NOT_APPLY else None,
            ban_uncertain=ban.status is BanStatus.CANNOT_DETERMINE,
            plan_quantile=PLAN_QUANTILE, handover_steps=HANDOVER_STEPS,
        )
        d = p.as_dict()
        d["ban_status"] = ban.status.value
        hours.append(d)
    worked = sum(h["work_minutes"] for h in hours)
    return {
        "workload": workload,
        "acclimatized": acclimatized,
        "worklimate_alto": worklimate_alto,
        "hours": hours,
        "summary": {
            "work_minutes": worked,
            "of_minutes": 60 * len(hours),
            "banned_hours": sum(1 for h in hours if h["outcome"] == "banned"),
            "handed_over": sum(1 for h in hours if h["needs_supervisor"]),
        },
    }
