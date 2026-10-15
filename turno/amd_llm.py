"""Calls to models served on AMD GPUs through AMD Token Factory.

Token Factory is AMD Radeon Cloud's model API, the AMD infrastructure this
hackathon provides: OpenAI-compatible endpoints running on AMD GPUs. One team
key, shared limits (20 requests a minute and a daily spend cap at the time of
writing), so every call goes through here: one place for backoff on 429, and one
log of every call's model, latency, tokens and cost, which is the evidence the
README reports.

The key is read from the environment (TOKEN_FACTORY_KEY or token_factory_key)
and never written anywhere. Prompts are logged by the provider for about two
days, so only public data is ever sent: weather, ordinance text, plans.
"""

from __future__ import annotations

import json
import os
import random
import time
from dataclasses import dataclass, field
from pathlib import Path

import httpx

BASE_URL = "https://developer.amd.com.cn/radeon/api/v1"
DEFAULT_MODEL = "DeepSeek-V4-Flash"
LOG = Path(__file__).resolve().parent.parent / "results" / "amd_calls.jsonl"


def api_key() -> str:
    for name in ("TOKEN_FACTORY_KEY", "token_factory_key"):
        v = os.environ.get(name)
        if v:
            return v.strip().strip('"').strip("'")
    env = Path(__file__).resolve().parents[5] / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            k, _, v = line.partition("=")
            if k.strip().lower().removeprefix("export ").strip() == "token_factory_key" and v:
                return v.strip().strip('"').strip("'")
    raise RuntimeError("no Token Factory key: set TOKEN_FACTORY_KEY")


@dataclass
class Reply:
    text: str
    model: str
    latency_s: float
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    raw: dict = field(repr=False, default_factory=dict)


def chat(
    messages: list[dict],
    model: str = DEFAULT_MODEL,
    max_tokens: int = 1024,
    json_mode: bool = False,
    temperature: float = 0.0,
    task: str = "",
    retries: int = 6,
) -> Reply:
    """One chat completion, retried only on 429 and 5xx, with backoff and jitter."""
    body: dict = {"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": temperature}
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    headers = {"Authorization": f"Bearer {api_key()}", "Content-Type": "application/json"}
    delay = 2.0
    for attempt in range(retries):
        t0 = time.perf_counter()
        r = httpx.post(f"{BASE_URL}/chat/completions", json=body, headers=headers, timeout=600)
        dt = time.perf_counter() - t0
        if r.status_code == 429 or r.status_code >= 500:
            wait = float(r.headers.get("retry-after", delay)) + random.uniform(0, 1)
            time.sleep(min(wait, 90))
            delay *= 2
            continue
        r.raise_for_status()
        d = r.json()
        u = d.get("usage") or {}
        reply = Reply(
            text=d["choices"][0]["message"].get("content") or "",
            model=model,
            latency_s=round(dt, 3),
            prompt_tokens=int(u.get("prompt_tokens") or 0),
            completion_tokens=int(u.get("completion_tokens") or 0),
            cost_usd=float(u.get("cost") or 0.0),
            raw=d,
        )
        _log(reply, task)
        return reply
    raise RuntimeError(f"Token Factory still rate-limited after {retries} attempts")


def _log(r: Reply, task: str) -> None:
    LOG.parent.mkdir(exist_ok=True)
    with LOG.open("a") as f:
        f.write(json.dumps({
            "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "task": task, "model": r.model,
            "latency_s": r.latency_s, "prompt_tokens": r.prompt_tokens,
            "completion_tokens": r.completion_tokens, "cost_usd": r.cost_usd,
        }) + "\n")
