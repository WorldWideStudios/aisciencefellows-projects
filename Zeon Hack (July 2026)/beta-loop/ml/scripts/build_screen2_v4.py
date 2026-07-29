#!/usr/bin/env python3
"""Build data/screens/2/v4 from v3 — same compounds/concentrations, spaced layout only."""

from __future__ import annotations

import copy
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from pvjthomas.plates import generate_plate_map_from_file  # noqa: E402

V3 = REPO / "data/screens/2/v3"
V4 = REPO / "data/screens/2/v4"
RUNS = REPO / "pvjthomas/runs/2/v4"


def main() -> int:
    v3_list = json.loads((V3 / "compound_list.json").read_text())
    v4_list = copy.deepcopy(v3_list)
    v4_list.update(
        {
            "version": 4,
            "version_label": "r2-discovery-v4",
            "supersedes": "data/screens/2/v3/compound_list.json",
            "rationale_doc": "pvjthomas/runs/2/v4/selection_rationale.md",
            "layout": "spaced_interior",
            "note": (
                "Same 10 compounds and literature-backed concentrations as v3; "
                "v4 changes well layout only (interior checkerboard, no edge wells)."
            ),
        }
    )

    V4.mkdir(parents=True, exist_ok=True)
    RUNS.mkdir(parents=True, exist_ok=True)

    compound_path = V4 / "compound_list.json"
    compound_path.write_text(json.dumps(v4_list, indent=2) + "\n")

    with (V3 / "compound_list.csv").open(newline="") as f_in, (V4 / "compound_list.csv").open(
        "w", newline=""
    ) as f_out:
        writer = csv.writer(f_out)
        for row in csv.reader(f_in):
            writer.writerow(row)

    plate_path = generate_plate_map_from_file(compound_path, V4 / "plate_map.json")

    manifest = {
        "run": 2,
        "round": 2,
        "version": 4,
        "label": "r2-discovery-v4",
        "created_at": datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%dT%H:%M:%S%z"),
        "author": "pvjthomas",
        "status": "pending_signoff",
        "supersedes": "data/screens/2/v3/manifest.json",
        "note": "v4 keeps v3 compound concentrations; well layout uses spaced interior checkerboard",
        "description": "Round 2 discovery v4 — same compounds/concentrations as v3, spaced interior layout",
        "layout": "spaced_interior",
        "files": {
            "compound_list": "data/screens/2/v4/compound_list.json",
            "compound_list_csv": "data/screens/2/v4/compound_list.csv",
            "plate_map": "data/screens/2/v4/plate_map.json",
            "selection_rationale": "pvjthomas/runs/2/v4/selection_rationale.md",
            "active_plate_map": "data/plate_map_r2.json",
            "active_selection_rationale": "pvjthomas/selection_rationale.md",
        },
    }
    (V4 / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    rationale = """# Round 2 / version 4 — spaced interior layout

**Round:** 2 · **Version:** 4 (`r2-discovery-v4`)  
**Supersedes:** [`data/screens/2/v3/`](../v3/)  
**Canonical concentrations:** [`compound_list.json`](../../../../data/screens/2/v4/compound_list.json) (unchanged from v3)

---

## What changed from v3

**Layout only.** Same 10 compounds, triplicates, and literature-backed concentrations as v3.

| Aspect | v3 | v4 |
|--------|----|----|
| Compounds & µM | unchanged | unchanged |
| Edge wells (A, H, col 1, col 12) | used (row A controls) | **empty** |
| Sample placement | packed rows B–D | **interior checkerboard** |
| Controls | row A × 9 | **rows B/D/F at cols 3/7/11** |
| Spacing | adjacent wells | **empty well between orthogonal neighbors** |

---

## Layout sketch

```
      1  2  3  4  5  6  7  8  9 10 11 12
A    ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·   ← edge (empty)
B    ·  S  ·  V  ·  S  ·  V  ·  S  ·  V   S=sample  V=vehicle
C    ·  ·  S  ·  S  ·  S  ·  S  ·  S  ·
D    ·  S  ·  N  ·  S  ·  N  ·  S  ·  N   N=noTEM1
E    ·  ·  S  ·  S  ·  S  ·  S  ·  S  ·
F    ·  S  ·  P  ·  S  ·  P  ·  S  ·  P   P=positive
G    ·  ·  S  ·  S  ·  S  ·  S  ·  S  ·
H    ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·  ·   ← edge (empty)
```

Promote to robot: copy `plate_map.json` → `data/plate_map_r2.json` after sign-off.
"""
    (RUNS / "selection_rationale.md").write_text(rationale)

    print(compound_path)
    print(plate_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
