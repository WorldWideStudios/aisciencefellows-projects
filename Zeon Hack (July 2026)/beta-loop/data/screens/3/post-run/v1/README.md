# Round 3 post-run analysis — v1

**Active** analysis for Run 3 v1 (`r3-discovery-v1`). **Complete.**

Scoring uses **substrate-control anchor** (T1008, T0224, T0985) — no vehicle wells. Decision tree: [`pvjthomas/runs/3/v1/run3_decision_tree.md`](../../../../pvjthomas/runs/3/v1/run3_decision_tree.md).

## Outcome (v1)

- **Q1:** PASS
- **Q1T sync dose:** PASS (~2 min span, operator estimate)
- **Q2 slope:** FAIL → **endpoint fallback**
- **Q2E endpoint:** PASS (Δ A490 ≈ 0.158)
- **Q3:** PASS (clavulanic ~99% on endpoint)

**Verdict:** Tier-1 inhibitors confirmed; **T0224 surprise_hit** — priority dose-response.

Regenerate:

```bash
python ml/scripts/generate_run3_artifacts.py
python ml/scripts/generate_r3_postrun_figures.py
```

| Artifact | Path |
|----------|------|
| Round summary + QC | [`analysis/r3_round_summary_eda.json`](analysis/r3_round_summary_eda.json) |
| Decision report | [`run3_decision_report.md`](run3_decision_report.md) |
| Figures + conclusions | [`figures/`](figures/) · [`conclusions.md`](conclusions.md) |
| Assay summary (git) | [`../../../assay/run_3_summary.json`](../../../assay/run_3_summary.json) |

Raw execution inputs live in [`../`](../).
