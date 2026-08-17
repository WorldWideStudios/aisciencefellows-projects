"""Bake 1-sentence overviews for each Pareto-frontier hypothesis narrative.

Reads workbench/pareto_frontier_narratives.json (the 22 Opus narratives from
bake_pareto_frontier_narratives.py) and asks Claude Haiku for a one-sentence
overview that captures the mechanism in plain clinician language — different
from the last-sentence "verdict" already in the narrative.

Adds a `summary` field to each entry and rewrites the file. Idempotent-safe:
skips entries that already have a summary.

Usage:
    ANTHROPIC_API_KEY=... ~/venv/bin/python -m prototype.ingest.bake_pareto_frontier_summaries
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO       = Path(__file__).resolve().parent.parent.parent
NARR_JSON  = REPO / "workbench" / "pareto_frontier_narratives.json"
MODEL      = os.environ.get("ANTHROPIC_SUMMARY_MODEL", "claude-haiku-4-5-20251001")
ENDPOINT   = "https://api.anthropic.com/v1/messages"


def call_summary(narrative: str, patient_id: str, hyp_id: str,
                 max_tokens: int = 150, timeout: int = 60) -> tuple[str, dict]:
    system = (
        "You distil rare-disease mechanism narratives into a single-sentence "
        "overview. The sentence must:\n"
        "  - Be ONE sentence, ≤ 32 words.\n"
        "  - Name the patient's variant OR the mechanism family.\n"
        "  - State the mechanism's central causal claim (variant → phenotype), "
        "    not just a verdict of credibility.\n"
        "  - Use clinician language; specific values (isoforms, tissues) where "
        "    they were named in the narrative.\n"
        "  - NO preamble like 'Summary:' or 'This narrative...'. Return the "
        "    sentence only."
    )
    body = {
        "model":      MODEL,
        "max_tokens": max_tokens,
        "system":     system,
        "messages":   [{
            "role": "user",
            "content": (
                f"Patient {patient_id} · Hypothesis H{hyp_id}\n\n"
                f"Narrative:\n{narrative}\n\n"
                f"Return the single-sentence overview."
            ),
        }],
    }
    req = urllib.request.Request(
        ENDPOINT, method="POST",
        headers={
            "x-api-key":         os.environ["ANTHROPIC_API_KEY"],
            "anthropic-version": "2023-06-01",
            "content-type":      "application/json",
        },
        data=json.dumps(body).encode(),
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        resp = json.load(r)
    text = resp["content"][0]["text"].strip()
    return text, resp.get("usage", {})


def main() -> None:
    print("=== Bake 1-sentence overviews for Pareto-frontier narratives ===\n")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set."); sys.exit(2)
    if not NARR_JSON.exists():
        print(f"ERROR: {NARR_JSON} not found — run bake_pareto_frontier_narratives.py first.")
        sys.exit(2)

    data = json.loads(NARR_JSON.read_text())
    todo = [k for k, v in data.items() if not v.get("summary")]
    print(f"Narratives: {len(data)} total · {len(todo)} need a summary\n")

    total_cost = 0.0
    for k in todo:
        v = data[k]
        print(f"[{k}] calling {MODEL}...", flush=True)
        try:
            summary, usage = call_summary(v["narrative"], v["patient_id"], v["hypothesis_id"])
        except (urllib.error.URLError, TimeoutError, KeyError, ValueError) as e:
            print(f"  FAILED: {type(e).__name__}: {e}")
            continue
        in_tok  = usage.get("input_tokens", 0)
        out_tok = usage.get("output_tokens", 0)
        # Haiku 4.5 pricing (Aug 2025): input $1/M, output $5/M
        cost = in_tok * 1 / 1e6 + out_tok * 5 / 1e6
        total_cost += cost
        v["summary"]         = summary
        v["summary_model"]   = MODEL
        v["summary_at"]      = datetime.now(timezone.utc).isoformat(timespec="seconds")
        v["summary_usage"]   = {"input_tokens": in_tok, "output_tokens": out_tok,
                                "cost_usd": round(cost, 5)}
        NARR_JSON.write_text(json.dumps(data, indent=2))
        print(f"  ✓ {len(summary.split())} words · {in_tok} in / {out_tok} out · ${cost:.5f}")
        print(f"    → {summary}")
        time.sleep(0.4)

    print(f"\nDone. {len(data)} entries · summary pass total: ${total_cost:.4f}")


if __name__ == "__main__":
    main()
