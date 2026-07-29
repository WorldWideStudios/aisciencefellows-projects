# Round 2 / version 2 — 10-compound discovery plate

**Round:** 2 · **Version:** 2 (`r2-discovery-v2`)  
**Supersedes:** [`data/screens/2/v1/`](../v1/) (24 compounds)  
**Active robot plate:** pending sign-off → [`data/plate_map_r2.json`](../../../../data/plate_map_r2.json)

---

## Why v2 (24 → 10)

v1 included every tier bucket at full count (4 + 4 + 8 + 8). v2 keeps the **minimum defensible set** for the inhibitor-vs-substrate story:

| Bucket | v1 | v2 | Rationale |
|--------|----|----|-----------|
| Tier-1 inhibitors | 4 | 4 | Must-test — core hypothesis |
| Inhibitor analogs | 4 | 0 | Redundant salts/prodrugs of Tier-1 |
| Substrate controls | 8 | 4 | One per antibiotic class |
| Diverse picks | 8 | 2 | Exploratory — defer rest to later round |

---

## Artifacts

| File | Purpose |
|------|---------|
| [`compound_list.json`](../../../../data/screens/2/v2/compound_list.json) | Canonical 10-compound list with concentrations |
| [`compound_list.csv`](../../../../data/screens/2/v2/compound_list.csv) | Spreadsheet review |
| [`plate_map.json`](../../../../data/screens/2/v2/plate_map.json) | 96-well layout |

---

## 10 compounds @ 50 µM

| Slot | ID | Name | Bucket | Expected |
|------|-----|------|--------|----------|
| 1 | T19860 | Clavulanic Acid | tier1_inhibitor | ≥50% inhibition |
| 2 | T1262 | Tazobactam | tier1_inhibitor | ≥50% inhibition |
| 3 | T6685 | Sulbactam sodium | tier1_inhibitor | ≥50% inhibition |
| 4 | T14081 | Enmetazobactam | tier1_inhibitor | ≥50% inhibition |
| 5 | T1005 | Amoxicillin | substrate_control | <20% inhibition |
| 6 | T1008 | Cephalexin | substrate_control | <20% inhibition |
| 7 | T0224 | Meropenem | substrate_control | <20% inhibition |
| 8 | T0985 | Oxacillin sodium salt | substrate_control | <20% inhibition |
| 9 | T0138 | Cefpiramide acid | diverse_pick | uncertain |
| 10 | T8390 | Cefazolin | diverse_pick | uncertain |

---

## Dropped from v1 (14 compounds)

| IDs | Reason |
|-----|--------|
| T14979, T1631, T13038, T1213 | Analog bucket — redundant with Tier-1 (T1213 is piperacillin, antibiotic not inhibitor) |
| T30787, T67978, T0814, T0366, T6385, TQ0056 | Extra substrates — penicillin/cephalo/carbapenem already covered |
| T0198, T0199, T0234, T1001 | Extra diverse picks — lowest priority |

---

## Plate layout

**42 wells used** (30 sample + 12 controls); rows E–H reserved.

```
        1      2      3      4      5      6      7      8      9     10     11     12
A    veh×6          noTEM1×4          pos×2
B   T19860×3  T1262×3  T6685×3  T14081×3
C   T1005×3   T1008×3   T0224×3   T0985×3
D   T0138×3   T8390×3
E–H  (empty)
```

---

## Promotion

After Philip sign-off:

1. Copy `data/screens/2/v2/plate_map.json` → `data/plate_map_r2.json`
2. Update `pvjthomas/selection_rationale.md` to point at this document
