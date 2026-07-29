# Where we are — pvjthomas workspace

**Owner:** Philip (pvjthomas)  
**Updated:** 2026-07-25  
**Active screen:** Round 2 discovery **v5** (`r2-discovery-v5`) — pending sign-off

This folder is a working copy of reports and plate artifacts. Canonical versioned files live under [`data/screens/`](../../data/screens/) and [`pvjthomas/runs/`](../runs/).

---

## Round 2 discovery — current proposal (v5)

| Item | Value |
|------|-------|
| **Status** | Pending sign-off → promote to `data/plate_map_r2.json` for robot |
| **Compounds** | 9 discovery + clavulanic acid as **positive control only** (not duplicated as a sample) |
| **Replicates** | 3 per compound, **same column, rows B/D/F** |
| **Controls** | 3 vehicle · 3 no-TEM-1 · 3 positive — **3/7 on B/D/F; 11 on C/E/G** |
| **Wells used** | 36 of 96 |
| **Layout** | Column-strip, x-spaced — band 1: B/D/F cols 2/4/6/8/10; band 2: C/E/G cols **5/9**; band 3: C/E/G cols 3/7 |
| **Concentrations** | Literature-backed (unchanged from v4); T1262 @ **1 µM**, others mostly @ 50 µM |

### Version history (Round 2)

| Ver | Label | What changed | Status |
|-----|-------|--------------|--------|
| v1 | `r2-discovery-v1` | 24 compounds × triplicate | Superseded |
| v2 | `r2-discovery-v2` | Cut to 10 compounds; compact layout | Superseded |
| v3 | `r2-discovery-v3` | Same layout as v2 + per-compound literature concentrations | Superseded by v4 layout |
| **v4** | `r2-discovery-v4` | Spaced interior checkerboard | Superseded by v5 layout |
| **v5** | **`r2-discovery-v5`** | **Column-strip: triplicates on B/D/F per column** | **Current proposal** |

Rationale docs: [`pvjthomas/runs/2/`](../runs/2/) (v1–v5).

---

## Files in this folder

### Plate maps (working copies)

| File | Description |
|------|-------------|
| [`plate_map_r2_v5.json`](plate_map_r2_v5.json) | **Current** plate map JSON |
| [`plate_map_r2_v5.png`](plate_map_r2_v5.png) | Visualization — color by sample type |
| [`plate_map_r2_v5_by_compound.png`](plate_map_r2_v5_by_compound.png) | Visualization — color by compound ID |
| [`compound_list_r2_v5.json`](compound_list_r2_v5.json) | Compound list with literature-backed concentrations |
| [`kinetic_schedule_r2_v5.json`](kinetic_schedule_r2_v5.json) | **A490 kinetic read plan** (25 °C, 2 min equilibration, 30 s × 10 min) |
| [`kinetic_schedule_r2_v5.md`](kinetic_schedule_r2_v5.md) | Human-readable kinetic schedule for R2 v5 |
| `plate_map_r2_v4.*` | Previous v4 spaced-interior layout (archive) |
| `plate_map.json` / `plate_map.png` | Earlier v2-era working copy (archive) |

Canonical paths:

- `data/screens/2/v5/plate_map.json`
- `data/screens/2/v5/plate_map.png`
- `data/screens/2/v5/plate_map_by_compound.png`
- `data/screens/2/v5/kinetic_schedule.json`
- `data/screens/2/post-run/` — robot run log, timing analysis, plate reader export (`kinetics_r2.csv`), EDA under `analysis/` (see [`manifest.json`](../../data/screens/2/post-run/manifest.json))

### Reports & tables

| File | Description |
|------|-------------|
| [`phase_a_report.md`](phase_a_report.md) | Phase A library inventory (105 compounds classified) |
| [`concentration_table.md`](concentration_table.md) | Literature concentration rules 1–3 (full library scan) |
| [`concentration_table.json`](concentration_table.json) | Machine-readable concentration table |
| [`tier1example.md`](tier1example.md) | Tier-1 inhibitor example dossier |
| [`tier2example.md`](tier2example.md) | Tier-2 example dossier |

---

## 9 discovery compounds on the v5 plate

T19860 (clavulanic acid) is **positive control only** — not in this table.

| Slot | ID | Name | Screen µM | Bucket |
|------|-----|------|-----------|--------|
| 1 | T1262 | Tazobactam | **1.0** | tier1_inhibitor |
| 2 | T6685 | Sulbactam sodium | 50 | tier1_inhibitor |
| 3 | T14081 | Enmetazobactam | 50 | tier1_inhibitor |
| 4 | T1005 | Amoxicillin | 50 | substrate_control |
| 5 | T1008 | Cephalexin | 50 | substrate_control |
| 6 | T0224 | Meropenem | 50 | substrate_control |
| 7 | T0985 | Oxacillin sodium salt | 50 | substrate_control |
| 8 | T0138 | Cefpiramide acid | 50 | diverse_pick |
| 9 | T8390 | Cefazolin | 50 | diverse_pick |

---

## Tooling

| Task | Command |
|------|---------|
| Build v5 from v4 | `python ml/scripts/build_screen2_v5.py` |
| Generate plate map from compound list | `python pvjthomas/scripts/generate_plate_map.py data/screens/2/v5/compound_list.json -o data/screens/2/v5/plate_map.json` |
| Render PNG (sample type) | `python scripts/render_platemap.py data/screens/2/v5/plate_map.json` |
| Render PNG (by compound) | `python scripts/render_platemap.py data/screens/2/v5/plate_map.json --by compound` |

Code:

- [`pvjthomas/plates.py`](../plates.py) — layout generator (`compact`, `spaced_interior`, `column_strip`; see `.cursor/rules/plate-layout.mdc`)
- [`ml/analysis/plate_viz.py`](../../ml/analysis/plate_viz.py) — colored PNG renderer
- [`ml/scripts/build_screen2_v3.py`](../../ml/scripts/build_screen2_v3.py) — v3 concentrations from literature
- [`ml/scripts/build_screen2_v5.py`](../../ml/scripts/build_screen2_v5.py) — v5 column-strip layout from v4

---

## Next steps

1. **Sign off v5** plate map (layout + concentrations).
2. Promote: `cp data/screens/2/v5/plate_map.json data/plate_map_r2.json`
3. Point active rationale at [`pvjthomas/runs/2/v5/selection_rationale.md`](../runs/2/v5/selection_rationale.md)
4. Run on robot / plate reader; merge results back via `ml/analysis/` pipeline
5. **Run 2 kinetics** — canonical CSV at `data/screens/2/post-run/kinetics_r2.csv` (promoted copy: `data/kinetics_r2.csv`):
   - [ ] `analyze_kinetics_run("data/screens/2/post-run/kinetics_r2.csv", run=2, version=5)` → outputs under `post-run/analysis/r2_*`
   - [ ] `analyze_kinetics_file(...)` → check Q1 (≥29/36 wells), Q2, Q3
   - [ ] Confirm compound calls use **median of 3/3** well scores per `compound_id` (T1262/T6685/T14081 ≥50; substrates <20)
   - [ ] Emit `data/assay/run_2_summary.json` with labels (`confirmed_hit`, `confirmed_substrate`, etc.)
   - [ ] If Q2 fail → [hand_q2_enzyme_check.md](../runs/2/v5/hand_q2_enzyme_check.md); if Q3 fail → [hand_q3_inhibition_check.md](../runs/2/v5/hand_q3_inhibition_check.md)

---

## Other rounds

| Round | Active version | Notes |
|-------|----------------|-------|
| R1 | v2 validation | Clavulanic vs DMSO @ 50 µM, 8 wells — [`data/screens/1/v2/`](../../data/screens/1/v2/) |
| R2 | **v5 proposed** | See above |
