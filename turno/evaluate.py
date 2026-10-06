"""Scoring a forecast arm against ERA5, the same way for every arm.

Every arm (persistence, ECMWF's open ensemble, Open-Meteo, Aurora) is scored by
these functions and nothing else, so no arm gets a friendlier metric. Two kinds
of score:

- WBGT error by lead time, in degrees C;
- decision quality: did the plan restrict work in the hours where the truth
  required it, and how often did it hand the hour to a person instead.

The truth plan is computed from ERA5 WBGT with the same rules, so a decision
error is always a forecast error, never a rules difference.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .plan import Outcome, plan_hour


@dataclass(frozen=True)
class WbgtScore:
    n: int
    mae_c: float
    bias_c: float
    rmse_c: float


def wbgt_score(forecast_c, truth_c) -> WbgtScore:
    """Errors of a single-valued forecast (use the ensemble median for an ensemble)."""
    f = np.asarray(forecast_c, dtype=float)
    t = np.asarray(truth_c, dtype=float)
    ok = np.isfinite(f) & np.isfinite(t)
    d = f[ok] - t[ok]
    if d.size == 0:
        raise ValueError("no overlapping finite values to score")
    return WbgtScore(int(d.size), float(np.mean(np.abs(d))), float(np.mean(d)), float(np.sqrt(np.mean(d**2))))


@dataclass(frozen=True)
class DecisionScore:
    hours: int
    restricted_truth: int
    caught: int
    missed: int
    false_restrictions: int
    handed_to_supervisor: int
    minutes_lost_to_caution: int
    minutes_over_truth: int = 0
    minutes_under_truth: int = 0

    @property
    def miss_rate(self) -> float:
        return self.missed / self.restricted_truth if self.restricted_truth else 0.0

    @property
    def supervisor_rate(self) -> float:
        return self.handed_to_supervisor / self.hours if self.hours else 0.0


def decision_score(
    members_by_hour,
    truth_by_hour,
    workload: str,
    acclimatized: bool,
    plan_quantile: float = 1.0,
    handover_steps: int = 1,
) -> DecisionScore:
    """Compare per-hour plans from forecast members against plans from the truth.

    A "restricted" hour is one where the truth allows fewer than 60 work minutes
    at the cautious end. A miss is a restricted hour the forecast planned as more
    work than the truth allows, which is the error that hurts someone. An
    undetermined hour is scored on its cautious value, the value the plan uses.

    Minutes over truth are the danger: work planned that the truth did not allow.
    Minutes under truth are the cost of caution: work the truth allowed that the
    plan withheld.
    """
    hours = restricted = caught = missed = false_r = handed = lost = over = under = 0
    for members, truth in zip(members_by_hour, truth_by_hour):
        if not np.all(np.isfinite(members)) or not np.isfinite(truth):
            continue
        hours += 1
        f = plan_hour("", members, workload, acclimatized, plan_quantile=plan_quantile,
                      handover_steps=handover_steps)
        t = plan_hour("", [truth], workload, acclimatized)
        truth_minutes = t.minutes
        over += max(0, f.minutes - truth_minutes)
        under += max(0, truth_minutes - f.minutes)
        if f.outcome is Outcome.UNDETERMINED:
            handed += 1
            lost += max(0, truth_minutes - f.minutes)
        if truth_minutes < 60:
            restricted += 1
            if f.minutes <= truth_minutes:
                caught += 1
            else:
                missed += 1
        elif f.minutes < 60:
            false_r += 1
    return DecisionScore(hours, restricted, caught, missed, false_r, handed, lost, over, under)
