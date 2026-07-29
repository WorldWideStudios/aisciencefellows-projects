# Round 2 — post-run artifacts

Robot execution outputs for the physical screen, after the plate design in [`../v5/`](../v5/) was run.

## Layout

```
post-run/
  kinetics_r2.csv          # shared Gen5 export
  nitrocefin_timing.json   # shared Q1T metadata
  reader_lid_close_utc.txt
  run_log_exec_*.txt
  r2_gen5_export.pdf
  v1/                      # frozen slope-only analysis (superseded)
  v2/                      # active endpoint-fallback analysis
```

| Location | Contents |
|----------|----------|
| **Root** | Raw execution exports (reader CSV, timing, run log, Gen5 PDF) |
| **[`v1/`](v1/)** | First-pass analysis — slope scoring only; Q2/Q3 failed |
| **[`v2/`](v2/)** | **Active** — endpoint fallback when slope Q2 fails; drives `data/assay/run_2_summary.json` |

## Regenerate active analysis (v2)

```bash
python ml/scripts/generate_run2_artifacts.py
```

Or EDA only:

```python
analyze_kinetics_run("data/screens/2/post-run/kinetics_r2.csv", run=2, version=5, analysis_version="v2")
```

Agent promotion copy: `data/kinetics_r2.csv`.

Timing parser docs: [`ml/analysis/RUN_LOG_TIMING.md`](../../../ml/analysis/RUN_LOG_TIMING.md).
