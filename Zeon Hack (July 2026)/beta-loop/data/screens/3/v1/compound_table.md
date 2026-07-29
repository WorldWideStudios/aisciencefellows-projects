# Run 3 v1 — compound table

**Round:** 3 · **Version:** 1 (`r3-discovery-v1`)  
**Plate map:** [`plate_map.json`](plate_map.json) · **Compound list:** [`compound_list.json`](compound_list.json)  
**Rationale:** [`selection_rationale.md`](../../../pvjthomas/runs/3/v1/selection_rationale.md)

---


All eight compounds were on **Run 2 v5** at the concentrations below (T1262 @ 1 µM in both rounds). R2 post-run analysis: [`r2_round_summary_eda.json`](../../2/post-run/v2/analysis/r2_round_summary_eda.json) (**v2**, endpoint fallback scoring).

| Slot | ID | Name | Bucket | Class | Screen µM | Work µM | R2 wells | R2 QC fail | R2 label | R2 % inhib (med) | R2 A490 end (med) | R3 wells |
|------|-----|------|--------|-------|-----------|---------|----------|------------|----------|------------------|-------------------|----------|
| 1 | T1262 | Tazobactam | tier1_inhibitor | positive | 1.0 | 10.0 | B2, D2, F2 | — | confirmed_hit | 84.6 | 0.214 | B2, D2, F2 |
| 2 | T6685 | Sulbactam sodium | tier1_inhibitor | positive | 50 | 500 | B4, D4, F4 | — | confirmed_hit | 107.7 | 0.252 | B4, D4, F4 |
| 3 | T14081 | Enmetazobactam | tier1_inhibitor | positive | 50 | 500 | B6, D6, F6 | — | confirmed_hit | 61.5 | 0.301 | B6, D6, F6 |
| 4 | T1008 | Cephalexin | substrate_control | negative | 50 | 500 | B10, D10, F10 | B10, D10 | surprise_hit | 76.9† | 0.215 | B10, D10, F10 |
| 5 | T0224 | Meropenem | substrate_control | negative | 50 | 500 | C5, E5, G5 | E5, G5 | surprise_hit | 100.0† | 0.060‡ | C5, E5, G5 |
| 6 | T0985 | Oxacillin sodium salt | substrate_control | negative | 50 | 500 | C9, E9, G9 | E9, G9 | likely substrate | 30.8 | 0.151 | C9, E9, G9 |
| 7 | T0138 | Cefpiramide acid | diverse_pick | unknown | 50 | 500 | C3, E3, G3 | G3 | novel_hit | 61.5† | 0.185 | C3, E3, G3 |
| 8 | T8390 | Cefazolin | diverse_pick | unknown | 50 | 500 | C7, E7, G7 | C7, E7 | borderline | 30.8 | 0.183 | C7, E7, G7 |

**Footnotes**

- † Median % inhibition uses all R2 replicate wells in EDA; only **one** non-failed rep for T1008 (F10), T0224 (C5), T0138 (C3, E3).
- ‡ C5 alone shows strong inhibition (A490 ≈ 0.06); failed reps E5/G5 had high endpoint absorbance — treat Meropenem as ambiguous pending R3 retest.
- R2 enzyme QC failed (wells Q2, Q3); nine sample wells flagged `failed_wells` — interpret single-rep hits cautiously.

### Per-replicate R2 % inhibition

| ID | R2 wells | % inhib per well |
|----|----------|------------------|
| T1262 | B2, D2, F2 | 84.6, 53.8, 92.3 |
| T6685 | B4, D4, F4 | 130.8, 84.6, 107.7 |
| T14081 | B6, D6, F6 | 61.5, 76.9, 30.8 |
| T1008 | B10†, D10†, F10 | failed, failed, 76.9 |
| T0224 | C5, E5†, G5† | 100.0, failed, failed |
| T0985 | C9, E9†, G9† | 30.8, failed, failed |
| T0138 | C3, E3, G3† | 100.0, 23.1, failed |
| T8390 | C7†, E7†, G7 | failed, failed, 30.8 |

† = R2 QC failed well

### Dropped from v1 (was on R2 v5)

| ID | Name | R2 label | R2 wells | Why dropped |
|----|------|----------|----------|-------------|
| T1005 | Amoxicillin | surprise_hit (ambiguous) | B8, D8, F8 | Col 8 left empty; R2 kinetics messy — not a clean inhibitor retest candidate |

