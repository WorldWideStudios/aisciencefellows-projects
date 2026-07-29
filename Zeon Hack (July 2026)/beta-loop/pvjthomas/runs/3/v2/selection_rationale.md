# Round 3 / version 2 — surprise & unknown retest plate (6 compounds)

> **DEPRECATED** — Do not use. Active design is [Run 3 v1](../v1/selection_rationale.md). See [`DEPRECATED.md`](../../../../data/screens/3/v2-deprecated/DEPRECATED.md).

**Round:** 3 · **Version:** 2 (`r3-discovery-v2`)  
**Status:** deprecated  
**Supersedes:** `data/screens/3/v1/compound_list.json`  
**Superseded by:** [`data/screens/3/v1/`](../../../../data/screens/3/v1/)  
**Canonical list:** [`compound_list.json`](../../../../data/screens/3/v2-deprecated/compound_list.json)

---

## What changed from v1

| Aspect | Prior | This version |
|--------|-------|--------------|
| Vehicle controls | 3 @ B3/B7/C11 (v5) | **Removed** |
| QC controls | — | **6** (3× no-TEM-1 + 3× clavulanic) |
| Selection policy | v1 mixed | **Cut expected ±, add unknowns** |
| Compounds | 8 | **6** (4 cut, 1 re-added, 1 new) |
| Cut (expected +) | T1262, T6685, T14081 on v1 | **Removed** |
| Cut (expected −) | T0985 on v1 | **Removed** |
| Add | — | **T1005** (surprise), **T0198** (new) |

---

## Selection policy

Run 3 v2 follows: **cut expected positives, cut expected negatives, retest interesting/unknowns, triplicate everything.**

### Cut from v1

| ID | Name | Run 2 label | Why cut |
|----|------|-------------|---------|
| T1262 | Tazobactam | confirmed_hit | Expected tier-1 inhibitor — validated |
| T6685 | Sulbactam sodium | confirmed_hit | Expected tier-1 inhibitor — validated |
| T14081 | Enmetazobactam | confirmed_hit | Expected tier-1 inhibitor — validated |
| T0985 | Oxacillin | likely substrate | Expected negative — behaved as substrate |

### Kept / added

| ID | Name | Run 2 label | Why on plate |
|----|------|-------------|--------------|
| T1008 | Cephalexin | surprise_hit | Substrate that inhibited — retest |
| T0224 | Meropenem | surprise_hit | Substrate that inhibited — retest |
| T0138 | Cefpiramide | novel_hit | Diverse unknown with signal |
| T1005 | Amoxicillin | surprise_hit | Substrate prior but inhibited in R2 |
| T8390 | Cefazolin | borderline | Weak/ambiguous — retest |
| T0198 | Ceftiofur sodium | **new** | Tier-3 diverse — not screened in R2 |

---

## Compounds & well layout

| Slot | ID | Name | µM | Wells (triplicate) |
|------|-----|------|-----|-------------------|
| 1 | T1008 | Cephalexin | 50 | B2, D2, F2 |
| 2 | T0224 | Meropenem | 50 | B4, D4, F4 |
| 3 | T0138 | Cefpiramide acid | 50 | B6, D6, F6 |
| 4 | T1005 | Amoxicillin | 50 | B8, D8, F8 |
| 5 | T8390 | Cefazolin | 50 | B10, D10, F10 |
| 6 | T0198 | Ceftiofur sodium | 50.0 | C5, E5, G5 |

---

## Controls

| Role | Wells |
|------|-------|
| no-TEM-1 | D3, D7, E11 |
| Clavulanic acid (T19860) @ 50 µM | F3, F7, G11 |

```bash
python ml/scripts/build_screen3.py --version 2
python ml/scripts/build_screen3.py --version 2 --only plate_map images
```
