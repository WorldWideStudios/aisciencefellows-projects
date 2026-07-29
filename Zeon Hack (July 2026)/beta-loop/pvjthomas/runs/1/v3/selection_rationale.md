# Round 1 / version 3 — discovery plate rationale

**Round:** 1 · **Version:** 3 (`r1-discovery-v3`)  
**Supersedes:** `data/screens/1/v1/` (single-replicate layout)  
**Active robot plate:** still v2 validation until sign-off → [`data/plate_map_r1.json`](../../../../data/plate_map_r1.json)

See [`data/README.md`](../../../../data/README.md) for rounds vs versions.

---

## Purpose

Full Round 1 discovery screen on a **96-well flat-bottom plate**. Each test compound is plated in **triplicate** (3 adjacent wells) for replicate statistics. Row A holds plate controls; rows B–G hold samples; row H is empty/reserved.

| Block | Wells | Content |
|-------|-------|---------|
| Controls | A1–A12 | 6× vehicle · 4× no-TEM-1 · 2× clavulanate positive |
| Tier-1 inhibitors | B1–B12 | 4 compounds × 3 |
| Inhibitor analogs | C1–C12 | 4 compounds × 3 |
| Substrate controls | D1–E12 | 8 compounds × 3 |
| Diverse picks | F1–G12 | 8 compounds × 3 |
| Reserved | H1–H12 | Empty |

**Totals:** 84 wells used · 72 sample wells · 24 compound slots (23 unique IDs — T0366 appears in both substrate and diverse buckets)

**Screen concentration:** 50 µM final (5 µL of 500 µM working solution into 50 µL assay).

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

Each `×3` = three adjacent wells with the same `compound_id` and `replicate` 1/2/3.

---

## Analysis notes

- **Hit call:** median `pct_inhibition` across triplicate ≥ 50% vs vehicle (use A1–A6 vehicle, A7–A10 no-TEM-1).
- **Replicate QC:** flag wells where replicate CV > threshold before averaging.
- **Normalization:** same formula as v1 — see [`../v1/selection_rationale.md`](../v1/selection_rationale.md).

---

## Promotion

After v2 validation passes and Philip signs off:

1. Copy `data/screens/1/v3/plate_map.json` → `data/plate_map_r1.json`
2. Update `pvjthomas/selection_rationale.md` to point at this document

---

## Related files

- Frozen plate map: [`data/screens/1/v3/plate_map.json`](../../../../data/screens/1/v3/plate_map.json)
- Draft (same layout): [`ml/workflows/compound_selection/plate_map_r2_draft.json`](../../../../ml/workflows/compound_selection/plate_map_r2_draft.json)
- Full compound rationale (v1 prose): [`../v1/selection_rationale.md`](../v1/selection_rationale.md)
