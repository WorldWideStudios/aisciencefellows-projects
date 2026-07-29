# Round 2 post-run v2 — conclusions

**Generated:** 2026-07-26 20:58 UTC  
**Analysis:** endpoint fallback (`scoring_mode = endpoint`) after slope Q2 fail  
**Spec:** [run2_decision_tree.md](../../../pvjthomas/runs/2/v5/run2_decision_tree.md)

---

## Executive summary

Run 2 v5 kinetic data are usable for **control QC via endpoint A490**, but **not** for a clean
9-compound discovery scorecard. Slope Q2 failed (vehicle and no-TEM-1 both near-flat); endpoint
rescued Q2E and Q3 (clavulanic ~83%). Most sample wells failed the 0–150% score window due to
16 min nitrocefin stagger and high initial absorbance on early-dosed wells.

**Verdict:** Proceed to **human multichannel nitrocefin addition** for substrate priors and tier-1 inhibitors;
do not treat v2 surprise hits (T1005, T0224) as confirmed inhibitors without that retest.

---

## QC gates (v1 slope vs v2 endpoint)

| Gate | v1 (slope) | v2 (endpoint fallback) |
|------|------------|-------------------------|
| Q2 slope | FAIL | FAIL |
| Q2E endpoint range | — | PASS |
| Q3 clavulanic | 107.7% (PASS) | 83.3% (PASS) |
| Scoring mode | slope | endpoint |
| Timing stagger | None min | 16.01 min |

---

## Compound calls

### v1 (slope-only) — superseded

| ID | Median % | Label |
|----|----------|-------|
| T0138 | 61.5 | `novel_hit` |
| T0224 | 100.0 | `surprise_hit` |
| T0985 | 30.8 | `likely substrate` |
| T1005 | 100.0 | `surprise_hit` |
| T1008 | 76.9 | `surprise_hit` |
| T1262 | 84.6 | `confirmed_hit` |
| T14081 | 61.5 | `confirmed_hit` |
| T6685 | 107.7 | `confirmed_hit` |
| T8390 | 30.8 | `borderline` |

### v2 (endpoint) — active

| ID | Median % | Label |
|----|----------|-------|
| T0224 | 97.0 | `surprise_hit` |
| T1005 | 68.2 | `surprise_hit` |
| T6685 | 27.3 | `surprise_miss` |

---

## What changed v1 → v2

- **Hits in v1 not in v2:** T0138, T1008, T1262, T14081, T6685
- **Hits in v2 not in v1:** —
- **Failed wells (v2):** 22 sample wells outside 0–150% endpoint score

Tier-1 inhibitors (T1262, T14081) and most substrates scored as hits on v1 slopes but **failed**
endpoint QC in v2 (A490 above vehicle at aligned read — stagger artifact, not super-activation).

---

## Figures

See [`figures/`](figures/) and [`figure_comparison.md`](figure_comparison.md).

| Figure | Takeaway |
|--------|----------|
| Endpoint bars | Fewer callable compounds; pos ctrl ~83%; surprise hits T1005/T0224 only |
| Stagger timeline | Same as before — 16 min span drives timing artifacts |
| Decision tree | Q2 slope FAIL → endpoint branch; Q3 PASS @ 83% |
| t-SNE | Unchanged — chemical-space rationale for R2 picks |
| R2 vs R3 plates | Unchanged — layout comparison for human multichannel nitrocefin retest plate |

---

## Recommended next steps

1. **Human multichannel nitrocefin addition** — add nitrocefin to all wells at once on substrate priors + tier-1 inhibitors.
2. **Round 3** — kinetics validation plate already designed from v1 calls; revisit picks using v2 skepticism.
3. **Do not advance dose-response** on T1005/T0224 until human multichannel nitrocefin addition confirms inhibition vs delayed substrate turnover.
