# Nitrocefin assay cheat sheet — Philip

Quick reference for TEM-1 β-lactamase inhibitor screen (Track A). Share with Rob/Chang for `workflows/screen.json`.

**Related:** [COMPOUND_SELECTION.md](COMPOUND_SELECTION.md) (classification taxonomy) · [PLAN.md](../PLAN.md) · [`data/compounds.csv`](../data/compounds.csv)

> **Plate controls, library classes, and functional mapping:** see [COMPOUND_SELECTION.md § Compound & plate classification](COMPOUND_SELECTION.md#compound--plate-classification-reference).

---

## What this assay measures

Nitrocefin is a chromogenic β-lactam **substrate**. TEM-1 cleaves it → color shift yellow → red → **A490 increases over time**.

- **Fast A490 slope** = high TEM-1 activity (vehicle control)
- **Slow slope** = inhibition
- **Flat slope** = strong inhibition, no enzyme, or failed well

**Metric:** initial slope of A490 vs time (first ~3–5 min of linear phase).

---

## What you mix in each well (50 µL final)

| # | Component | Typical volume | Notes |
|---|-----------|----------------|--------|
| 1 | **Assay buffer (BLB)** | fills to volume | Na phosphate ~pH 7; often 0.1% BSA |
| 2 | **TEM-1 enzyme** | ~20 µL | CFPS prep or purified dilution; **omit in no-TEM-1 wells** |
| 3 | **Compound or vehicle** | 5 µL | From 10 mM DMSO library stock; working soln = **10× final conc** |
| 4 | **Nitrocefin** | 25 µL | Add **last** — starts reaction |

**Purified-enzyme example (from brief):**
- 20 µL enzyme (0.1 ng/µL → 2 ng/well)
- 5 µL inhibitor or matched vehicle
- 25 µL nitrocefin working solution
- **= 50 µL**

**Round 1 screening concentration:** 50 µM final compound → 500 µM working solution (5 µL into 50 µL = 10× dilution).

---

## Mixing order (do not reorder)

```
buffer / enzyme prep
    → add compound OR vehicle (DMSO-matched)
    → pre-incubate RT (~10 min)
    → add nitrocefin to ALL wells (track time)
    → plate reader: A490 every 30 s for several minutes
```

Nitrocefin addition **starts the clock**. Staggered adds = staggered kinetics — robot should batch nitrocefin add then read immediately.

---

## Controls (every plate)

| Well type | Enzyme | Compound | Expected slope |
|-----------|--------|----------|----------------|
| **Vehicle** | ✓ | DMSO only (matched %) | **Max** — normalization reference |
| **No-TEM-1** | ✗ | DMSO or compound | **Min** — background |
| **Positive** (recommended) | ✓ | Clavulanic acid @ 50 µM (T19860) | Strongly reduced vs vehicle |

---

## Minimal validation plate (before Round 1)

**Antibiotics are not required** to prove TEM-1 activity — only enzyme, nitrocefin, and the three control types below.

| Well(s) | Role | What to prove |
|---------|------|----------------|
| 4× Vehicle | enzyme + DMSO + nitrocefin | TEM-1 is **active** |
| 2× No-TEM-1 | nitrocefin, no enzyme | Signal is **enzymatic** |
| 2× Clavulanate (T19860) @ 50 µM | known inhibitor | **Inhibition** is detectable |
| 2× Ampicillin (T1005) @ 50 µM | *optional* | Substrate shows **low** inhibition (not required to pass) |

**Pass gate:** vehicle slope high · no-TEM-1 flat · clavulanate ≥50% inhibition → Philip signs off → Round 1 OK.

---

## Clavulanate vs antibiotics in the library

| | Clavulanate (inhibitor) | Antibiotics (~97 in library) |
|---|-------------------------|------------------------------|
| **What it is** | β-lactamase **inhibitor** | β-lactam **antibiotics** (substrates) |
| **TEM-1** | Enzyme blocked | Enzyme hydrolyzes the drug |
| **Nitrocefin assay** | Strong inhibition expected | Weak/none expected |
| **Validation plate** | **Required** (positive control) | **Not required** |
| **Round 1 plate** | **Must test** (Tier 1) | **~8 as negative controls** — prove assay discriminates |

**Do not skip all antibiotics in Round 1** — they make the inhibitor hits meaningful. **Do not require them** to validate the assay itself.

---

## DMSO rule (critical)

- Library stock: **10 mM in DMSO**
- **Same DMSO concentration** in every inhibitor well and every vehicle well
- If compound well has 5 µL of 10 mM DMSO stock → vehicle well gets equivalent DMSO volume/concentration
- Otherwise slope changes may be solvent artifact, not inhibition

---

## Do NOT put in test wells

| Item | Why |
|------|-----|
| **Nitrocefin (T19709)** from compound library | It *is* the substrate — exclude from `plate_map` |
| CFPS master mix / DNA / Sepia reagents | Expression only — use enzyme **output** in screen |
| Acetic acid during kinetics | Stops/alters enzyme activity mid-read (endpoint quench only, if validated) |

---

## Scoring (for analysis / agent)

Normalize each well to controls on the **same plate**:

**Slope mode** (Q2 pass):

```
pct_inhibition = 100 × (1 - (slope_sample - slope_no_tem1) / (slope_vehicle - slope_no_tem1))
```

**Endpoint mode** (Q2 fail — fallback):

```
pct_inhibition = 100 × (A490_vehicle - A490_sample) / (A490_vehicle - A490_no_tem1)
```

Endpoint A490 is read at **t0 + 600 s** per well (aligned to nitrocefin add time). Slopes are still computed for Q2 QC and `timing_suspect` flags.

| Result | Interpretation |
|--------|----------------|
| ≥ 50% @ 50 µM | Hit → consider dose-response in R2 |
| < 20% + antibiotic scaffold | Likely **substrate**, not inhibitor (expected for many library compounds) |
| Tier 1 inhibitor flat | **Assay failure** — debug before trusting other wells |

---

## Plate map → robot (Chang)

From `data/plate_map_r{N}.json`:

- `compound_id` → lookup `plate`, `row`, `col` in [`data/compounds.csv`](../data/compounds.csv)
- `role`: `sample` | `vehicle` | `no_tem1` | `pos-ctrl-clavaculin`
- `concentration_uM`: final in-well concentration after all mixing

---

## Kickoff confirmations (still open)

- [ ] CFPS lysate **directly** in assay, or separate enzyme prep?
- [ ] Nitrocefin stock concentration (brief has 20 µM vs 20 mM typo)
- [ ] Exact BLB recipe and pre-incubation time validated on-site
- [ ] Plate reader export format for `kinetics_r*.csv`

---

## One-line demo explanation

> We mix TEM-1 enzyme with each β-lactam compound, let it pre-bind, then add nitrocefin and watch whether the red product forms fast (substrate/antibiotic) or slow (true inhibitor like clavulanate).
