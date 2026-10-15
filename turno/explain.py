"""Why an hour went to the supervisor, in plain words, written on AMD.

When forecast members disagree by two work steps or more, the hour is handed to
the site supervisor. A chat model on AMD Token Factory explains the situation in
two sentences, Italian and English. Like the briefing, it may only use numbers
that are in the hour's plan; otherwise its text is dropped and the plan's own
reasons are shown.
"""

from __future__ import annotations

import json

from .amd_llm import chat
from .briefing import check

SYSTEM = (
    "You explain to a construction site supervisor why one hour of today's heat plan needs their decision. "
    "Use only the numbers in the JSON, written exactly as they appear. The plan follows the hottest "
    "forecast member, given as plan_assumes_wbgt_c, and allows work_minutes. Say what the members disagree "
    "about or what must be confirmed (read the reasons), what the plan assumes meanwhile, and one thing "
    "the supervisor can check on site, such as cloud cover, shade or the crew's pace. Never state a "
    "threshold, limit or rule that is not in the JSON. Two sentences in Italian under ITALIANO, then two "
    "in English under ENGLISH."
)


def explain(hour: dict, site: str, day: str) -> dict:
    hour = dict(hour, plan_assumes_wbgt_c=hour.get("wbgt_c", {}).get("max"))
    payload = {"site": site, "date": day, "hours": [hour]}
    r = chat([{"role": "system", "content": SYSTEM},
              {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
             max_tokens=400, task="explain_handover")
    problems = check(r.text, payload)
    return {"text": r.text if not problems else None, "problems": problems, "model": r.model,
            "runs_on": "AMD Token Factory (AMD Radeon Cloud)", "latency_s": r.latency_s,
            "fallback": " ".join(hour.get("reasons", [])) if problems else None}
