# Round 3 / version 1 — legacy confirmation plate (8 compounds, col 8 empty)

**Round:** 3 · **Version:** 1 (`r3-discovery-v1`)  
**Status:** pending sign-off  
**Supersedes:** `data/screens/2/v5/compound_list.json`  
**Canonical list:** [`compound_list.json`](../../../../data/screens/3/v1/compound_list.json)  
**Decision tree:** [`run3_decision_tree.md`](run3_decision_tree.md) — slope QC primary, **endpoint fallback** if Q2 fails (same Q2E/Q3E gates as Run 2)

> **Note:** Run 3 v2 is [deprecated](../../../../data/screens/3/v2-deprecated/DEPRECATED.md). This v1 plate is the active design.

---

## What changed from Run 2 v5

| Aspect | Prior | This version |
|--------|-------|--------------|
| Vehicle controls | 3 @ B3/B7/C11 (v5) | **Removed** |
| QC controls | — | **6** (3× no-TEM-1 + 3× clavulanic) |
| Compounds | 9 (v5) | **8** (T1005 dropped) |
| Col 8 | T1005 | **Empty** |

---

## Compound table (concentrations, class, R2 history)

All eight compounds were on **Run 2 v5** at the concentrations below (T1262 @ 1 µM in both rounds). R2 post-run analysis: [`r2_round_summary_eda.json`](../../../../data/screens/2/post-run/v2/analysis/r2_round_summary_eda.json) (**v2**, endpoint fallback scoring).

| Slot | ID | Name | Bucket | Class | Screen µM | Work µM | R2 wells | R2 QC fail | R2 label | R2 % inhib (med) | R2 A490 end (med) |
|------|-----|------|--------|-------|-----------|---------|----------|------------|----------|------------------|-------------------|
| 1 | T1262 | Tazobactam | tier1_inhibitor | positive | 1.0 | 10.0 | B2, D2, F2 | — | confirmed_hit | 84.6 | 0.214 |
| 2 | T6685 | Sulbactam sodium | tier1_inhibitor | positive | 50 | 500 | B4, D4, F4 | — | confirmed_hit | 107.7 | 0.252 |
| 3 | T14081 | Enmetazobactam | tier1_inhibitor | positive | 50 | 500 | B6, D6, F6 | — | confirmed_hit | 61.5 | 0.301 |
| 4 | T1008 | Cephalexin | substrate_control | negative | 50 | 500 | B10, D10, F10 | B10, D10 | surprise_hit | 76.9† | 0.215 |
| 5 | T0224 | Meropenem | substrate_control | negative | 50 | 500 | C5, E5, G5 | E5, G5 | surprise_hit | 100.0† | 0.060‡ |
| 6 | T0985 | Oxacillin sodium salt | substrate_control | negative | 50 | 500 | C9, E9, G9 | E9, G9 | likely substrate | 30.8 | 0.151 |
| 7 | T0138 | Cefpiramide acid | diverse_pick | unknown | 50 | 500 | C3, E3, G3 | G3 | novel_hit | 61.5† | 0.185 |
| 8 | T8390 | Cefazolin | diverse_pick | unknown | 50 | 500 | C7, E7, G7 | C7, E7 | borderline | 30.8 | 0.183 |

Full table with footnotes: [`compound_table.md`](../../../../data/screens/3/v1/compound_table.md).

Also in this folder: [`compound_table.md`](../../../../data/screens/3/v1/compound_table.md).

---

## Compounds & well layout

| Slot | ID | Name | µM | Wells (triplicate) |
|------|-----|------|-----|-------------------|
| 1 | T1262 | Tazobactam | 1.0 | B2, D2, F2 |
| 2 | T6685 | Sulbactam sodium | 50 | B4, D4, F4 |
| 3 | T14081 | Enmetazobactam | 50 | B6, D6, F6 |
| 4 | T1008 | Cephalexin | 50 | B10, D10, F10 |
| 5 | T0224 | Meropenem | 50 | C5, E5, G5 |
| 6 | T0985 | Oxacillin sodium salt | 50 | C9, E9, G9 |
| 7 | T0138 | Cefpiramide acid | 50 | C3, E3, G3 |
| 8 | T8390 | Cefazolin | 50 | C7, E7, G7 |

---

## Controls

| Role | Wells |
|------|-------|
| no-TEM-1 | D3, D7, E11 |
| Clavulanic acid (T19860) @ 50 µM | F3, F7, G11 |

```bash
python ml/scripts/build_screen3.py --version 1
python ml/scripts/build_screen3.py --version 1 --only plate_map images
```
