# Round 2 / version 4 — spaced interior layout

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
