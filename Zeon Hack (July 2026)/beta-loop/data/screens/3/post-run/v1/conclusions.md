# Round 3 post-run v1 — conclusions

**Generated:** 2026-07-26 22:05 UTC  
**Scoring mode:** `endpoint`  
**Spec:** [run3_decision_tree.md](../../../pvjthomas/runs/3/v1/run3_decision_tree.md)

---

## Executive summary

Run 3 v1 kinetic data passed **Q1, Q1T, Q2E, and Q3** with sync manual nitrocefin dosing (~2 min span).
Slope Q2 failed (substrate and no-TEM-1 slopes both near-flat), so compound calls use **endpoint fallback**
(`endpoint`). Positive control clavulanic scored 99.4%.

**Tier-1 inhibitors (T1262, T6685, T14081) all confirmed hits.** T0224 (substrate prior) scored as a
**surprise_hit** at ~98% — priority dose-response before treating as a true inhibitor.

T1008 substrate control wells largely **failed** the 0–150% score window (8 failed wells total),
so substrate-anchor QC should be interpreted cautiously despite Q2E passing on endpoint dynamic range.

---

## QC gates

| Gate | Result | Notes |
|------|--------|-------|
| Q1 data | PASS | ≥24/30 assay wells |
| Q1T sync dose | PASS | 2.0 min span |
| Q2 slope | FAIL | substrate vs no-TEM-1 slope separation |
| Q2E endpoint | PASS | Δ A490 = 0.158 |
| Q3 clavulanic | PASS | 99.4% |

---

## Compound calls

| ID | Median % | Label |
|----|----------|-------|
| T1262 | 100.0 | `confirmed_hit` |
| T0224 | 98.1 | `surprise_hit` |
| T14081 | 98.1 | `confirmed_hit` |
| T6685 | 91.8 | `confirmed_hit` |
| T0985 | 13.3 | `confirmed_substrate` |
| T0138 | 8.2 | `inactive` |
| T8390 | 4.4 | `inactive` |

---

## Recommended next steps

1. **8-point dose-response on T0224** — surprise hit on a substrate prior; confirm before advancing.
2. **Advance tier-1 confirmed hits** (T1262, T6685, T14081) to dose-response design.
3. **Investigate T1008 well failures** — substrate anchor wells B10/D10/F10 failed scoring; check replicates and raw traces.
4. **Do not treat T0138/T8390 as hits** — inactive on endpoint scoring.

See [`run3_decision_report.md`](../run3_decision_report.md) for full per-well detail.
