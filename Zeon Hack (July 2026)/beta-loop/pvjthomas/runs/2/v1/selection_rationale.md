# Round 2 / version 1 — discovery plate rationale

**Round:** 2 · **Version:** 1 (`r2-discovery-v1`)  
**Active robot plate:** pending sign-off → [`data/plate_map_r2.json`](../../../../data/plate_map_r2.json)

---

## Artifact layout

Round 2 v1 separates compound selection from well layout:

| File | Purpose |
|------|---------|
| [`compound_list.json`](../../../../data/screens/2/v1/compound_list.json) | Canonical 24-compound screen list (machine-readable) |
| [`compound_list.csv`](../../../../data/screens/2/v1/compound_list.csv) | Same list for spreadsheet review |
| [`plate_map.json`](../../../../data/screens/2/v1/plate_map.json) | 96-well layout derived from the list |

Edit `compound_list.json` first; regenerate `plate_map.json` when concentrations or compound picks change.

---

## Purpose

Discovery screen on a **96-well flat-bottom plate**. Each test compound is plated in **triplicate** (3 adjacent wells). Row A holds plate controls; rows B–G hold samples; row H is empty/reserved.

| Block | Wells | Content |
|-------|-------|---------|
| Controls | A1–A12 | 6× vehicle · 4× no-TEM-1 · 2× clavulanate positive |
| Tier-1 inhibitors | B1–B12 | 4 compounds × 3 |
| Inhibitor analogs | C1–C12 | 4 compounds × 3 |
| Substrate controls | D1–E12 | 8 compounds × 3 |
| Diverse picks | F1–G12 | 8 compounds × 3 |
| Reserved | H1–H12 | Empty |

**Totals:** 84 wells used · 72 sample wells · **24 unique compound IDs**

**Screen concentration:** 50 µM final for all compounds (5 µL of 500 µM working solution into 50 µL assay). T19860 has literature-backed rationale; others use project default pending full curation.

---

## 24 compounds

| Slot | ID | Name | Bucket | Conc (µM) |
|------|-----|------|--------|-----------|
| 1 | T19860 | Clavulanic Acid | tier1_inhibitor | 50 |
| 2 | T1262 | Tazobactam | tier1_inhibitor | 50 |
| 3 | T6685 | Sulbactam sodium | tier1_inhibitor | 50 |
| 4 | T14081 | Enmetazobactam | tier1_inhibitor | 50 |
| 5 | T14979 | Clavulanate lithium | inhibitor_analog | 50 |
| 6 | T1631 | Sulbactam | inhibitor_analog | 50 |
| 7 | T13038 | Sultamicillin | inhibitor_analog | 50 |
| 8 | T1213 | Piperacillin sodium | inhibitor_analog | 50 |
| 9 | T0985 | Oxacillin sodium salt | substrate_control | 50 |
| 10 | T30787 | Cefetamet sodium | substrate_control | 50 |
| 11 | T67978 | Cefuzonam | substrate_control | 50 |
| 12 | T0814 | Ampicillin Trihydrate | substrate_control | 50 |
| 13 | T0366 | Cefadroxil | substrate_control | 50 |
| 14 | T6385 | Amoxicillin Sodium | substrate_control | 50 |
| 15 | TQ0056 | Cefuracetime | substrate_control | 50 |
| 16 | T8390 | Cefazolin | substrate_control | 50 |
| 17 | T0138 | Cefpiramide acid | diverse_pick | 50 |
| 18 | T0198 | Ceftiofur sodium | diverse_pick | 50 |
| 19 | T0199 | Cephradine | diverse_pick | 50 |
| 20 | T0234 | Methicillin sodium salt | diverse_pick | 50 |
| 21 | T1001 | Dicloxacillin Sodium hydrate | diverse_pick | 50 |
| 22 | T1005 | Amoxicillin | diverse_pick | 50 |
| 23 | T1008 | Cephalexin | diverse_pick | 50 |
| 24 | T0224 | Meropenem | diverse_pick | 50 |

---

## Plate map (compact)

```
        1      2      3      4      5      6      7      8      9     10     11     12
A    veh×6          noTEM1×4          pos×2
B   T19860×3  T1262×3  T6685×3  T14081×3
C   T14979×3  T1631×3  T13038×3 T1213×3
D–E  substrate controls ×3 each (8 compounds)
F–G  diverse picks ×3 each (8 compounds)
H    (empty)
```

---

## Promotion

After Philip sign-off:

1. Copy `data/screens/2/v1/plate_map.json` → `data/plate_map_r2.json`
2. Update `pvjthomas/selection_rationale.md` to point at this document
