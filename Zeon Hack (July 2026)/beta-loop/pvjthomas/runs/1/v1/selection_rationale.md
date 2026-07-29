# Round 1 plate — compound selection rationale

**Run:** 1 · **Version:** 1 · **Label:** `r1-discovery-v1`  
**Owner:** Philip (pvjthomas)

| Copy | Path |
|------|------|
| Versioned rationale (immutable) | [`pvjthomas/runs/1/v1/selection_rationale.md`](runs/1/v1/selection_rationale.md) |
| Versioned plate map | [`data/screens/1/v1/plate_map.json`](../data/screens/1/v1/plate_map.json) |
| Active plate map (robot) | [`data/plate_map_r1.json`](../data/plate_map_r1.json) |
| Run manifest | [`data/screens/1/v1/manifest.json`](../data/screens/1/v1/manifest.json) |

**Library:** TargetMol β-Lactam Compound Library-A (105 compounds) · [`data/compounds.csv`](../data/compounds.csv)

This document explains **every well** on the Round 1 discovery plate for teammates (Rob/Chang/ML). Use it for QC, demo narrative, and R1→R2 decisions.

---

## Assay in one sentence

TEM-1 cleaves nitrocefin → A490 rises. **True β-lactamase inhibitors** (clavulanate-class) slow that rise; **β-lactam antibiotics** are hydrolyzed as substrates and usually do **not** block nitrocefin cleavage.

**Screen concentration:** 50 µM final (5 µL of 500 µM working solution into 50 µL assay).  
**Hit threshold:** ≥50% inhibition vs vehicle (normalized to no-TEM-1 background).

**Excluded from all test wells:** **T19709 (nitrocefin)** — it is the chromogenic assay substrate, not a compound to screen.

---

## Plate layout (36 wells used)

| Row | Wells | Content |
|-----|-------|---------|
| **A** | A1–A12 | Plate controls (6 vehicle · 4 no-TEM-1 · 2 clavulanate positive) |
| **B** | B1–B4 | Tier-1 inhibitors (4 scaffold reps) |
| **C** | C1–C4 | Inhibitor analogs (+1 wildcard) |
| **D** | D1–D8 | Substrate controls (intentional negatives) |
| **E** | E1–E8 | Diverse picks (scaffold exploration) |
| *F–H* | — | Empty / reserved |

```
        1      2      3      4      5      6      7      8      9     10     11     12
A    veh    veh    veh    veh    veh    veh   noE    noE    noE    noE   T19860 T19860
B   T19860 T1262  T6685  T14081
C   T14979 T1631  T13038 T1213
D   T1005  T1008  T1305  T0814L T1122  T1063  T0199  T0198
E   T0224  T1029  T7387  T1037  T13926 T0989  T21369 T124492
```

---

## Plate controls (Row A)

These wells are **not** part of the 24-compound discovery set. They anchor normalization and pass/fail QC.

| Well(s) | Role | Enzyme? | Compound | Expected A490 slope | Pass if… |
|---------|------|---------|----------|---------------------|----------|
| A1–A6 | `vehicle` | ✓ | DMSO matched | **Max** | Strong enzymatic signal |
| A7–A10 | `no_tem1` | ✗ | DMSO matched | **Min** | Flat / background only |
| A11–A12 | `pos-ctrl-clavaculin` | ✓ | T19860 clavulanic acid @ 50 µM | **Low** | ≥50% inhibition vs vehicle |

**DMSO rule:** Every compound well and every vehicle well must carry the **same DMSO fraction**. Library stock is 10 mM in DMSO; do not let vehicle wells run DMSO-free.

**If clavulanate fails but vehicle works → debug the assay** (DMSO matching, pre-incubation, enzyme prep), not compound selection.

---

## Bucket 1 — Tier-1 inhibitors (B1–B4)

Four distinct **known β-lactamase inhibitor scaffolds** in the library. All are suicide/covalent inhibitors with published class A β-lactamase activity. **Expect hits.**

| Well | ID | Name | Scaffold | Source plate · well | Why this compound |
|------|-----|------|----------|---------------------|-------------------|
| B1 | **T19860** | Clavulanic acid | Clavulanate (5-membered β-lactam + oxazolidine) | PHD215176 · h7 | Gold-standard positive; also duplicated as A11–A12 controls |
| B2 | **T1262** | Tazobactam | Penicillanic acid sulfone + triazole | PHD215176 · b10 | Zosyn component; distinct from sulbactam side chain |
| B3 | **T6685** | Sulbactam sodium | Penicillanic acid sulfone | PHD215176 · f2 | Unasyn component; minimal side chain = inhibitor not antibiotic |
| B4 | **T14081** | Enmetazobactam | Penicillanic acid sulfone + methyl-triazolium | PHD215176 · f7 | Newer clinical inhibitor (AAI101); tests 4th chemotype |

---

## Bucket 2 — Inhibitor analogs (C1–C4)

Same biology as Tier-1, but **salt forms, prodrugs, or inhibitor-adjacent structures**. Expect most to inhibit; C4 is a deliberate wildcard.

| Well | ID | Name | Relationship | Source plate · well | Notes |
|------|-----|------|--------------|---------------------|-------|
| C1 | **T14979** | Clavulanate lithium | Li⁺ salt of T19860 core | PHD215176 · g6 | Tests counterion / formulation effects |
| C2 | **T1631** | Sulbactam (Na⁺) | Same core as T6685 | PHD215177 · a10 | Redundant scaffold rep; confirms reproducibility |
| C3 | **T13038** | Sultamicillin | Prodrug: ampicillin ↔ sulbactam ester | PHD215177 · b10 | May show mixed behavior after cleavage — watch kinetics |
| C4 | **T1213** | Piperacillin sodium | Ureidopenicillin (Zosyn partner antibiotic) | PHD215176 · b7 | **+1 pick:** β-lactamase-labeled extended penicillin; thematic pair to tazobactam, likely **substrate** not inhibitor |

> **+1 pick note:** GNINA docking has not been run yet (`dock_score` column empty). T1213 was chosen manually as the tazobactam clinical partner. Swap for a GNINA top hit once scores land.

---

## Bucket 3 — Substrate controls (D1–D8)

**Intentional negatives.** These are β-lactam **antibiotics** that TEM-1 hydrolyzes. They should show **<20% inhibition** — proving the assay discriminates inhibitors from substrates.

| Well | ID | Name | Class | Source plate · well |
|------|-----|------|-------|---------------------|
| D1 | **T1005** | Amoxicillin | Penicillin (aminopenicillin) | PHD215176 · a8 |
| D2 | **T1008** | Cephalexin | 1st-gen cephalosporin | PHD215176 · a9 |
| D3 | **T1305** | Ceftazidime | 3rd-gen cephalosporin | PHD215176 · b3 |
| D4 | **T0814L** | Ampicillin | Penicillin (aminopenicillin) | PHD215176 · b4 |
| D5 | **T1122** | Cephalothin sodium | 1st-gen cephalosporin | PHD215176 · b2 |
| D6 | **T1063** | Ticarcillin disodium | Extended-spectrum penicillin | PHD215176 · a11 |
| D7 | **T0199** | Cephradine | 1st-gen cephalosporin | PHD215176 · a4 |
| D8 | **T0198** | Ceftiofur sodium | 3rd-gen cephalosporin (vet) | PHD215176 · a3 |

**Coverage:** penicillins + cephalosporins, narrow and extended spectrum, 1st and 3rd generation.

---

## Bucket 4 — Diverse picks (E1–E8)

**Exploration wells** — scaffolds not already in the substrate bucket. GNINA scores not available yet; selected manually for **structural diversity** (carbapenems, monobactams, intermediates, clinical oddities). Most are expected substrates; any surprise hit is worth follow-up in R2.

| Well | ID | Name | Class | Source plate · well | Why included |
|------|-----|------|-------|---------------------|--------------|
| E1 | **T0224** | Meropenem | Carbapenem | PHD215177 · a3 | Different fused ring system |
| E2 | **T1029** | Aztreonam | Monobactam | PHD215177 · a5 | Monocyclic β-lactam — unusual scaffold |
| E3 | **T7387** | Ceftaroline fosamil | 5th-gen cephalosporin (anti-MRSA) | PHD215177 · b4 | Very bulky acyl side chain |
| E4 | **T1037** | Doripenem monohydrate | Carbapenem | PHD215176 · c8 | Second carbapenem representative |
| E5 | **T13926** | Tigemonam | Monobactam (oral) | PHD215176 · h3 | Second monobactam |
| E6 | **T0989** | 7-Aminocephalosporanic acid (7-ACA) | β-lactam intermediate | PHD215176 · g11 | No full side chain — edge case |
| E7 | **T21369** | Mecillinam | Amdinopenicillin | PHD215177 · b6 | Unique amidine side chain |
| E8 | **T124492** | Imipenem | Carbapenem | PHD215176 · h6 | Foundational carbapenem |

> Replace any E-row compound with GNINA top scores once batch docking completes.

---

## Expected outcomes (for QC and demo)

| Bucket | Wells | Expected @ 50 µM | R2 action if confirmed |
|--------|-------|------------------|------------------------|
| Tier-1 inhibitors | B1–B4 | ≥50% inhibition | 8-point dose-response |
| Inhibitor analogs | C1–C3 | ≥50% inhibition | DR if hit; investigate C3/C4 if borderline |
| Substrate controls | D1–D8 | <20% inhibition | Drop; document as confirmed substrates |
| Diverse picks | E1–E8 | Mostly <20%; surprises retest | DR on unexpected hits |
| Positive controls | A11–A12 | ≥50% inhibition | Assay must pass or stop |

**Normalization formula** (same plate):

```
pct_inhibition = 100 × (1 - (slope_sample - slope_no_tem1) / (slope_vehicle - slope_no_tem1))
```

Use median of A1–A6 for vehicle and A7–A10 for no-TEM-1.

---

## Enrichment story (for pitch)

> We selected 24 compounds from a 105-compound β-lactam library: 8 inhibitor-class wells (4 scaffolds + 4 analogs) and 16 antibiotic/exploration wells (8 substrate controls + 8 diverse picks). Forward literature search identified 7 known inhibitors in-library; we placed all of them on-plate. Substrate controls are **predicted negatives** — if they stay hot while clavulanate inhibits, the closed-loop selection worked.

---

## Robot lookup (Chang)

For each `compound_id` in `plate_map_r1.json`, transfer from source plate using [`data/compounds.csv`](../data/compounds.csv):

| Field | CSV columns |
|-------|-------------|
| Source plate | `plate` (PHD215176 / PHD215177 / PHD215178) |
| Source well | `row` + `col` (lowercase row letter) |
| Stock | 10 mM in DMSO, 50 µL |

**Roles in JSON:**

| `role` | Robot behavior |
|--------|----------------|
| `vehicle` | Add matched DMSO; **add enzyme** |
| `no_tem1` | Add matched DMSO; **skip enzyme** |
| `pos-ctrl-clavaculin` | Add T19860 @ 50 µM; **add enzyme** |
| `sample` | Add compound @ 50 µM; **add enzyme** |

---

## Related docs

- [NITROCEFIN_ASSAY.md](NITROCEFIN_ASSAY.md) — mixing order, DMSO rule, scoring
- [COMPOUND_SELECTION.md](COMPOUND_SELECTION.md) — full selection strategy
- [PLAN.md](../PLAN.md) — file contract, two-round loop
- [ml/CLOSED_LOOP.md](../ml/CLOSED_LOOP.md) — ML/agent handoffs

---

*Run 1 · v1 · drafted 2026-07-25. Philip sign-off pending before Round 1 screen.*
