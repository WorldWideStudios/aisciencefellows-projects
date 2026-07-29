# Round 2 post-run analysis — v1 (slope-only)

Frozen analysis snapshot using **slope-based scoring only** (180–480 s aligned window).

| Artifact | Path |
|----------|------|
| Round summary + QC | [`analysis/r2_round_summary_eda.json`](analysis/r2_round_summary_eda.json) |
| Decision report | [`run2_decision_report.md`](run2_decision_report.md) |
| Pattern / LLM context | [`analysis/`](analysis/) |

## Outcome (v1)

- **Q2 slope:** FAIL (vehicle and no-TEM-1 both near-flat)
- **Q3:** FAIL (clavulanic median 25% on slopes)
- Compound calls treated slope flatness as inhibition → spurious `surprise_hit` on substrate priors

Superseded by [`../v2/`](../v2/) which applies endpoint fallback when slope Q2 fails.

Raw execution inputs (kinetics CSV, timing, run log) live in [`../`](../).
