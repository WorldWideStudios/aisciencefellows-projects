# Tier 2 example — Category 2: exclude (assay substrate)

**Compound:** T19709 · Nitrocefin  
**Phase A rule:** Hard-coded ID → `scaffold_class = exclude`, `exclude = true`  
**Source plate:** PHD215176 **g3**

This is **not** a β-lactamase inhibitor. It is the **chromogenic assay substrate** (yellow → red when TEM-1 cleaves it). Included here because TargetMol still mentions β-lactamase in the compound entry — but with the opposite role (substrate for detection, not drug inhibitor).

---

## Where is β-lactamase mentioned?

| Layer | Where | What it says |
|-------|--------|--------------|
| **TargetMol sheet** | `Bioactivity` column (not `Receptor`) | “chromogenic **substrate** and a detection tool for **β-lactamase**” |
| **TargetMol sheet `Receptor`** | `Others` | Does **not** say β-Lactamase |
| **Our Phase A tag** | Hard-coded exclude ID | T19709 → `exclude` — never plate on a screen |

---

## TargetMol sheet entry (raw export)

| Column | Value |
|--------|-------|
| ID | T19709 |
| Name | Nitrocefin |
| Plate / Row / Col | PHD215176 / g / 3 |
| CAS | 41906-86-9 |
| **Receptor** | Others |
| **Target** | Others;Antibacterial;Antibiotic |
| **Bioactivity** | Nitrocefin is a chromogenic **substrate** and a detection tool for **β-lactamase**, featuring high sensitivity and rapid color development. Used for β-lactamase activity detection… |

---

## Our parsed entry — `data/compounds.csv`

```csv
compound_id,name,plate,row,col,scaffold_class,tier,exclude,receptor,target
T19709,Nitrocefin,PHD215176,g,3,exclude,,true,Others,Others;Antibacterial;Antibiotic
```

No tier assigned. `exclude = true` overrides everything else.

---

## Our dossier entry — `data/compound_dossiers.json`

```json
"T19709": {
  "compound_id": "T19709",
  "name": "Nitrocefin",
  "classification": {
    "scaffold_class": "exclude",
    "functional_class": "exclude",
    "tier": null,
    "exclude": true
  },
  "source": { "plate": "PHD215176", "well": "g3" },
  "assay": { "expected_at_50uM": "do not plate" }
}
```

---

## Contrast — Category 3 default (not Tier 1 or exclude)

**T1005 Amoxicillin** shows how the ~97 `antibiotic_substrate` compounds are tagged — from sheet `Receptor`/`Target`, **not** hard-coded IDs:

| Sheet `Receptor` | Sheet `Target` | Phase A tag |
|------------------|----------------|-------------|
| antibiotic; Bacterial | Antibacterial;Antibiotic | `antibiotic_substrate`, tier 3 |

Bioactivity describes **PBP binding** (antibiotic mechanism), not β-lactamase inhibition.

```csv
T1005,Amoxicillin,PHD215176,a,8,antibiotic_substrate,3,false,antibiotic; Bacterial,Antibacterial;Antibiotic
```

Dossier: `functional_class: negative` — expected **<20% inhibition** at 50 µM (substrate control).

---

## Summary: three ways β-lactamase appears

| Category | Example ID | β-lactamase in sheet? | Phase A tag source |
|----------|------------|------------------------|-------------------|
| 1 — inhibitor | T19860 | Receptor + Bioactivity say **inhibitor** | **Hard-coded ID** (7 compounds) |
| 2 — exclude | T19709 | Bioactivity says **substrate for detection** | **Hard-coded ID** (T19709 only) |
| 3 — antibiotic | T1005 | No inhibitor language; PBP/antibiotic | **Default rule** from Receptor/Target |

There is no per-compound TargetMol product webpage in this workflow — metadata lives in the **Google Sheet row** and is copied into **`data/compounds.csv`** and **`data/compound_dossiers.json`**.
