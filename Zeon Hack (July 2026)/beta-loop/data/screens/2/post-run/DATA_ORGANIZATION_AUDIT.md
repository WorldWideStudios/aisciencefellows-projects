# Run 2 data organization audit

Generated: 2026-07-26T15:52:04Z

This report lists scattered Round 2 artifacts and recommends whether to consolidate under [`data/screens/2/post-run/`](../../data/screens/2/post-run/) or leave in place.

## Executive summary

No file moves recommended — post-run folder looks consolidated.

**Still missing for decision-tree analysis:**
- `data/screens/2/post-run/nitrocefin_timing.json — Per-well t0 from robot dispense log (Q1T)`
- `data/screens/2/post-run/reader_lid_close_utc.txt — Plate reader lid-close timestamp`
- `data/plate_map_r2.json — Promoted active plate map for analyze_kinetics()`
- `data/assay/run_2_summary.json — Decision-tree output summary`
- `data/round_summary_r2.json — Legacy agent round summary path`

## Action counts

| Action | Count |
|--------|------:|
| `archive_ok` | 4 |
| `dedupe_do_not_move` | 5 |
| `generate_from_existing` | 1 |
| `human_review` | 7 |
| `keep_in_place` | 29 |
| `promote_to_data` | 2 |

## Detailed findings

### ✓ `data/screens/2/post-run/kinetics_r2.csv`
- **Relevance:** `required_for_analysis`
- **Action:** `keep_in_place`
- **Size:** 73,717 bytes
- **Reason:** Present: Kinetic CSV for Q1–Q3 analysis

### ✗ `data/screens/2/post-run/nitrocefin_timing.json`
- **Relevance:** `missing_expected`
- **Action:** `generate_from_existing`
- **Reason:** Missing: Per-well t0 from robot dispense log (Q1T)

### ✗ `data/screens/2/post-run/reader_lid_close_utc.txt`
- **Relevance:** `missing_expected`
- **Action:** `human_review`
- **Reason:** Missing: Plate reader lid-close timestamp

### ✗ `data/plate_map_r2.json`
- **Relevance:** `missing_expected`
- **Action:** `human_review`
- **Reason:** Missing: Promoted active plate map for analyze_kinetics()

### ✗ `data/assay/run_2_summary.json`
- **Relevance:** `missing_expected`
- **Action:** `human_review`
- **Reason:** Missing: Decision-tree output summary

### ✓ `data/kinetics_r2.csv`
- **Relevance:** `required_for_analysis`
- **Action:** `keep_in_place`
- **Duplicate of:** `data/screens/2/post-run/kinetics_r2.csv`
- **Size:** 73,717 bytes
- **Reason:** Present: Agent tool path expected by analyze_kinetics(round=2)

### ✗ `data/round_summary_r2.json`
- **Relevance:** `missing_expected`
- **Action:** `human_review`
- **Reason:** Missing: Legacy agent round summary path

### ✓ `data/screens/2/post-run/run_log_exec_tem1_activity_screen_hack_world_22_20260725_230432.txt`
- **Relevance:** `required_for_analysis`
- **Action:** `keep_in_place`
- **Size:** 31,101 bytes
- **Reason:** Robot run log

### ✓ `data/screens/2/post-run/r2_timing_log_analysis.md`
- **Relevance:** `required_for_analysis`
- **Action:** `keep_in_place`
- **Size:** 10,099 bytes
- **Reason:** Timing budget write-up

### ✓ `data/screens/2/post-run/manifest.json`
- **Relevance:** `required_for_analysis`
- **Action:** `keep_in_place`
- **Size:** 1,380 bytes
- **Reason:** Post-run manifest

### ✓ `data/screens/2/post-run/README.md`
- **Relevance:** `required_for_analysis`
- **Action:** `keep_in_place`
- **Size:** 1,437 bytes
- **Reason:** Post-run index

### ✓ `data/screens/2/post-run/kinetics_r2.csv`
- **Relevance:** `required_for_analysis`
- **Action:** `keep_in_place`
- **Size:** 73,717 bytes
- **Reason:** Run 2 post-run: Primary Gen5 kinetic CSV for Run 2 v5

### ✓ `data/screens/2/post-run/r2_gen5_export.pdf`
- **Relevance:** `required_for_analysis`
- **Action:** `keep_in_place`
- **Size:** 152,596 bytes
- **Reason:** Run 2 post-run: Source Gen5 PDF export for Run 2

### ✓ `data/screens/2/post-run/analysis/r2_kinetics_annotated.csv`
- **Relevance:** `useful_derivative`
- **Action:** `keep_in_place`
- **Size:** 129,241 bytes
- **Reason:** Run 2 post-run: Annotated kinetic CSV (EDA pipeline)

### ✓ `data/screens/2/post-run/analysis/r2_parsed.json`
- **Relevance:** `useful_derivative`
- **Action:** `keep_in_place`
- **Size:** 691,865 bytes
- **Reason:** Run 2 post-run: Parsed Gen5 PDF JSON (96-well Max V)

### ✓ `data/screens/2/post-run/analysis/r2_round_summary_eda.json`
- **Relevance:** `useful_derivative`
- **Action:** `keep_in_place`
- **Size:** 33,430 bytes
- **Reason:** Run 2 post-run: Q1/Q2/Q3 round summary from EDA

### ✓ `data/screens/2/post-run/analysis/r2_pattern_summary.json`
- **Relevance:** `useful_derivative`
- **Action:** `keep_in_place`
- **Size:** 66,903 bytes
- **Reason:** Run 2 post-run: Pattern summary JSON

### ✓ `data/screens/2/post-run/analysis/r2_pattern_summary.md`
- **Relevance:** `useful_derivative`
- **Action:** `keep_in_place`
- **Size:** 2,851 bytes
- **Reason:** Run 2 post-run: Pattern summary markdown

### ✓ `data/screens/2/post-run/analysis/r2_kinetics_llm_context.json`
- **Relevance:** `useful_derivative`
- **Action:** `keep_in_place`
- **Size:** 25,756 bytes
- **Reason:** Run 2 post-run: LLM context bundle

### ✓ `data/screens/2/post-run/analysis/r2_kinetics_llm_context.md`
- **Relevance:** `useful_derivative`
- **Action:** `keep_in_place`
- **Size:** 4,806 bytes
- **Reason:** Run 2 post-run: LLM context markdown

### ✓ `data/screens/2/v5/plate_map.json`
- **Relevance:** `pre_run_design`
- **Action:** `keep_in_place`
- **Size:** 8,475 bytes
- **Reason:** Pre-run plate design v5 — canonical under data/screens/2/v5/

### ✓ `data/screens/2/v5/plate_map.png`
- **Relevance:** `pre_run_design`
- **Action:** `keep_in_place`
- **Size:** 105,314 bytes
- **Reason:** Pre-run plate design v5 — canonical under data/screens/2/v5/

### ✓ `data/screens/2/v5/plate_map_by_compound.png`
- **Relevance:** `pre_run_design`
- **Action:** `keep_in_place`
- **Size:** 132,628 bytes
- **Reason:** Pre-run plate design v5 — canonical under data/screens/2/v5/

### ✓ `data/screens/2/v5/compound_list.json`
- **Relevance:** `pre_run_design`
- **Action:** `keep_in_place`
- **Size:** 10,647 bytes
- **Reason:** Pre-run plate design v5 — canonical under data/screens/2/v5/

### ✓ `data/screens/2/v5/compound_list.csv`
- **Relevance:** `pre_run_design`
- **Action:** `keep_in_place`
- **Size:** 2,654 bytes
- **Reason:** Pre-run plate design v5 — canonical under data/screens/2/v5/

### ✓ `data/screens/2/v5/kinetic_schedule.json`
- **Relevance:** `pre_run_design`
- **Action:** `keep_in_place`
- **Size:** 4,032 bytes
- **Reason:** Pre-run plate design v5 — canonical under data/screens/2/v5/

### ✓ `data/screens/2/v5/manifest.json`
- **Relevance:** `pre_run_design`
- **Action:** `keep_in_place`
- **Size:** 920 bytes
- **Reason:** Pre-run plate design v5 — canonical under data/screens/2/v5/

### ✓ `pvjthomas/output/plate_map_r2_v5.json`
- **Relevance:** `duplicate_working_copy`
- **Action:** `dedupe_do_not_move`
- **Duplicate of:** `data/screens/2/v5/plate_map.json`
- **Size:** 8,475 bytes
- **Reason:** Working copy; canonical version lives under data/screens/2/v5/

### ✓ `pvjthomas/output/plate_map_r2_v5.png`
- **Relevance:** `duplicate_working_copy`
- **Action:** `dedupe_do_not_move`
- **Duplicate of:** `data/screens/2/v5/plate_map.png`
- **Size:** 105,314 bytes
- **Reason:** Working copy; canonical version lives under data/screens/2/v5/

### ✓ `pvjthomas/output/plate_map_r2_v5_by_compound.png`
- **Relevance:** `duplicate_working_copy`
- **Action:** `dedupe_do_not_move`
- **Duplicate of:** `data/screens/2/v5/plate_map_by_compound.png`
- **Size:** 132,628 bytes
- **Reason:** Working copy; canonical version lives under data/screens/2/v5/

### ✓ `pvjthomas/output/compound_list_r2_v5.json`
- **Relevance:** `duplicate_working_copy`
- **Action:** `dedupe_do_not_move`
- **Duplicate of:** `data/screens/2/v5/compound_list.json`
- **Size:** 10,647 bytes
- **Reason:** Working copy; canonical version lives under data/screens/2/v5/

### ✓ `pvjthomas/output/kinetic_schedule_r2_v5.json`
- **Relevance:** `duplicate_working_copy`
- **Action:** `dedupe_do_not_move`
- **Duplicate of:** `data/screens/2/v5/kinetic_schedule.json`
- **Size:** 4,032 bytes
- **Reason:** Working copy; canonical version lives under data/screens/2/v5/

### ✓ `pvjthomas/output/phase_a_report.md`
- **Relevance:** `unrelated_or_unclear`
- **Action:** `keep_in_place`
- **Size:** 4,772 bytes
- **Reason:** Philip workspace report — not a Run 2 execution artifact

### ✓ `pvjthomas/output/concentration_table.md`
- **Relevance:** `unrelated_or_unclear`
- **Action:** `keep_in_place`
- **Size:** 3,650 bytes
- **Reason:** Philip workspace report — not a Run 2 execution artifact

### ✓ `pvjthomas/output/concentration_table.json`
- **Relevance:** `unrelated_or_unclear`
- **Action:** `keep_in_place`
- **Size:** 5,050 bytes
- **Reason:** Philip workspace report — not a Run 2 execution artifact

### ✓ `pvjthomas/output/concentration_literature_run.log`
- **Relevance:** `unrelated_or_unclear`
- **Action:** `keep_in_place`
- **Size:** 10,770 bytes
- **Reason:** Philip workspace report — not a Run 2 execution artifact

### ✓ `pvjthomas/output/tier1example.md`
- **Relevance:** `unrelated_or_unclear`
- **Action:** `keep_in_place`
- **Size:** 3,289 bytes
- **Reason:** Philip workspace report — not a Run 2 execution artifact

### ✓ `pvjthomas/output/tier2example.md`
- **Relevance:** `unrelated_or_unclear`
- **Action:** `keep_in_place`
- **Size:** 3,485 bytes
- **Reason:** Philip workspace report — not a Run 2 execution artifact

### ✓ `pvjthomas/output/status.md`
- **Relevance:** `unrelated_or_unclear`
- **Action:** `keep_in_place`
- **Size:** 6,342 bytes
- **Reason:** Philip workspace report — not a Run 2 execution artifact

### ✓ `data/screens/2/v1/manifest.json`
- **Relevance:** `superseded_version`
- **Action:** `archive_ok`
- **Size:** 828 bytes
- **Reason:** Superseded Round 2 design v1; keep for history

### ✓ `data/screens/2/v2/manifest.json`
- **Relevance:** `superseded_version`
- **Action:** `archive_ok`
- **Size:** 827 bytes
- **Reason:** Superseded Round 2 design v2; keep for history

### ✓ `data/screens/2/v3/manifest.json`
- **Relevance:** `superseded_version`
- **Action:** `archive_ok`
- **Size:** 1,201 bytes
- **Reason:** Superseded Round 2 design v3; keep for history

### ✓ `data/screens/2/v4/manifest.json`
- **Relevance:** `superseded_version`
- **Action:** `archive_ok`
- **Size:** 849 bytes
- **Reason:** Superseded Round 2 design v4; keep for history

### ✓ `skill_platereader_measure_20260724_231705.pdf`
- **Relevance:** `unrelated_or_unclear`
- **Action:** `human_review`
- **Suggested target:** `data/screens/2/post-run/skill_platereader_measure_20260724_231705.pdf`
- **Size:** 109,220 bytes
- **Reason:** Plate reader skill PDF at repo root (~109 KB); smaller than r2_gen5_export.pdf (~153 KB) — likely a different/partial read; confirm before moving

### ✓ `mastermix/data/platereader/skill_platereader_measure_20260725_173839/skill_platereader_measure_20260725_173839.pdf`
- **Relevance:** `unrelated_or_unclear`
- **Action:** `human_review`
- **Size:** 109,724 bytes
- **Reason:** Mastermix platereader skill capture — compare to r2_gen5_export.pdf before consolidating

### ✓ `mastermix/data/platereader/skill_platereader_measure_20260725_174147/skill_platereader_measure_20260725_174147.pdf`
- **Relevance:** `unrelated_or_unclear`
- **Action:** `human_review`
- **Size:** 109,704 bytes
- **Reason:** Mastermix platereader skill capture — compare to r2_gen5_export.pdf before consolidating

### ✗ `data/plate_map_r2.json`
- **Relevance:** `missing_expected`
- **Action:** `promote_to_data`
- **Suggested target:** `data/plate_map_r2.json`
- **Reason:** Promote v5 plate map after human sign-off (see pvjthomas/output/status.md)

## Suggested promotion commands (manual — not executed by audit)

```bash
# Agent/analysis promotion (after sign-off)
cp data/screens/2/v5/plate_map.json data/plate_map_r2.json
cp data/screens/2/post-run/kinetics_r2.csv data/kinetics_r2.csv
cp data/screens/2/post-run/analysis/r2_round_summary_eda.json data/assay/run_2_summary.json
```

Regenerate: `python ml/scripts/audit_run2_data.py`
