"""Step-by-step approval with an escalation ladder, and Markov statistics over the custody chain.

For every specimen at every step (sort -> disperse -> image -> pick -> lyse -> incubate -> sequence) a snapshot
frame is taken (baebugs.tiers: pixels -> tiles -> groups -> objects -> frame, all Merkle-hashed). The specimen's
object node is then judged by a LADDER of deciders, cheapest first:

  rung 1  taxon model   per-order / per-family preprocessor (DAISY-BB-004), only where its verdict and scope allow
  rung 2  local vision  small local VLM (Ollama, e.g. qwen2.5vl:3b)
  rung 3  frontier      Claude
  rung 4  human         entomologist; always decides

A rung decides only if (a) it is admitted for this taxon and place, (b) its confidence >= the rung threshold and
(c) the specimen's novelty is below the rung's novelty ceiling. Otherwise it ESCALATES. Every attempt is a custody
record: input hash (object node), decider id (weights tensor sha or model digest), output, hash of output.
The specimen moves to the next step only when the decision is APPROVE; REWORK sends it back, HOLD parks it.

Markov statistics are computed FROM THE CHAIN, never kept separately: states are (step, outcome); transitions are
counted per filter, protocol and novelty band, giving P(next | state, context) with Wilson intervals, plus where on
the ladder each family gets decided. Recompute the chain and you recompute the statistics.
"""
from __future__ import annotations

import hashlib
import json
import math
from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from itertools import pairwise
from pathlib import Path

from .mmr import MMRLog

STEPS = ["sort", "disperse", "image", "pick", "lyse", "incubate", "sequence"]
OUTCOMES = ("APPROVE", "REWORK", "HOLD")


def H(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


@dataclass
class Rung:
    name: str                       # "taxon:ORDER", "local:qwen2.5vl:3b", "frontier:claude", "human"
    decider_id: str                 # weights tensor sha / model digest / person role
    decide: Callable[[dict], dict]  # obj context -> {"outcome", "confidence", "label", ...}
    threshold: float = 0.8
    novelty_ceiling: float = 1.0    # rung refuses specimens whose novelty percentile is above this
    scope: dict = field(default_factory=dict)   # e.g. {"orders": [...], "states": ["CA"]}

    def admitted(self, ctx):
        s = self.scope
        if s.get("orders") and ctx.get("order") not in s["orders"]:
            return False, "order out of scope"
        if s.get("states") and ctx.get("state") not in s["states"]:
            return False, "place out of scope"
        if ctx.get("novelty", 0.0) > self.novelty_ceiling:
            return False, "too novel for this rung"
        return True, None


def climb(ladder, ctx):
    """Run the ladder for one specimen at one step. Returns (decision, attempts)."""
    attempts = []
    for k, r in enumerate(ladder):
        ok, why = r.admitted(ctx)
        if not ok:
            attempts.append({"rung": k + 1, "name": r.name, "decider": r.decider_id, "result": "SKIP", "why": why})
            continue
        out = r.decide(ctx)
        conf = float(out.get("confidence", 0.0))
        final = r.name == "human" or conf >= r.threshold
        attempts.append({"rung": k + 1, "name": r.name, "decider": r.decider_id, "result": "DECIDE" if final else "ESCALATE",
                         "confidence": round(conf, 4), "output_sha256": H(out), "output": out})
        if final:
            return {"outcome": out["outcome"], "decided_by": r.name, "rung": k + 1, "label": out.get("label")}, attempts
    raise RuntimeError("ladder has no human rung")


def novelty_band(x):
    return "low" if x < 0.9 else "high" if x < 0.99 else "novel"


def record_step(log: MMRLog, specimen, step, frame_summary, obj, ctx, ladder):
    """Snapshot + ladder decision for one specimen at one step, appended to the custody chain."""
    decision, attempts = climb(ladder, {**ctx, "object": obj})
    prev = next((r["leaf"] for r in reversed(log.records) if r["record"].get("specimen") == specimen), None)
    rec = {"type": "step", "specimen": specimen, "step": step, "frame_root": frame_summary["root"],
           "image_raw_sha256": frame_summary["image_raw_sha256"], "object_hash": obj["hash"], "bbox": obj["bbox"],
           "filter": ctx.get("filter"), "protocol": ctx.get("protocol"), "module": ctx.get("module"),
           "order": ctx.get("order"), "family": ctx.get("family"), "novelty": round(float(ctx.get("novelty", 0.0)), 4),
           "novelty_band": novelty_band(float(ctx.get("novelty", 0.0))), "attempts": attempts, "decision": decision,
           "prev_specimen_leaf": prev}
    return log.append(rec), decision


def _wilson(k, n, z=1.96):
    if n == 0:
        return [0.0, 1.0]
    p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d; w = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(max(0.0, c - w), 4), round(min(1.0, c + w), 4)]


def markov(records, by=("filter", "protocol", "novelty_band")):
    """Transition statistics from the chain. State = step:outcome; next = the same specimen's next record."""
    per = defaultdict(list)
    for r in records:
        x = r.get("record", r)
        if x.get("type") == "step":
            per[x["specimen"]].append(x)
    trans = defaultdict(Counter)
    for xs in per.values():
        for a, b in pairwise(xs):
            ctx = tuple(f"{k}={a.get(k)}" for k in by)
            trans[(f"{a['step']}:{a['decision']['outcome']}",) + ctx][f"{b['step']}:{b['decision']['outcome']}"] += 1
        last = xs[-1]
        ctx = tuple(f"{k}={last.get(k)}" for k in by)
        trans[(f"{last['step']}:{last['decision']['outcome']}",) + ctx]["END"] += 1
    table = []
    for key, c in sorted(trans.items()):
        n = sum(c.values())
        for nxt, k in sorted(c.items()):
            table.append({"from": key[0], "context": list(key[1:]), "to": nxt, "n": k, "of": n,
                          "p": round(k / n, 4), "ci95": _wilson(k, n)})
    # where on the ladder decisions happen, per family
    rungs = defaultdict(Counter)
    approve = defaultdict(Counter)
    for xs in per.values():
        for x in xs:
            rungs[x.get("family") or x.get("order") or "?"][x["decision"]["decided_by"]] += 1
            approve[(x["step"], x.get("filter"), x.get("protocol"))][x["decision"]["outcome"]] += 1
    gate = [{"step": s, "filter": f, "protocol": p, **dict(c), "n": sum(c.values()),
             "p_approve": round(c["APPROVE"] / sum(c.values()), 4), "ci95": _wilson(c["APPROVE"], sum(c.values()))}
            for (s, f, p), c in sorted(approve.items(), key=lambda kv: tuple(map(str, kv[0])))]
    out = {"transitions": table, "decided_by": {k: dict(v) for k, v in sorted(rungs.items())}, "approval_by_step": gate,
           "specimens": len(per), "records": sum(len(v) for v in per.values())}
    out["stats_sha256"] = H(out)
    return out


def run_specimen(log, specimen, frames_by_step, ctx_by_step, ladder):
    """Walk one specimen through the steps; REWORK repeats the step (frames may supply a retry), HOLD stops."""
    path = []
    for step in STEPS:
        if step not in frames_by_step:
            continue
        for attempt, (fs, obj) in enumerate(frames_by_step[step]):
            _row, dec = record_step(log, specimen, step, fs, obj, ctx_by_step[step][attempt], ladder)
            path.append((step, dec["outcome"], dec["decided_by"]))
            if dec["outcome"] != "REWORK":
                break
        if dec["outcome"] != "APPROVE":
            break
    return path


def load(path):
    return MMRLog(Path(path)).records
