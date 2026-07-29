# Round 2 / version 3 — literature-backed concentrations

**Round:** 2 · **Version:** 3 (`r2-discovery-v3`)  
**Supersedes:** [`data/screens/2/v2/`](../v2/)  
**Canonical concentrations:** [`compound_list.json`](../../../../data/screens/2/v3/compound_list.json)

---

## What changed from v2

Same **10-compound layout** as v2. v3 adds per-compound **screen concentrations**, **concentration_rule** (1–3), and **concentration_reference** from the 2026-07-26 literature search.

| Rule | Meaning |
|------|---------|
| **1** | Literature nitrocefin assay concentration |
| **2** | 10× literature IC50 or Ki |
| **3** | Project default 50 µM |

---

## Concentrations

| Slot | ID | Name | µM | Rule | Source |
|------|-----|------|-----|------|--------|
| 1 | T19860 | Clavulanic Acid | 50 | 1 | literature |
| 2 | T1262 | Tazobactam | 1.0 | 2 | 10x_ic50 |
| 3 | T6685 | Sulbactam sodium | 50 | 3 | project_default |
| 4 | T14081 | Enmetazobactam | 50 | 3 | project_default |
| 5 | T1005 | Amoxicillin | 50 | 3 | project_default |
| 6 | T1008 | Cephalexin | 50 | 3 | project_default |
| 7 | T0224 | Meropenem | 50 | 3 | project_default |
| 8 | T0985 | Oxacillin sodium salt | 50 | 3 | project_default |
| 9 | T0138 | Cefpiramide acid | 50 | 3 | project_default |
| 10 | T8390 | Cefazolin | 50 | 3 | project_default |

---

## Where data lives

- **Per-compound detail (rule + reference):** `compound_list.json` → `compounds[].concentration_reference`
- **Well layout:** `plate_map.json` (concentrations copied from compound list)
- **Manifest:** file index only — does not duplicate compound fields

Promote to robot: copy `plate_map.json` → `data/plate_map_r2.json` after sign-off.
