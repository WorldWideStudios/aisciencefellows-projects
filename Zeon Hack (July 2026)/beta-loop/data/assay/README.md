# Assay results (git-tracked summaries)

Final per-compound assay outputs live here. **Raw plate-reader exports** default to [`pvjthomas/local/kinetics/`](../../pvjthomas/local/README.md).

See [`STORAGE.md`](../STORAGE.md) for the full git vs local policy.

## Files

| File | When | Contents |
|------|------|----------|
| `run_{n}_summary.json` | After screen run *n* | Slopes, `pct_inhibition`, labels per `compound_id`, QC gates |

## `run_{n}_summary.json` shape

```json
{
  "run": 2,
  "round": 2,
  "status": "complete",
  "source_csv_local": "pvjthomas/local/kinetics/kinetics_r2.csv",
  "source_csv_git": null,
  "normalization": {
    "vehicle_wells": ["B3", "B7", "C11"],
    "no_tem1_wells": ["D3", "D7", "E11"]
  },
  "qc_gates": {
    "q1_pass": true,
    "q1t_timing_unknown": false,
    "q1t_timing_stagger": true,
    "q2_pass": true,
    "q2_endpoint_pass": true,
    "q3_pass": true,
    "pos_ctrl_median_pct": 92.5
  },
  "scoring_mode": "endpoint",
  "analysis_version": "v2",
  "analysis_dir": "data/screens/2/post-run/v2/analysis",
  "timing_stagger_min": 22.5,
  "wells_timing_suspect": ["B2", "D2"],
  "pre_read_overage_wells": [],
  "compounds": {
    "T1262": {
      "median_pct_inhibition": 88.0,
      "label": "confirmed_hit",
      "timing_suspect_reps": 0,
      "wells": [
        {
          "well": "B2",
          "pct_inhibition": 88.0,
          "timing_suspect": false,
          "concentration_uM": 1.0
        }
      ]
    }
  }
}
```

**Labels:** `confirmed_hit` | `confirmed_substrate` | `surprise_hit` | `surprise_miss` | `borderline` | `failed_well` | `timing_suspect` | `false_flat_substrate` | `retest_sync_dose`

Results are merged into [`compound_dossiers.json`](../compound_dossiers.json) by analysis scripts after each run.

Analysis implementation: [`ml/analysis/kinetics.py`](../../ml/analysis/kinetics.py) → `analyze_kinetics_file()`. Decision tree: [`pvjthomas/runs/2/v5/run2_decision_tree.md`](../../pvjthomas/runs/2/v5/run2_decision_tree.md).
