#!/usr/bin/env python3
"""Build data/screens/2/v5 from v4 — same compounds/concentrations, column-strip layout."""

from __future__ import annotations

import copy
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from pvjthomas.plates import (  # noqa: E402
    DEFAULT_POSITIVE_CONTROL_COMPOUND_ID,
    generate_plate_map_from_file,
    sample_compounds_excluding_positive_control,
    DEFAULT_CONTROL_ROW,
)

V4 = REPO / "data/screens/2/v4"
V5 = REPO / "data/screens/2/v5"
RUNS = REPO / "pvjthomas/runs/2/v5"


POSITIVE_CONTROL_COMPOUND_ID = DEFAULT_POSITIVE_CONTROL_COMPOUND_ID


def _drop_positive_from_samples(compound_list: dict) -> None:
    """Remove clavulanic acid from discovery list; it remains the plate positive control."""
    samples, _excluded = sample_compounds_excluding_positive_control(
        compound_list["compounds"],
        control_row=DEFAULT_CONTROL_ROW,
    )
    compound_list["compounds"] = samples
    for i, c in enumerate(compound_list["compounds"], start=1):
        c["slot"] = i
    compound_list["compound_count"] = len(compound_list["compounds"])


def main() -> int:
    v4_list = json.loads((V4 / "compound_list.json").read_text())
    v5_list = copy.deepcopy(v4_list)
    _drop_positive_from_samples(v5_list)
    v5_list.update(
        {
            "version": 5,
            "version_label": "r2-discovery-v5",
            "supersedes": "data/screens/2/v4/compound_list.json",
            "rationale_doc": "pvjthomas/runs/2/v5/selection_rationale.md",
            "layout": "column_strip",
            "note": (
                "9 discovery compounds (T19860 clavulanic acid is positive control only); "
                "v5 column-strip layout (triplicates on rows B/D/F per compound)."
            ),
        }
    )

    V5.mkdir(parents=True, exist_ok=True)
    RUNS.mkdir(parents=True, exist_ok=True)

    compound_path = V5 / "compound_list.json"
    compound_path.write_text(json.dumps(v5_list, indent=2) + "\n")

    with (V4 / "compound_list.csv").open(newline="") as f_in, (V5 / "compound_list.csv").open(
        "w", newline=""
    ) as f_out:
        reader = csv.DictReader(f_in)
        rows = [r for r in reader if r["compound_id"] != POSITIVE_CONTROL_COMPOUND_ID]
        for i, row in enumerate(rows, start=1):
            row["slot"] = str(i)
        writer = csv.DictWriter(f_out, fieldnames=reader.fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    plate_path = generate_plate_map_from_file(compound_path, V5 / "plate_map.json")

    manifest = {
        "run": 2,
        "round": 2,
        "version": 5,
        "label": "r2-discovery-v5",
        "created_at": datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%dT%H:%M:%S%z"),
        "author": "pvjthomas",
        "status": "pending_signoff",
        "supersedes": "data/screens/2/v4/manifest.json",
        "note": "v5 keeps v4 concentrations; column-strip layout (one compound per column, B/D/F triplicates)",
        "description": "Round 2 discovery v5 — same compounds/concentrations as v4, column-strip layout",
        "layout": "column_strip",
        "files": {
            "compound_list": "data/screens/2/v5/compound_list.json",
            "compound_list_csv": "data/screens/2/v5/compound_list.csv",
            "plate_map": "data/screens/2/v5/plate_map.json",
            "selection_rationale": "pvjthomas/runs/2/v5/selection_rationale.md",
            "active_plate_map": "data/plate_map_r2.json",
            "active_selection_rationale": "pvjthomas/selection_rationale.md",
        },
    }
    (V5 / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    rationale = """# Round 2 / version 5 — column-strip layout

**Round:** 2 · **Version:** 5 (`r2-discovery-v5`)  
**Supersedes:** [`data/screens/2/v4/`](../v4/)  
**Canonical concentrations:** [`compound_list.json`](../../../../data/screens/2/v5/compound_list.json) (unchanged from v4)

---

## What changed from v4

**Layout only.** Same 10 compounds, triplicates, and literature-backed concentrations.

| Aspect | v4 | v5 |
|--------|----|----|
| Compounds & µM | unchanged | unchanged |
| Replicate geometry | checkerboard | **one column per compound** |
| Sample rows | B–G mixed | **B, D, F only** (every other row) |
| Example (compound 1) | scattered | **B2, D2, F2** |
| Controls | B/D/F cols 3/7/11 | **C/E/G cols 3/7/11** (interior, spaced) |

---

## Layout sketch

```
      1  2  3  4  5  6  7  8  9 10 11 12
A    ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·   ← empty (edge)
B    ·  1  2  3  4  5  6  7  8  9 10  ·   ← rep 1
C    ·  ·  V  ·  ·  ·  V  ·  ·  ·  V  ·   ← vehicle (cols 3/7/11)
D    ·  1  2  3  4  5  6  7  8  9 10  ·   ← rep 2
E    ·  ·  N  ·  ·  ·  N  ·  ·  ·  N  ·   ← no-TEM1
F    ·  1  2  3  4  5  6  7  8  9 10  ·   ← rep 3
G    ·  ·  P  ·  ·  ·  P  ·  ·  ·  P  ·   ← positive
H    ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·   ← empty (edge)
```

Each digit is that compound's replicate in the column. Controls share columns 3/7/11 with samples but sit on gap rows C/E/G (never row A).

Promote to robot: copy `plate_map.json` → `data/plate_map_r2.json` after sign-off.
"""
    (RUNS / "selection_rationale.md").write_text(rationale)

    print(compound_path)
    print(plate_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
