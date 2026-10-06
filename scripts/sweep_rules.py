"""Choose Turno's two decision settings on the June development dates only.

Selection rule, written before the sweep was run (Amendment 2): among settings
whose hand-off rate is at most 25% of working-hour times, pick the lowest miss
rate on heat-restricted times; break ties by fewer minutes withheld from safe
work. Pooled over 5 sites, leads 1 to 3 days, unacclimatized limit (RAL), on the
ECMWF ENS arm. July and August dates are never read here: they are the test set.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from score_grid import load_truth, score_files  # noqa: E402

DEV_DATES = ["20260603", "20260610", "20260617", "20260624"]
QUANTILES = [0.5, 0.7, 0.8, 0.9, 1.0]
HANDOVER = [1, 2, 3, 99]
MAX_HANDOFF = 0.25


def main() -> int:
    truth, cells = load_truth()
    paths = [ROOT / "data" / "ecmwf" / f"enfo_{d}00.nc" for d in DEV_DATES]
    lines = [
        "# Rule sweep on the June development dates (ECMWF ENS, 10 members)",
        "",
        "Leads 1 to 3, RAL, working hours, pooled over 5 sites and 4 dates. July and August untouched.",
        "",
        "| Plan quantile | Hand over at steps apart | Restricted | Miss rate | Hand-off rate | Minutes withheld per time | Minutes over per time |",
        "|---|---|---|---|---|---|---|",
    ]
    results = []
    for q in QUANTILES:
        for h in HANDOVER:
            rows = [r for r in score_files(paths, truth, cells, q, h)
                    if not r["acclimatized"] and r["lead_days"] <= 3]
            restricted = sum(r["restricted"] for r in rows)
            missed = sum(r["missed"] for r in rows)
            hours = sum(r["hours"] for r in rows)
            handed = sum(r["handed_over"] for r in rows)
            under = sum(r["minutes_under"] for r in rows)
            over = sum(r["minutes_over"] for r in rows)
            res = (q, h, restricted, missed / restricted, handed / hours, under / hours, over / hours)
            results.append(res)
            hlabel = "never" if h == 99 else str(h)
            lines.append(f"| {q} | {hlabel} | {restricted} | {res[3]:.1%} | {res[4]:.1%} | {res[5]:.2f} | {res[6]:.2f} |")
    eligible = [r for r in results if r[4] <= MAX_HANDOFF]
    best = min(eligible, key=lambda r: (r[3], r[5]))
    lines += ["", f"**Chosen by the rule:** plan quantile {best[0]}, hand over at "
              f"{'never' if best[1] == 99 else best[1]} steps apart (miss {best[3]:.1%}, hand-off {best[4]:.1%})."]
    out = ROOT / "results" / "rule_sweep_june.md"
    out.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
