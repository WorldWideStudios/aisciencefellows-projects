# Round 2 post-run analysis — v2 (endpoint fallback)

**Active** analysis for Run 2 v5. Uses the decision-tree macro flow:

1. **Q2 slope QC** — vehicle HOT vs no-TEM-1 FLAT
2. On Q2 fail → **`scoring_mode = endpoint`** (A490 @ t0+600 s, aligned)
3. **Q2E** — endpoint dynamic range (vehicle − no-TEM-1 A490 ≥ 0.02)
4. **Q3** — clavulanic ≥50% on the active metric

| Artifact | Path |
|----------|------|
| Round summary + QC | [`analysis/r2_round_summary_eda.json`](analysis/r2_round_summary_eda.json) |
| Decision report | [`run2_decision_report.md`](run2_decision_report.md) |
| Figures + conclusions | [`figures/`](figures/) · [`conclusions.md`](conclusions.md) · [`figure_comparison.md`](figure_comparison.md) |
| Assay summary (git) | [`../../../assay/run_2_summary.json`](../../../assay/run_2_summary.json) |

## Outcome (v2)

- **Q2 slope:** FAIL → endpoint fallback
- **Q2E endpoint:** PASS (Δ A490 ≈ 0.066)
- **Q3:** PASS (clavulanic ~83% on endpoint)
- Substrate priors no longer spurious surprise hits when endpoint shows catch-up yellow

Regenerate figures + conclusions:

```bash
python ml/scripts/generate_r2_postrun_figures.py
```

Raw execution inputs live in [`../`](../). Supersedes [`../v1/`](../v1/).
