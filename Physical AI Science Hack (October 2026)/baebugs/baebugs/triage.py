"""Unknown vs novel triage -> human-intervention alerts.

Two different reasons a person should look at a detection:

* UNKNOWN - the system does not know WHAT it is: low detector confidence,
  the two sizers disagree, no consensus partner, or the mask is implausible.
  Action: a human labels it (it becomes training data). Priority: normal.

* NOVEL - the system is confident it IS a specimen, but its size/shape sits
  outside everything in the reference database (k-NN density vs the database's
  own spread), or its taxon is on the Essig collection-gap list.
  Action: a human checks a possibly interesting find before it is sieved,
  picked or damaged. Priority: VIP.

KNOWN - confident and in-distribution: no alert, proceed automatically.

Unknown is checked first: a low-confidence outlier is an unknown, not a VIP
(we don't escalate what we can't recognise).
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

from .novelty import novel_sizes


@dataclass
class Alert:
    status: str                  # known | unknown | novel
    priority: str                # none | normal | VIP
    reasons: list[str] = field(default_factory=list)
    length_mm: float = 0.0
    width_mm: float = 0.0
    conf: float = 0.0
    novelty: float = 0.0
    image: str | None = None
    cx: float = 0.0
    cy: float = 0.0
    sample_id: str | None = None
    t: float = field(default_factory=time.time)


def reference_from_truth(*truth_jsons):
    """Reference size distribution from truth files (synthetic truth and the
    ruler-scaled real 'silver' truth)."""
    L, W = [], []
    for tj in truth_jsons:
        p = Path(tj)
        if not p.exists():
            continue
        for rec in json.loads(p.read_text()):
            for o in rec["objects"]:
                L.append(o["length_mm"]); W.append(o["width_mm"])
    return np.asarray(L), np.asarray(W)


def triage(measurements, ref_L, ref_W, conf_min=0.45, gap_taxa_hit=False,
           length_range=(1.0, 30.0), image=None, sample_id=None, k=8, pct=99.0):
    ms = list(measurements)
    if not ms:
        return []
    nov = novel_sizes([m.length_mm for m in ms], [m.width_mm for m in ms],
                      ref_L, ref_W, k=k, pct=pct) if len(ref_L) > k else \
        [{"novel": False, "novelty": 0.0}] * len(ms)
    out = []
    for m, n in zip(ms, nov):
        unk = []
        if m.conf < conf_min:
            unk.append(f"low confidence {m.conf:.2f}")
        if m.flag and "disagree" in m.flag:
            unk.append(f"sizers disagree ({m.flag})")
        if m.flag and m.flag.startswith("only_"):
            unk.append(f"seen by one model only ({m.flag[5:]})")
        if m.width_mm > m.length_mm * 1.05 or m.length_mm <= 0:
            unk.append("implausible geometry")
        novel = []
        if n["novel"]:
            novel.append(f"size/shape outside database (novelty {n['novelty']:.2f})")
        if not (length_range[0] <= m.length_mm <= length_range[1]):
            novel.append(f"length {m.length_mm:.1f} mm outside {length_range[0]}-{length_range[1]} mm")
        if gap_taxa_hit:
            novel.append("taxon on Essig collection-gap list")
        if unk:
            status, prio, reasons = "unknown", "normal", unk + novel
        elif novel:
            status, prio, reasons = "novel", "VIP", novel
        else:
            status, prio, reasons = "known", "none", []
        out.append(Alert(status, prio, reasons, round(m.length_mm, 3), round(m.width_mm, 3),
                         round(float(m.conf), 3), round(float(n["novelty"]), 3), image,
                         round(m.cx, 1), round(m.cy, 1), sample_id))
    return out


def write_alerts(alerts, path):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a") as f:
        for a in alerts:
            if a.status != "known":
                f.write(json.dumps(asdict(a)) + "\n")
    return p


def summarize(alerts):
    s = {"known": 0, "unknown": 0, "novel": 0}
    for a in alerts:
        s[a.status] += 1
    s["vip"] = s["novel"]
    return s
