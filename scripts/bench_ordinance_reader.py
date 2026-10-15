"""Benchmark the ordinance reader against the verified 2026 records.

Source per region: MinerU2.5-Pro OCR on AMD of the region's own PDF where the
URL is a single signed ordinance; otherwise the primary text saved in
sources/ordinances/ (bulletins and web pages). Reference: data/ordinances_2026.json.

Scored only where one document holds the whole rule. Regions whose 2026 rule
was built from several acts (Lazio, Campania, Sicilia, Sardegna, Veneto) are run
and reported separately: there the question is whether the reader flags the act
as amending or extending, not whether one document's dates match the season's.

The safety number is "accepted and wrong": a field the checks let through that
disagrees with the reference. Everything the checks reject goes to a person.
Output: results/ordinance_reader.md and .json.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from turno.ordinance_reader import read, ocr_pdf  # noqa: E402

OCR_REGIONS = {"Liguria", "Lombardia", "Puglia", "Sicilia", "Calabria", "Sardegna", "Umbria"}
MULTI_ACT = {"Lazio", "Campania", "Sicilia", "Sardegna", "Veneto"}
SCORED = ("valid_to", "ban_start", "ban_end")


def main() -> int:
    recs = json.loads((ROOT / "data" / "ordinances_2026.json").read_text())
    seen, rows = set(), []
    for r in recs:
        region = r["region"]
        if region in seen or r["status"] != "VERIFIED_PRIMARY":
            continue
        seen.add(region)
        key = region.lower().replace("-", "")
        if region in OCR_REGIONS and r.get("url", "").startswith("http"):
            text, source = ocr_pdf(r["url"], key), "MinerU2.5-Pro OCR on AMD of the region's PDF"
        else:
            text, source = (ROOT / "sources" / "ordinances" / f"{region.lower()}-2026.txt").read_text(), "saved primary text"
        rd = read(region, text)
        row = {"region": region, "source": source, "multi_act": region in MULTI_ACT, "model": rd.model,
               "latency_s": rd.latency_s, "cost_usd": rd.cost_usd, "amends_flag": rd.amends, "fields": {}}
        for n, c in rd.checks.items():
            ref = r.get(n) if n in SCORED else None
            row["fields"][n] = {"value": c.value, "accepted": c.accepted, "reason": c.reason,
                                "reference": ref, "matches_reference": (str(c.value) == str(ref)) if ref else None}
        rows.append(row)
        print(region, {n: ("OK" if f["accepted"] else "REV") for n, f in row["fields"].items()}, flush=True)

    (ROOT / "results" / "ordinance_reader.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False))
    single = [x for x in rows if not x["multi_act"]]
    lines = ["# Ordinance reader against the verified 2026 records", "",
             f"Run {date.today().isoformat()}. Model {rows[0]['model'] if rows else ''} on AMD Token Factory. "
             f"{len(single)} single-act regions scored on {', '.join(SCORED)}; {len(rows) - len(single)} multi-act "
             "regions reported for amendment detection.", "",
             "| Field | Accepted | Accepted and correct | **Accepted and wrong** | Sent to a person |",
             "|---|---|---|---|---|"]
    for n in SCORED:
        acc = [x["fields"][n] for x in single if x["fields"][n]["accepted"]]
        ok = sum(1 for f in acc if f["matches_reference"])
        lines.append(f"| {n} | {len(acc)} | {ok} | **{len(acc) - ok}** | {len(single) - len(acc)} |")
    lines += ["", "| Region | Source | Multi-act | Flags amendment | Fields sent to a person | Latency s |",
              "|---|---|---|---|---|---|"]
    for x in rows:
        rev = [n for n, f in x["fields"].items() if not f["accepted"]]
        lines.append(f"| {x['region']} | {x['source']} | {'yes' if x['multi_act'] else 'no'} | {x['amends_flag']} | "
                     f"{', '.join(rev) or 'none'} | {x['latency_s']} |")
    (ROOT / "results" / "ordinance_reader.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
