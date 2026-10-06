"""Pool results/grid_scores.jsonl into one table per arm and lead, for the README.

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
    rows = [json.loads(line) for line in (ROOT / "results" / "grid_scores.jsonl").read_text().splitlines()]
    agg: dict[tuple, dict] = defaultdict(lambda: defaultdict(float))
    for r in rows:
        k = (r["arm"], r["acclimatized"], r["lead_days"])
        a = agg[k]
        a["n"] += r["n"]
        a["abs"] += r["mae_c"] * r["n"]
        a["bias"] += r["bias_c"] * r["n"]
        for f in ("restricted", "missed", "false_restrictions", "handed_over", "hours"):
            a[f] += r[f]
        a["inits"] = a.get("inits", set()) | {r["init"]}

    lines = [
        "# Gridded arms against ERA5, pooled over 5 sites",
        "",
        f"Run {date.today().isoformat()}. Workload heavy. 3-hourly valid times. Init dates from "
        "PREREGISTRATION.md.",
        "",
        "| Arm | Limit | Lead (days) | Inits | Times | WBGT MAE C | Bias C | Restricted | Missed | Miss rate | Handed over |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for (arm, accl, lead), a in sorted(agg.items()):
        miss = a["missed"] / a["restricted"] if a["restricted"] else 0.0
        hand = a["handed_over"] / a["hours"] if a["hours"] else 0.0
        lines.append(
            f"| {arm} | {'REL' if accl else 'RAL'} | {lead} | {len(a['inits'])} | {int(a['n'])} | "
            f"{a['abs'] / a['n']:.2f} | {a['bias'] / a['n']:+.2f} | {int(a['restricted'])} | {int(a['missed'])} | "
            f"{miss:.1%} | {hand:.1%} |"
        )
    out = ROOT / "results" / "grid_summary.md"
    out.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
