# Tier 1 example — Category 1: β-lactamase inhibitor

**Compound:** T19860 · Clavulanic Acid  
**Phase A rule:** Hard-coded ID → `scaffold_class = inhibitor`, `tier = 1`  
**Source plate:** PHD215176 **h7**

---

## Where is “β-lactamase inhibitor” tagged?

**Two places — only one drives Phase A classification.**

| Layer | Where | What it says |
|-------|--------|--------------|
| **TargetMol sheet (vendor metadata)** | Google Sheet columns `Receptor` and `Bioactivity` | Receptor = `β-Lactamase;Fungal` · Bioactivity calls it a “potent bacterial **beta-lactamase inhibitor**” |
| **Our Phase A tag (authoritative)** | Hard-coded compound ID list in project rules | T19860 is one of 7 IDs always tagged `inhibitor` / Tier 1 — **not** parsed automatically from the sheet |

Phase A does **not** scan the sheet for “β-Lactamase” in `Receptor`. The seven Tier 1 IDs were chosen manually; the sheet metadata happens to agree for clavulanate.

**Sheet URL (library tab):**  
https://docs.google.com/spreadsheets/d/1b7UuzXu_auqoq2hFT81X3UuRutxxWxZW/edit?gid=372192752#gid=372192752  
(Find row with ID `T19860`, plate PHD215176, well h7.)

---

## TargetMol sheet entry (raw export)

| Column | Value |
|--------|-------|
| ID | T19860 |
| Name | Clavulanic Acid |
| Plate / Row / Col | PHD215176 / h / 7 |
| CAS | 58001-44-8 |
| **Receptor** | **β-Lactamase;Fungal** |
| **Target** | Antibacterial;Antibiotic;Antifungal |
| **Bioactivity** | Clavulanic Acid(RX-10100)… is a **potent bacterial beta-lactamase inhibitor** used in the study of infections caused by bacteria… |

Synonyms on sheet: BRL 14151; MM-14151; RX-10100; …

---

## Our parsed entry — `data/compounds.csv`

```csv
compound_id,name,plate,row,col,scaffold_class,tier,exclude,receptor,target
T19860,Clavulanic Acid,PHD215176,h,7,inhibitor,1,false,β-Lactamase;Fungal,Antibacterial;Antibiotic;Antifungal
```

Note: `receptor` and `target` are copied from the sheet. **`scaffold_class` and `tier` come from our hard-coded rule**, not from parsing `Receptor`.

---

## Our dossier entry — `data/compound_dossiers.json`

```json
"T19860": {
  "compound_id": "T19860",
  "name": "Clavulanic Acid",
  "classification": {
    "scaffold_class": "inhibitor",
    "functional_class": "positive",
    "tier": 1,
    "exclude": false
  },
  "source": { "plate": "PHD215176", "well": "h7" }
}
```

`functional_class: positive` = expected nitrocefin **hit** at 50 µM (≥50% inhibition).

---

## Same pattern on another Tier 1 ID (T1262 Tazobactam)

| Sheet `Receptor` | Sheet `Bioactivity` (excerpt) |
|------------------|-------------------------------|
| Antibiotic; Bacterial; **β-Lactamase** | “…inhibits the action of bacterial **beta-lactamases**.” |

Also hard-coded as `inhibitor` / tier 1 — same Category 1 rule.

---

## Trap: “β-Lactamase” in Receptor ≠ inhibitor

Many **antibiotic substrates** also list `β-Lactamase` in `Receptor` (e.g. T1213 Piperacillin: `Antibiotic; Bacterial; β-Lactamase`) because they are **hydrolyzed** by the enzyme, not inhibitors. Phase A leaves those as `antibiotic_substrate` unless they are one of the seven hard-coded IDs.

See [tier2example.md](tier2example.md) for Category 2 (exclude) and contrast with default substrate tagging.
