# Run log timing analysis

How robot run logs are parsed into structured timing reports, how those reports map
back to workflow steps, and where timing artifacts land in the assay pipeline.

This tooling covers **robot motion time** (pipetting, plate moves, waits). It is
separate from **reaction start time** (`nitrocefin_timing.json` per-well t0), which
feeds kinetics scoring in `ml/analysis/kinetics.py`.

---

## Where this fits in a workflow

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Zeon workflow run (e.g. tem1_activity_screen)                          │
│    skills emit run_log_*.jsonl during execution                         │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  save_run_folder (last workflow node)                                   │
│    copies run_log → data/logs/<eid>/<run>_<ts>/logs/                    │
│    renders run_log.txt                                                    │
│    writes timing_summary.json  ← auto via timing_summary.py               │
│    copies nitrocefin_timing.json if present                               │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │
              ┌─────────────────┴─────────────────┐
              ▼                                   ▼
   Post-run review / optimization          CI regression check
   (human or agent reads summary)         (pytest + --check-baseline)
```

**Required for auto timing summary:** workflow must end with `save_run_folder`
(as `tem1_activity_screen` does). No code changes are needed inside individual
pipetting skills.

**Optional for phase bucketing:** add `timing_phases` to the workflow JSON (see
below). Without it, the parser falls back to generic TEM-1 heuristics.

**Optional for CI budgets:** commit a baseline under
`ml/analysis/timing_baselines/<workflow_id>_v<version>.json` after a reference
run.

---

## Artifacts

| File | Produced by | Purpose |
|------|-------------|---------|
| `run_log.jsonl` | Zeon runtime | Raw structured events |
| `run_log.txt` | `save_run_folder` | Human-readable log |
| `timing_summary.json` | `save_run_folder` → `timing_summary.py` | Phase budgets, step spans, idle gaps |
| `timing/nitrocefin_timing.json` | `batched_dispense_mastermix` (when `timing_label` set) | Per-well substrate t0 for kinetics |
| `timing_baselines/*.json` | Committed manually | Expected phase durations for regression |

Example run folder:

```
data/logs/<execution_id>/<run_name>_<timestamp>/
├── logs/
│   ├── run_log.jsonl
│   ├── run_log.txt
│   └── timing_summary.json
├── timing/
│   └── nitrocefin_timing.json
├── metadata.json
└── run_inputs.json
```

---

## Module: `ml/analysis/run_log_timing.py`

### Parsing

| Function | Use when |
|----------|----------|
| `parse_run_log_path(path)` | You have a `.txt` or `.jsonl` path; no workflow mapping |
| `analyze_run_log(log_path, workflow_json=..., workflow_id=...)` | Full report with `node_id` / `skill_id` / phase from workflow JSON |
| `build_run_timing_report(header, events, workflow_index=...)` | You already parsed events and want the report object |

Log step labels join to workflow nodes on **`nodes[].label`** (the text after `▶`
in `STARTING` lines). Duplicate `STARTING` pings are collapsed into one span per
step (first start → first start of the next label).

### Workflow configuration

| Function | Use when |
|----------|----------|
| `load_workflow_step_index(workflow_json)` | Build `label → {node_id, skill_id, phase}` |
| `load_timing_phases(workflow_dict)` | Read `timing_phases` array from workflow JSON |
| `map_step_spans_to_workflow(spans, index, phase_rules=...)` | Attach workflow metadata to collapsed spans |

#### `timing_phases` schema (workflow JSON)

Add a top-level array to any workflow:

```json
"timing_phases": [
  { "phase": "setup", "match": ["prepare dilutions", "pick up pipette"] },
  { "phase": "assay_loading", "match": ["dispense tem-1", "dispense test compound"] }
]
```

- **`phase`**: bucket name in timing summaries and baselines
- **`match`**: case-insensitive substrings of log step labels; **first match wins**
- Unmatched labels → `"other"`
- If `timing_phases` is omitted → `DEFAULT_PHASE_RULES` (TEM-1 screen defaults)

**Workflows with `timing_phases` today**

| Workflow | In our R2 TEM-1 runs? | Notes |
|----------|----------------------|-------|
| `tem1_activity_screen.json` | **Yes** | Part 3 nitrocefin screen; baseline committed |
| `tem1_dilution_plate.json` | Partial (dilution-only variant) | Single `setup` phase |
| `cfps_mastermix.json` | **No** | Part 1 CFPS (Rob); phases added for future runs, no baseline yet |

### Output helpers

| Function | Use when |
|----------|----------|
| `report_to_dict(report)` | JSON-serializable dict (APIs, dashboards) |
| `format_text_summary(report)` | Terminal / markdown review |
| `write_timing_artifact(report, path)` | Write `timing_summary.json` |

### Regression baselines (CI)

| Function | Use when |
|----------|----------|
| `resolve_timing_baseline_path(workflow_json=..., execution_workflow=...)` | Find `timing_baselines/<id>_v<version>.json` |
| `load_timing_baseline(path)` | Load baseline JSON |
| `check_timing_regression(report, baseline)` | Returns list of violation strings (empty = pass) |

Baseline schema (`ml/analysis/timing_baselines/tem1_activity_screen_v1.0.0.json`):

```json
{
  "schema_version": 1,
  "workflow_id": "tem1_activity_screen",
  "workflow_version": "1.0.0",
  "tolerance_defaults": { "relative_pct": 20.0, "min_absolute_seconds": 60.0 },
  "phases": { "setup": { "expected_seconds": 4587.0 }, ... },
  "total_seconds": { "expected_seconds": 10280.0 }
}
```

Tolerance per phase: `limit = expected + max(expected × relative_pct / 100, min_absolute_seconds)`.

---

## Skill hook: `save_run_folder/timing_summary.py`

Called from `save_run_folder` after log copy. Not imported by other skills.

| Function | Role |
|----------|------|
| `find_repo_root(project_data=...)` | Locate repo `ml/` from project data dir |
| `workflow_id_from_metadata(meta_path)` | Read `workflow_id` from `metadata.json` |
| `write_run_log_timing_summary(logs_dir, ...)` | Parse log, write `logs/timing_summary.json` |

Best-effort: warnings via `print_log`, never fails the workflow.

---

## CLI

```bash
cd ml/agent
PYTHONPATH=../ python3 -m analysis.run_log_timing \
  /path/to/run_log.txt \
  --workflow ../../mastermix/workflows/tem1_activity_screen.json \
  --out timing_summary.json \
  --text

# Fail if slower than committed baseline (CI)
PYTHONPATH=../ python3 -m analysis.run_log_timing \
  /path/to/run_log.txt \
  --workflow ../../mastermix/workflows/tem1_activity_screen.json \
  --check-baseline
```

---

## Python API (typical)

```python
from analysis.run_log_timing import (
    analyze_run_log,
    check_timing_regression,
    format_text_summary,
    load_timing_baseline,
    resolve_timing_baseline_path,
)

report = analyze_run_log("run_log.txt", workflow_json="mastermix/workflows/tem1_activity_screen.json")
print(format_text_summary(report))

baseline_path = resolve_timing_baseline_path(workflow_json="mastermix/workflows/tem1_activity_screen.json")
if baseline_path:
    violations = check_timing_regression(report, load_timing_baseline(baseline_path))
    assert not violations, violations
```

---

## Adding timing support to a new workflow

1. **Ensure terminal node** is `save_run_folder` (timing summary is automatic).
2. **Add `timing_phases`** to the workflow JSON — match strings against real
   `nodes[].label` values from a test run log.
3. **Run once**, inspect `logs/timing_summary.json` phase buckets; tune `match`
   strings if steps land in `"other"`.
4. **Commit a baseline** (optional): copy phase seconds into
   `ml/analysis/timing_baselines/<workflow_id>_v<version>.json`.
5. **Add pytest** mirroring `test_sample_log_within_timing_baseline` in
   `ml/agent/tests/unit/test_run_log_timing.py`.

For kinetics-sensitive dispenses (substrate t0), pass `timing_label` into
`batched_dispense_mastermix` — that path is independent of run-log timing.

---

## Repeatable manual analysis checklist

1. Parse header (execution id, workflow, duration).
2. Classify events: dispense, wait, swap, milestone; ignore duplicate `STARTING`.
3. Collapse to one span per step label.
4. Map spans to workflow `nodes[].label` → `node_id`.
5. Sum spans by `timing_phases` phase → time budget.
6. Flag idle gaps >3 min without a logged wait.
7. Cross-check biology: pre-incubation logged duration, nitrocefin prep vs dispense
   stagger; join `nitrocefin_timing.json` for per-well t0 if doing kinetics QC.

---

## Tests

```bash
cd ml/agent
PYTHONPATH=../ pytest tests/unit/test_run_log_timing.py tests/unit/test_save_run_folder_timing.py -q
```

Reference log: `data/screens/2/post-run/run_log_exec_tem1_activity_screen_hack_world_22_20260725_230432.txt`.
Human write-up: `data/screens/2/post-run/r2_timing_log_analysis.md`.
