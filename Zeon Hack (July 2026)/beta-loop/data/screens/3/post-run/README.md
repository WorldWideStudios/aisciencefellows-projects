# Round 3 — post-run artifacts

Robot + operator execution outputs for **r3-discovery-v1** (`data/screens/3/v1/`).

**Active plate design:** v1 — 8 compounds × triplicate, sync manual nitrocefin.  
**Not this run:** v2 is deprecated (`../v2-deprecated/DEPRECATED.md`).

Promoted plate map: [`data/plate_map_r3.json`](../../../plate_map_r3.json)

---

## File inventory

Legend: **input** = you provide · **synthetic** = estimated from operator notes · **generated** = pipeline output · **n/a** = will not exist for Run 3

### Root (`post-run/`)

| File | Status | Notes |
|------|--------|-------|
| [`kinetics_r3.csv`](kinetics_r3.csv) | **input — pending** | Gen5 kinetic export (`well, time_s, temperature_c, wavelength_nm, absorbance_a490`). Required to run analysis. |
| [`nitrocefin_timing.json`](nitrocefin_timing.json) | **synthetic — present** | No per-well log available. Built from operator estimate: 12-channel pipette, 6 dispenses, 120 s total span, batches interpolated 24 s apart. Absolute UTC anchor is arbitrary; relative offsets are authoritative. |
| [`reader_lid_close_utc.txt`](reader_lid_close_utc.txt) | **synthetic — present** | No Gen5 PDF. Reader start placed at the 2 min mark (aligned to end of dosing span in `nitrocefin_timing.json`). |
| `run_log_exec_*.txt` | **n/a** | No robot run log for this round. Timing cannot be derived from hole_10 batch events. |
| `r3_gen5_export.pdf` | **n/a** | No Gen5 PDF export. Lid-close time is synthetic (see above). |
| [`manifest.json`](manifest.json) | **generated — present** | Post-run index (this folder). |

### Analysis (`post-run/v1/`)

First-pass analysis for Run 3 v1. Substrate-anchor scoring (`anchor_mode = substrate`); slope primary, endpoint fallback per [`run3_decision_tree.md`](../../../pvjthomas/runs/3/v1/run3_decision_tree.md).

| File | Status | Notes |
|------|--------|-------|
| [`v1/README.md`](v1/README.md) | **generated — present** | Analysis version notes. |
| `v1/run3_decision_report.md` | **generated — pending** | QC gate pass/fail + compound calls. Needs `kinetics_r3.csv`. |
| `v1/conclusions.md` | **generated — pending** | Summary narrative. Needs analysis. |
| `v1/figure_comparison.md` | **generated — pending** | Figure captions vs R2. Needs analysis. |
| `v1/analysis/r3_round_summary_eda.json` | **generated — pending** | Round summary + QC gates. |
| `v1/analysis/r3_kinetics_annotated.csv` | **generated — pending** | Per-well slopes, scores, labels. |
| `v1/analysis/r3_parsed.json` | **generated — pending** | Parsed time courses. |
| `v1/analysis/r3_pattern_summary.json` | **generated — pending** | Pattern clustering. |
| `v1/analysis/r3_pattern_summary.md` | **generated — pending** | Human-readable patterns. |
| `v1/analysis/r3_kinetics_llm_context.json` | **generated — pending** | Agent-readable context. |
| `v1/analysis/r3_kinetics_llm_context.md` | **generated — pending** | Agent-readable context (markdown). |
| `v1/figures/manifest.json` | **generated — pending** | Figure index. |
| `v1/figures/r3_endpoint_inhibition_bars.png` | **generated — pending** | Endpoint inhibition bar chart. |
| `v1/figures/r3_nitrocefin_stagger_timeline.png` | **generated — pending** | Dosing timeline (from synthetic timing). |
| `v1/figures/r3_decision_tree_multichannel_nitrocefin.png` | **generated — pending** | Decision tree flowchart. |
| `v1/figures/r3_tsne_over_library.png` | **generated — pending** | t-SNE overlay. |

### Repo-level outputs (outside this folder)

| File | Status | Notes |
|------|--------|-------|
| [`data/plate_map_r3.json`](../../../plate_map_r3.json) | **generated — present** | Promoted from `data/screens/3/v1/plate_map.json` (signed off 2026-07-26). |
| `data/assay/run_3_summary.json` | **generated — pending** | Git-tracked assay summary. Needs `kinetics_r3.csv`. |
| `data/kinetics_r3.csv` | **generated — pending** | Agent-tool promotion copy of `kinetics_r3.csv`. |

---

## What blocks analysis

Only one **input** file is still required:

```
data/screens/3/post-run/kinetics_r3.csv
```

Drop the Gen5 export there, then run the R3 artifact pipeline (to be wired; mirrors `generate_run2_artifacts.py`).

Everything else either exists (synthetic timing, promoted plate map), will be created by the pipeline, or is explicitly **n/a** for this run.

---

## Layout

```
post-run/
  README.md                    ← this file
  manifest.json
  kinetics_r3.csv              ← INPUT (pending)
  nitrocefin_timing.json       ← synthetic
  reader_lid_close_utc.txt     ← synthetic
  v1/
    README.md
    run3_decision_report.md    ← pending
    conclusions.md             ← pending
    analysis/                  ← pending
    figures/                   ← pending
```

Timing parser docs (R2 run-log method): [`ml/analysis/RUN_LOG_TIMING.md`](../../../ml/analysis/RUN_LOG_TIMING.md) — not applicable here (no run log).
