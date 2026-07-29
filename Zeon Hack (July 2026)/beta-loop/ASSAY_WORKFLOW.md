# Assay workflow — purified TEM-1 nitrocefin screen

Wet-lab reference for the TEM-1 β-lactamase inhibitor screen (Track A): **what goes in each well, how robot steps connect, and what the readouts mean**.

**Plan change (Run 2 onward):** The original hack sequence was CFPS → GFP gate → nitrocefin screen. That path was **deferred**. Round 2 and current robotics work **start from purified TEM-1** (commercial or lab-prep stock), dilute on-deck, and run the nitrocefin inhibition screen directly — no cell-free expression plate and no GFP gate on the critical path.

**Related docs**

- [PLAN.md](PLAN.md) — project plan, timeline, validation gates
- [ml/analysis/RUN_LOG_TIMING.md](ml/analysis/RUN_LOG_TIMING.md) — run log timing parser, workflow `timing_phases`, CI baselines
- [pvjthomas/NITROCEFIN_ASSAY.md](pvjthomas/NITROCEFIN_ASSAY.md) — controls, scoring, DMSO rules
- [mastermix/workflows/tem1_activity_screen.json](mastermix/workflows/tem1_activity_screen.json) — Run 2 robot workflow (implemented)
- [mastermix/.zeon/CFPS_README.md](mastermix/.zeon/CFPS_README.md) — *deferred* Part 1 CFPS detail (Rob)

**Workflow status (current)**

| Step | Zeon workflow | Status |
|------|---------------|--------|
| Dilution + nitrocefin screen | `mastermix/workflows/tem1_activity_screen.json` | **Implemented** — Run 2 |
| CFPS expression | `mastermix/workflows/cfps_mastermix.json` | Deferred (not on Run 2 path) |
| GFP gate | `workflows/gfp_read.json` | Deferred |

---

## Overview (current path)

```
Purified TEM-1 stock          Robot: dilutions + assay setup          Plate reader
(on deck / cold block)    →    tem1_activity_screen workflow      →    A490 kinetics
100 ng/µL stock                  compound plate + nitrocefin
```

| Stage | Question answered | Material | Readout |
|-------|-------------------|----------|---------|
| **On-deck prep** | Are working solutions at the right concentration? | Purified TEM-1, compound library, BLB, nitrocefin stock | Run log / QC |
| **Screen** | Does each compound inhibit TEM-1? | 96-well assay plate | Yellow → **red** (A490 slope) |

**Critical path (Run 2):** Validation plate passes (vehicle active, no-TEM-1 flat, clavulanate inhibits) → Round 2 library screen → kinetic analysis. No GFP gate required.

---

## Robot workflow — `tem1_activity_screen`

Single workflow covers dilution prep through nitrocefin addition. Enzyme source is **purified TEM-1**, not CFPS lysate.

### High-level robot phases

1. **Prepare dilutions** — TEM-1 stock (100 ng/µL) → intermediate (1 ng/µL) → working (0.1 ng/µL); compound/control working solutions on PCR dilution plate; matched vehicle (5% DMSO).
2. **Assay plate loading** — TEM-1 working solution (20 µL) to enzyme wells; BLB to no-enzyme controls; vehicle and compounds (5 µL each) from dilution plate.
3. **Plate mix** — whole-plate shaker (~1 min).
4. **Pre-incubation** — compound + enzyme at RT (workflow default 10 min; Run 2 log showed 2 min — confirm for production).
5. **Nitrocefin** — prepare 100 µM working solution just-in-time; dispense 25 µL per well by condition (substrate clock starts).
6. **Save run folder** — log, timing summary, `nitrocefin_timing.json` for per-well t0.

Plate map and compound IDs: Run 2 v5 layout — see [`pvjthomas/runs/2/v5/run2_decision_tree.md`](pvjthomas/runs/2/v5/run2_decision_tree.md).

---

## Nitrocefin screen (inhibition assay)

**Goal:** Measure whether each compound reduces TEM-1 β-lactamase activity using nitrocefin kinetics.

### What nitrocefin measures

Nitrocefin is a chromogenic β-lactam **substrate**. TEM-1 cleaves it → visible color shift **yellow → red** → **A490 increases over time**.

| Slope | Meaning |
|-------|---------|
| Fast A490 rise | High TEM-1 activity (vehicle control) |
| Slow rise | Inhibition |
| Flat | Strong inhibition, no enzyme, or failed well |

**Metric:** initial slope of A490 vs time (kinetic window aligned to per-well nitrocefin t0 when timing metadata is available).

### Screen plate contents (50 µL final per well)

| # | Component | Typical volume | Notes |
|---|-----------|----------------|--------|
| 1 | Assay buffer (BLB) | in enzyme / no-enzyme prep | Na phosphate ~pH 7; often 0.1% BSA |
| 2 | **TEM-1 (purified)** | **20 µL @ 0.1 ng/µL** | **2 ng TEM-1 per well**; omit in no-TEM-1 wells |
| 3 | Compound or vehicle | 5 µL | From working soln on dilution plate; **50 µM final** in Round 1 / Run 2 |
| 4 | Nitrocefin | 25 µL | Add **last** — starts the reaction clock |

This is the **Run 2 default**. Purified enzyme removes CFPS extract, buffer, and DNA carryover from the screen well.

### Mixing order (do not reorder)

```
TEM-1 working solution (or BLB for no-enzyme)
  → add compound OR DMSO-matched vehicle
  → plate mix + pre-incubate RT
  → prepare nitrocefin working solution
  → add nitrocefin to ALL wells (track time per well)
  → plate reader: A490 kinetics
```

Nitrocefin addition starts the clock. Stagger across conditions is logged in `nitrocefin_timing.json` for slope alignment.

### Controls (every screen plate)

| Well type | Enzyme | Compound | Expected |
|-----------|--------|----------|----------|
| **Vehicle** | ✓ | DMSO only (matched %) | Max slope — normalization reference |
| **No-TEM-1** | ✗ | DMSO or compound | Min slope — background |
| **Positive** (recommended) | ✓ | Clavulanic acid @ 50 µM (T19860) | Strong inhibition vs vehicle |

### Scoring

Normalize each well to controls on the **same plate**:

```
pct_inhibition = 100 × (1 - (slope_sample - slope_no_tem1) / (slope_vehicle - slope_no_tem1))
```

Use **median** of 3/3 replicate wells per control type and per compound. See [`ml/analysis/kinetics.py`](ml/analysis/kinetics.py) and the Run 2 decision tree.

| Result @ 50 µM | Interpretation |
|----------------|----------------|
| ≥ 50% | Hit → dose-response in later rounds |
| < 20% + antibiotic scaffold | Likely **substrate**, not inhibitor |

---

## What “enzyme prep” means (Run 2)

**Enzyme prep = purified TEM-1 in BLB**, prepared on-deck from stock:

| Step | Concentration | Location |
|------|---------------|----------|
| Stock | 100 ng/µL | Cold block (e.g. `hole_1`) |
| Intermediate | 1 ng/µL | Cold block (e.g. `hole_2`) |
| Working | **0.1 ng/µL** | Cold block (e.g. `hole_8`) |
| Assay well | 20 µL working → **2 ng/well** | 96-well screen plate |

There is **no CFPS lysate**, no sfGFP fusion, and no Sepia kit components in the screen well. This simplifies interpretation: A490 signal reflects purified β-lactamase activity in defined buffer, not expression machinery carryover.

**Handoff from wet lab to robot:** place purified TEM-1 stock, nitrocefin stock, BLB, DMSO, and compound library plates on the deck per world layout; robot handles dilutions and plating.

---

## Validation before library screens

Run a minimal validation plate before committing a full library plate. Antibiotics are **not required** to prove the assay works.

| Wells | Role | Pass criterion |
|-------|------|----------------|
| 3× Vehicle | enzyme + DMSO + nitrocefin | Strong linear A490 slope |
| 3× No-TEM-1 | nitrocefin, no enzyme | Flat (background) |
| 3× Clavulanate @ 50 µM | known inhibitor | ≥ 50% inhibition vs vehicle |

Philip signs off → run library screen. See [NITROCEFIN_ASSAY.md](pvjthomas/NITROCEFIN_ASSAY.md) for DMSO matching rules.

---

## Original plan — CFPS → GFP gate (deferred)

The documents below describe the **initial** three-part pipeline. It remains in the repo for Rob’s CFPS workflow and a possible future return to expression-based enzyme, but **Run 2 did not use it**.

```
Part 1: CFPS          Part 2: GFP gate       Part 3: Nitrocefin screen
(make enzyme)    →    (confirm expression) → (measure inhibition)
     │                       │                         │
  CFPS plate              same plate              new plate
  (expression)            (read green)            (read red @ A490)
```

| Part | Question | Status |
|------|----------|--------|
| **1 — CFPS** | Can we synthesize TEM-1 cell-free (OpenCFPS / sfGFP–TEM-1 fusion)? | Workflow exists; not on Run 2 path |
| **2 — GFP gate** | Was fusion expressed (green fluorescence on CFPS plate)? | Planned only |
| **3 — Screen from lysate** | Inhibition using **CFPS lysate aliquot** (~20 µL) instead of purified enzyme | Superseded by purified-TEM-1 path for Run 2 |

### Why we deferred CFPS for Run 2

- **Time:** CFPS incubation + GFP read add hours before any inhibition data.
- **Complexity:** Lysate carryover (extract, buffer, DNA) complicates assay interpretation and timing QC.
- **Run 2 goal:** Close the loop on compound scoring, kinetics, and agent-driven Round 3 plate design using a **known-good enzyme source**.

CFPS may return later if the team wants expression-based enzyme for demo narrative or cost reasons. Until then, treat [`cfps_mastermix.json`](mastermix/workflows/cfps_mastermix.json) and GFP gate as **optional upstream**, not part of the active assay workflow doc path.

<details>
<summary>CFPS robot steps (reference — <code>cfps_mastermix</code>)</summary>

1. Log plate map (positive / negative / sample wells).
2. Pick up pipette.
3. Build three master-mix tubes: Extract + Buffer + Water, mix in place.
4. Aliquot into destination wells on a 96-well flat-bottom plate.
5. Operator pre-loads DNA by hand (below ~0.5 µL robot minimum).
6. After run: seal → incubate → cool → GFP read (Part 2, never implemented on Run 2).

Three CFPS conditions: positive (sfGFP only), sample (sfGFP–TEM-1 fusion), negative (no DNA). Compound library plates are for the nitrocefin screen only, not expression.

Full detail: [mastermix/.zeon/CFPS_README.md](mastermix/.zeon/CFPS_README.md).

</details>

---

## Open questions (Run 2 / production)

- [ ] Pre-incubation time on hardware (workflow default 10 min vs 2 min observed in one run log)
- [ ] Nitrocefin prep overlap with pre-incubation (substrate stability vs total wall time)
- [ ] Plate reader kinetic schedule and export format for `kinetics_r*.csv`
- [ ] When / whether to re-enable CFPS + GFP for demo or cost reasons

---

## One-line demo explanation (Run 2)

> We dilute purified TEM-1 on the robot, add each β-lactam compound, start the clock with nitrocefin, and measure whether the red product forms fast (substrate / antibiotic) or slow (true inhibitor like clavulanate).
