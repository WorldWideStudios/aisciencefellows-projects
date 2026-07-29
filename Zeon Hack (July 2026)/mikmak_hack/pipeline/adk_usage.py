"""What the agent layer costs: token usage read out of ADK's own session store.

`adk web` persists every model call to `pipeline/agents/<agent>/.adk/session.db`
(SQLite), and each event carries a `usage_metadata` block with real token counts.
So the cost of driving this pipeline conversationally is measured, not estimated
from message counts.

Cost = tokens x rate, and **the rates are the one thing here that isn't measured**.
They are published list prices that change; `RATES_USD_PER_MTOK` is a plain dict,
dated, meant to be edited. Token counts stay correct regardless — if a rate is
stale, the tokens are still exactly what was spent, which is why the dashboard
leads with tokens and treats dollars as derived.
"""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = PROJECT_ROOT / "pipeline" / "agents"

# USD per million tokens. VERIFY against current pricing before quoting these
# numbers to anyone — they are list prices noted 2026-07, not a live feed.
# `cached` is the discounted rate for prompt tokens served from context cache;
# `output` covers both response and thinking tokens, which bill the same.
RATES_USD_PER_MTOK: dict[str, dict[str, float]] = {
    "gemini-2.5-flash": {"input": 0.30, "cached": 0.075, "output": 2.50},
    "gemini-2.5-pro":   {"input": 1.25, "cached": 0.3125, "output": 10.00},
}
DEFAULT_RATE_KEY = "gemini-2.5-flash"

# Override without editing code: PIPELINE_RATES='{"gemini-2.5-flash":{...}}'
if os.environ.get("PIPELINE_RATES"):
    try:
        RATES_USD_PER_MTOK.update(json.loads(os.environ["PIPELINE_RATES"]))
    except json.JSONDecodeError:
        pass


def _rate_for(model: str) -> dict[str, float]:
    """Longest-prefix match, so 'gemini-2.5-flash-001' bills as 'gemini-2.5-flash'."""
    for key in sorted(RATES_USD_PER_MTOK, key=len, reverse=True):
        if model and model.startswith(key):
            return RATES_USD_PER_MTOK[key]
    return RATES_USD_PER_MTOK[DEFAULT_RATE_KEY]


def session_dbs() -> list[Path]:
    return sorted(AGENTS_DIR.glob("*/.adk/session.db"))


def _cost(prompt: int, cached: int, output: int, model: str) -> float:
    r = _rate_for(model)
    # Cached tokens are a *subset* of prompt tokens, billed at the lower rate.
    fresh = max(prompt - cached, 0)
    return (fresh * r["input"] + cached * r["cached"] + output * r["output"]) / 1_000_000


def read_events(db: Path) -> list[dict]:
    """One record per model call that reported usage."""
    out: list[dict] = []
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        rows = con.execute(
            "select session_id, invocation_id, timestamp, event_data from events"
        ).fetchall()
    except sqlite3.DatabaseError:
        return out
    finally:
        con.close()

    for session_id, invocation_id, ts, blob in rows:
        try:
            d = json.loads(blob)
        except (TypeError, json.JSONDecodeError):
            continue
        usage = d.get("usage_metadata") or d.get("usageMetadata")
        if not usage:
            continue
        prompt = usage.get("prompt_token_count", 0) or 0
        cached = usage.get("cached_content_token_count", 0) or 0
        thoughts = usage.get("thoughts_token_count", 0) or 0
        candidates = usage.get("candidates_token_count", 0) or 0
        # Billable input that is NOT inside prompt_token_count: the tokens spent
        # describing tools to the model. This pipeline hands its agents 7-12 tools
        # each, so leaving it out understates the input side.
        tool_prompt = usage.get("tool_use_prompt_token_count", 0) or 0
        model = d.get("model_version") or ""
        out.append({
            "agent": db.parent.parent.name,
            "session_id": session_id,
            "invocation_id": invocation_id,
            "timestamp": ts,
            "author": d.get("author") or "",
            "model": model,
            "prompt": prompt,
            "cached": cached,
            "thoughts": thoughts,
            "candidates": candidates,
            "tool_prompt": tool_prompt,
            # `traffic_type` distinguishes on-demand from provisioned throughput.
            # Under provisioned capacity these rates don't apply at all, so surface
            # it rather than silently billing pay-as-you-go prices.
            "traffic_type": usage.get("traffic_type") or "",
            "total": usage.get("total_token_count", prompt + thoughts + candidates) or 0,
            "cost_usd": _cost(prompt + tool_prompt, cached, thoughts + candidates, model),
        })
    return out


def all_events() -> list[dict]:
    events: list[dict] = []
    for db in session_dbs():
        events.extend(read_events(db))
    events.sort(key=lambda e: e["timestamp"] or 0)
    return events


def summarize(events: list[dict] | None = None) -> dict:
    """Totals plus per-agent and per-model breakdowns, for the dashboard."""
    events = all_events() if events is None else events
    tot = {
        "calls": len(events),
        "prompt": sum(e["prompt"] for e in events),
        "cached": sum(e["cached"] for e in events),
        "thoughts": sum(e["thoughts"] for e in events),
        "candidates": sum(e["candidates"] for e in events),
        "tool_prompt": sum(e["tool_prompt"] for e in events),
        "total": sum(e["total"] for e in events),
        "cost_usd": sum(e["cost_usd"] for e in events),
        "sessions": len({(e["agent"], e["session_id"]) for e in events}),
    }
    traffic = sorted({e["traffic_type"] for e in events if e["traffic_type"]})

    def group(key: str) -> list[dict]:
        acc: dict[str, dict] = {}
        for e in events:
            k = e[key] or "(unknown)"
            a = acc.setdefault(k, {key: k, "calls": 0, "total": 0, "cost_usd": 0.0})
            a["calls"] += 1
            a["total"] += e["total"]
            a["cost_usd"] += e["cost_usd"]
        return sorted(acc.values(), key=lambda r: -r["total"])

    return {
        "totals": tot,
        "by_agent": group("author"),
        "by_model": group("model"),
        "rates": RATES_USD_PER_MTOK,
        "traffic_types": traffic,
        # Stated, not implied: the API returns tokens only. Every dollar figure on
        # the dashboard is tokens x a hand-maintained rate table.
        "cost_basis": "computed locally — the Gemini API/ADK return token counts, never prices",
        # A prompt token served from cache is billed at the lower rate; showing the
        # share makes it obvious when a long conversation is mostly re-sent context.
        "cache_hit_rate": (tot["cached"] / tot["prompt"]) if tot["prompt"] else 0.0,
    }


if __name__ == "__main__":
    s = summarize()
    t = s["totals"]
    print(f"{t['calls']} model call(s) across {t['sessions']} session(s)")
    print(f"  prompt     {t['prompt']:>10,}  (cached {t['cached']:,} = {s['cache_hit_rate']:.0%})")
    print(f"  thinking   {t['thoughts']:>10,}")
    print(f"  output     {t['candidates']:>10,}")
    print(f"  TOTAL      {t['total']:>10,}")
    print(f"  est. cost  ${t['cost_usd']:>9.4f}   (rates: list prices noted 2026-07 — verify)")
    for row in s["by_agent"]:
        print(f"    {row['author']:<22} {row['total']:>8,} tok  ${row['cost_usd']:.4f}  ({row['calls']} calls)")
