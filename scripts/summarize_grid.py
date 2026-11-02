"""Pool results/grid_scores.jsonl into one table per arm and lead, for the README.

With --region pk, pools results/pk/grid_scores.jsonl into results/pk/grid_summary.md, adds the workload,
a per-site table, and the pass or fail of each prediction in results/pk/PREREGISTRATION-PK.md.

Pooled over sites and init dates. A miss is a heat-restricted hour (truth allows
under 60 work minutes) that the arm planned as more work than the truth allows.
Hand-offs are undetermined hours, which the plan sends to the supervisor.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    if sys.argv[1:3] == ["--region", "pk"]:
        return main_pk()
    rows = [json.loads(line) for line in (ROOT / "results" / "grid_scores.jsonl").read_text().splitlines()]
    agg: dict[tuple, dict] = defaultdict(lambda: defaultdict(float))
    for r in rows:
        k = (r["arm"], r["acclimatized"], r["lead_days"])
        a = agg[k]
        a["n"] += r["n"]
        a["abs"] += r["mae_c"] * r["n"]
        a["bias"] += r["bias_c"] * r["n"]
        for f in ("restricted", "missed", "false_restrictions", "handed_over", "hours", "minutes_over", "minutes_under"):
            a[f] += r[f]
        a["inits"] = a.get("inits", set()) | {r["init"]}

    lines = [
        "# Gridded arms against ERA5, pooled over 5 sites",
        "",
        f"Run {date.today().isoformat()}. Workload heavy. 3-hourly valid times. Init dates from "
        "PREREGISTRATION.md. Working hours only (06, 09, 12, 15 UTC). Rules frozen in turno/rules.py.",
        "",
        "| Arm | Limit | Lead (days) | Inits | Times | WBGT MAE C | Bias C | Restricted | Missed | Miss rate | Handed over | Min over per time | Min withheld per time |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for (arm, accl, lead), a in sorted(agg.items()):
        miss = a["missed"] / a["restricted"] if a["restricted"] else 0.0
        hand = a["handed_over"] / a["hours"] if a["hours"] else 0.0
        lines.append(
            f"| {arm} | {'REL' if accl else 'RAL'} | {lead} | {len(a['inits'])} | {int(a['n'])} | "
            f"{a['abs'] / a['n']:.2f} | {a['bias'] / a['n']:+.2f} | {int(a['restricted'])} | {int(a['missed'])} | "
            f"{miss:.1%} | {hand:.1%} | {a['minutes_over'] / a['hours']:.2f} | {a['minutes_under'] / a['hours']:.2f} |"
        )
    out = ROOT / "results" / "grid_summary.md"
    out.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


def pool(rows, keyf):
    agg: dict[tuple, dict] = defaultdict(lambda: defaultdict(float))
    for r in rows:
        a = agg[keyf(r)]
        a["n"] += r["n"]
        a["abs"] += r["mae_c"] * r["n"]
        a["bias"] += r["bias_c"] * r["n"]
        for f in ("restricted", "missed", "false_restrictions", "handed_over", "hours", "minutes_over", "minutes_under"):
            a[f] += r[f]
        a["inits"] = a.get("inits", set()) | {r["init"]}
    return agg


def rate(a, num, den):
    return a[num] / a[den] if a[den] else float("nan")


def main_pk() -> int:
    rows = [json.loads(line) for line in (ROOT / "results" / "pk" / "grid_scores.jsonl").read_text().splitlines()]
    arms = {"oper": "ECMWF IFS (single)", "enfo": "ECMWF ENS + Turno rules"}
    by_lead = pool(rows, lambda r: (r["workload"], r["acclimatized"], r["arm"], r["lead_days"]))
    lines = [
        "# Pakistan: the frozen planner against ERA5, pooled over 5 sites",
        "",
        f"Run {date.today().isoformat()}. Pre-registration: `PREREGISTRATION-PK.md` (commit e824b49, before any data). "
        "Rules frozen from Italy (`turno/rules.py`). 3-hourly valid times inside working hours only "
        "(03, 06, 09, 12 UTC = 08, 11, 14, 17 PKT). A time is heat-restricted when the ERA5 truth allows under "
        "60 work minutes.",
        "",
        "## Predictions (heavy work, unacclimatized limit, leads 1 to 3)",
        "",
        "| Lead | IFS miss rate | ENS miss rate | Relative reduction | P1: at least 30% | ENS hand-off rate | P2: under 25% |",
        "|---|---|---|---|---|---|---|",
    ]
    for lead in (1, 2, 3):
        i = by_lead.get(("heavy", False, "oper", lead))
        e = by_lead.get(("heavy", False, "enfo", lead))
        if not i or not e:
            lines.append(f"| {lead} | missing | missing | | | | |")
            continue
        mi, me = rate(i, "missed", "restricted"), rate(e, "missed", "restricted")
        red = (mi - me) / mi if mi else float("nan")
        hand = rate(e, "handed_over", "hours")
        lines.append(f"| {lead} | {mi:.1%} | {me:.1%} | {red:.0%} | {'PASS' if red >= 0.30 else 'FAIL'} | "
                     f"{hand:.1%} | {'PASS' if hand < 0.25 else 'FAIL'} |")
    lines += [
        "",
        "## All arms, workloads, limits and leads",
        "",
        "| Workload | Limit | Arm | Lead (days) | Inits | Times | WBGT MAE C | Bias C | Restricted | Missed | Miss rate | Handed over | Min over per time | Min withheld per time |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for (wl, accl, arm, lead), a in sorted(by_lead.items()):
        lines.append(
            f"| {wl} | {'REL' if accl else 'RAL'} | {arms.get(arm, arm)} | {lead} | {len(a['inits'])} | {int(a['n'])} | "
            f"{a['abs'] / a['n']:.2f} | {a['bias'] / a['n']:+.2f} | {int(a['restricted'])} | {int(a['missed'])} | "
            f"{rate(a, 'missed', 'restricted'):.1%} | {rate(a, 'handed_over', 'hours'):.1%} | "
            f"{a['minutes_over'] / a['hours']:.2f} | {a['minutes_under'] / a['hours']:.2f} |")
    by_site = pool([r for r in rows if r["workload"] == "heavy" and not r["acclimatized"] and r["lead_days"] <= 3],
                   lambda r: (r["site"], r["arm"]))
    lines += [
        "",
        "## Per site (heavy work, unacclimatized, leads 1 to 3 pooled)",
        "",
        "| Site | Arm | Times | Restricted share | Missed | Miss rate | Handed over |",
        "|---|---|---|---|---|---|---|",
    ]
    for (site, arm), a in sorted(by_site.items()):
        lines.append(f"| {site} | {arms.get(arm, arm)} | {int(a['hours'])} | {rate(a, 'restricted', 'hours'):.1%} | "
                     f"{int(a['missed'])} | {rate(a, 'missed', 'restricted'):.1%} | {rate(a, 'handed_over', 'hours'):.1%} |")
    out = ROOT / "results" / "pk" / "grid_summary.md"
    out.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
