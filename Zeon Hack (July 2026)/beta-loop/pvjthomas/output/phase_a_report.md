# Phase A — library inventory report

**Owner:** Philip (pvjthomas) · **Status:** Complete  
**Date:** 2026-07-25  
**Next:** [Phase B ADK pipeline](../COMPOUND_SELECTION.md#phase-b--adk-implementation-done) (forward / reverse / bridge)

Phase A is a one-time **library inventory** pass: parse the TargetMol β-lactam sheet into structured CSV, apply rule-based tags, and emit per-compound dossiers. No literature search, docking, or agent orchestration — that is Phase B.

---

## Source

| Item | Value |
|------|-------|
| Vendor library | [TargetMol Beta-Lactam Compound Library-A](https://docs.google.com/spreadsheets/d/1b7UuzXu_auqoq2hFT81X3UuRutxxWxZW/edit?gid=372192752#gid=372192752) |
| Sheet gid | `372192752` |
| Source plates | PHD215176 (80 wells), PHD215177 (22), PHD215178 (3) |
| Stock | 10 mM in DMSO, 50 µL per well |
| Compounds parsed | **105** |

---

## Classification rules

Rules are applied in order. First match wins.

### 1. Hard-coded β-lactamase inhibitors (Tier 1)

Seven compound IDs are always tagged `inhibitor`, `tier = 1`, regardless of TargetMol metadata:

| compound_id | name | plate | well |
|-------------|------|-------|------|
| T19860 | Clavulanic Acid | PHD215176 | h7 |
| T14979 | Clavulanate lithium | PHD215176 | g6 |
| T6685 | Sulbactam sodium | PHD215176 | f2 |
| T1631 | Sulbactam | PHD215177 | a10 |
| T1262 | Tazobactam | PHD215176 | b10 |
| T14081 | Enmetazobactam | PHD215176 | f7 |
| T13038 | Sultamicillin | PHD215177 | b10 |

These are known TEM-1 β-lactamase inhibitors in the library. Expected nitrocefin assay behavior at 50 µM: **≥50% inhibition**.

### 2. Exclude assay substrate

| compound_id | name | plate | well | reason |
|-------------|------|-------|------|--------|
| T19709 | Nitrocefin | PHD215176 | g3 | Chromogenic **assay substrate** (yellow → red with TEM-1). Not a screen compound. |

Tagged `exclude`, `exclude = true`, no tier.

### 3. Default: antibiotic substrate

All remaining compounds (~97) are tagged `antibiotic_substrate`, `tier = 3`.

Classification uses TargetMol sheet columns **`Receptor`** and **`Target`**, which consistently describe antibacterial / PBP-binding antibiotics rather than β-lactamase inhibitors. Examples:

- T0138 (Cefpiramide): Receptor `PBPs` · Target `Antibacterial;Antibiotic`
- T0198 (Ceftiofur sodium): Receptor `Antibacterial; Antibiotic; Bacterial` · Target includes `Antibacterial;Antibiotic`

These compounds are hydrolyzed by TEM-1 as **substrates**. Expected at 50 µM: **<20% nitrocefin inhibition** — intentional negative controls in Round 1.

### 4. Dossiers — `functional_class` mapping

[`data/compound_dossiers.json`](../../data/compound_dossiers.json) carries a unified assay vocabulary derived from Phase A tags:

| `scaffold_class` (Phase A) | `functional_class` (dossier) | Count |
|----------------------------|------------------------------|-------|
| `inhibitor` | `positive` | 7 |
| `antibiotic_substrate` | `negative` | 97 |
| `exclude` | `exclude` | 1 |

Each dossier entry also records source plate/well, storage pointers for literature/docking/assay artifacts, and placeholders for Phase B+ enrichment.

---

## Results summary

| `scaffold_class` | Count | Tier | `exclude` | Role in screen |
|------------------|-------|------|-----------|----------------|
| `inhibitor` | 7 | 1 | false | Positive controls / must-test hits |
| `antibiotic_substrate` | 97 | 3 | false | Substrate controls / expected negatives |
| `exclude` | 1 | — | true | Never plate (nitrocefin) |
| **Total** | **105** | | | |

---

## Outputs

| File | Description |
|------|-------------|
| [`data/compounds.csv`](../../data/compounds.csv) | Full library index — SMILES, plate/well, `scaffold_class`, `tier`, `exclude`, TargetMol `receptor`/`target` |
| [`data/compound_dossiers.json`](../../data/compound_dossiers.json) | Per-compound summaries with `classification.functional_class` |
| [`data/LIBRARY.md`](../../data/LIBRARY.md) | Column schema and re-export instructions |

Phase A bootstrap IDs are preserved in Phase B reverse tooling (`ml/agent/tools/reverse.py` → `TIER1_INHIBITOR_IDS`, `EXCLUDE_IDS`) so RDKit re-tagging does not overwrite known inhibitors or nitrocefin.

---

## What Phase A does not cover

- Literature matching (Phase B **forward**)
- RDKit SMARTS re-classification (Phase B **reverse**)
- Tanimoto analog bridging (Phase B **bridge**)
- Plate design or tier merge (Phase B **merger**)

See [PLAN.md § Compound list generation](../../PLAN.md#compound-list-generation-phase-a--phase-b) and [DIAGRAMS.md § Phase naming](../../DIAGRAMS.md#phase-naming-two-schemes).

---

## Handoff

**Phase A complete.** Proceed to Phase B scaffold classify (forward pass done; reverse / bridge / merge as needed).
