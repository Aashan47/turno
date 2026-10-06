"""NIOSH heat limits, turned into minutes of work per hour.

NIOSH 2016-106, section 8.1, verbatim:

    RAL [degrees C-WBGT] = 59.9 - 14.1 log10 M [W]
    REL [degrees C-WBGT] = 56.7 - 11.5 log10 M [W]

RAL is for unacclimatized workers, REL for acclimatized ones. "The estimates of
both environmental and metabolic heat are expressed as 1-hour time-weighted
averages (TWAs)", and the limits "take work/rest schedules into consideration so
are shown for 60, 45, 30, and 15 minute time periods". So the question for any
hour is: how many of its minutes can be spent working before the hour's average
metabolic rate exceeds what the WBGT allows? See SOURCES.md.

Two simplifications, both conservative, both stated:
- rest is assumed to happen at the same WBGT as work. Rest in shade is cooler,
  so the real allowance is never smaller than the one computed here;
- the answer is rounded down to NIOSH's own steps of 60, 45, 30, 15 and 0 minutes.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# NIOSH 2016-106 Table 5-1, NIOSH column, verbatim ranges.
RESTING_W = 117.0  # "Resting ... 100 kcal/h (117 W)"

STEPS_MINUTES = (60, 45, 30, 15, 0)


@dataclass(frozen=True)
class Workload:
    key: str
    label: str
    m_low_w: float
    m_high_w: float
    source: str


WORKLOADS = {
    "moderate": Workload(
        "moderate", "moderate work", 234.0, 349.0,
        "NIOSH 2016-106 Table 5-1: Moderate, 201-300 kcal/h (234-349 W)",
    ),
    "heavy": Workload(
        "heavy", "heavy work", 350.0, 465.0,
        "NIOSH 2016-106 Table 5-1: Heavy, 301-400 kcal/h (350-465 W)",
    ),
    "very_heavy": Workload(
        "very_heavy", "very heavy work", 466.0, 580.0,
        "NIOSH 2016-106 Table 5-1: Very heavy, 401-500 kcal/h (466-580 W)",
    ),
}


def rel_c(m_watts: float) -> float:
    if m_watts <= 0.0:
        raise ValueError("metabolic rate must be positive")
    return 56.7 - 11.5 * math.log10(m_watts)


def ral_c(m_watts: float) -> float:
    if m_watts <= 0.0:
        raise ValueError("metabolic rate must be positive")
    return 59.9 - 14.1 * math.log10(m_watts)


def allowed_twa_watts(wbgt_c: float, acclimatized: bool) -> float:
    """The largest 1-hour average metabolic rate the limit allows at this WBGT."""
    if acclimatized:
        return 10 ** ((56.7 - wbgt_c) / 11.5)
    return 10 ** ((59.9 - wbgt_c) / 14.1)


def work_minutes_exact(wbgt_c: float, m_work_w: float, acclimatized: bool) -> float:
    """Minutes of work in an hour such that the time-weighted average equals the limit."""
    m_allow = allowed_twa_watts(wbgt_c, acclimatized)
    if m_allow >= m_work_w:
        return 60.0
    if m_allow <= RESTING_W:
        return 0.0
    return 60.0 * (m_allow - RESTING_W) / (m_work_w - RESTING_W)


def snap_down(minutes: float) -> int:
    """Round down to NIOSH's steps, never up."""
    for step in STEPS_MINUTES:
        if minutes + 1e-9 >= step:
            return step
    return 0


@dataclass(frozen=True)
class MinutesBand:
    """Allowed work minutes for one hour, as a band over the workload range.

    The harder end of the workload gives fewer minutes. If the two ends snap to
    the same step, the answer is determined by the forecast alone. If they do
    not, it depends on how hard the crew actually works, which no forecast knows.
    """

    fewest: int
    most: int

    @property
    def determined(self) -> bool:
        return self.fewest == self.most


def minutes_band(wbgt_c: float, workload: Workload | str, acclimatized: bool) -> MinutesBand:
    if isinstance(workload, str):
        workload = WORKLOADS[workload]
    fewest = snap_down(work_minutes_exact(wbgt_c, workload.m_high_w, acclimatized))
    most = snap_down(work_minutes_exact(wbgt_c, workload.m_low_w, acclimatized))
    return MinutesBand(fewest=fewest, most=most)
