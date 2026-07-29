# CFPS Master Mix — Make the Enzyme (Part 1 of 3)

This workflow (`workflows/cfps_mastermix.json`) is **Part 1 of the TEM-1 β-lactamase
inhibitor screen: making the enzyme** by cell-free protein synthesis (CFPS). It is
pipetting only and takes you up to a finished, **unsealed** plate. Sealing,
incubation with shaking, and cooling happen after this run.

The same content lives inside the run UI (`canvas/cfps_mastermix_screen.tsx`) as
collapsible "more info" panels — this README is the standalone companion.

---

## How this workflow works

The robot runs these steps in order:

1. **Log the plate map** — prints which wells are Positive / Negative / Sample to the run log.
2. **Pick up the pipette** off its stand.
3. **Build three master-mix tubes** — one each for the positive control, negative
   control, and sample. The robot pipettes **Extract + Buffer + Water** into each tube
   and mixes it. (The DNA is pre-loaded by hand — see *Assumptions*.)
4. **Aliquot each mix** into its painted wells on the flat-bottom plate.
5. **Return the pipette** to its stand.

**Why a master mix?** Each condition is mixed once in a single tube, then split across
its wells — so every replicate of a condition is identical and you pipette far fewer
times. Any volume above the 10 µL pipette maximum is drawn in several strokes
automatically.

**What comes next?** After this run you seal the plate, incubate it with shaking, and
cool. **Part 2** reads sfGFP fluorescence to confirm the enzyme was actually made (the
go / no-go gate). **Part 3** runs the nitrocefin activity screen to measure inhibition.

---

## Assumptions & deck setup

Check each one before you run:

- **DNA is pre-loaded.** Both the sample (plasmid) DNA and the positive-control DNA are
  added **by hand** into their microcentrifuge tubes **before** the run — and those
  tubes are the master-mix tubes. The robot only adds Extract, Buffer, and Water to
  them. The DNA volumes are below the on-deck pipetting minimum (0.5 µL), so the robot
  can't dispense them; the run UI lists the amounts to pre-load.
- **Source plates 1, 2 and 3 are all compounds.** The compound source plates
  (`wellplate_pcr_parts_1`…`_3`) hold the library compounds. They're used by the Part 3
  screen, not by this enzyme build.
- **Everything is built on one flat-bottom plate.** All reactions are assembled on the
  single 96-well flat-bottom plate (`wellplate_96_flatbottom`).
- **Seal goes shiny side up.** When the plate is sealed (downstream, not in this
  workflow), the gas-permeable seal is placed **shiny side up** in the reinforced plate
  stand (`seal_holder_stacked_reinforced`). The gas-permeable seal lets the shaking
  expression step breathe.

---

## The science — TEM-1 β-lactamase inhibitor screen

### Why this matters

Antimicrobial resistance — bacteria surviving the drugs meant to kill them — is rising,
and the world isn't ready for it.

> Approximately 1 in 6 laboratory-confirmed bacterial infections worldwide were
> resistant to antibiotics in 2023. — World Health Organization

**TEM-1** is the archetypal resistance enzyme. Bacteria use it to shred penicillins
before the drug can act — a big reason many antibiotics stopped working. Shut TEM-1 down
and a "dead" antibiotic can get its teeth back, which is exactly what clinical inhibitors
do.

### The scientific question

Which compounds meaningfully reduce TEM-1 activity, and what dose-response patterns do
they show?

### The three workflows

1. **Make the enzyme (this workflow).** Cell-free synthesis of TEM-1.
2. **Confirm it.** Read sfGFP fluorescence to check the enzyme was actually made — a
   go / no-go gate before you spend an assay on it.
3. **Screen it.** Build the assay plate, add compounds and nitrocefin, and read the
   reaction kinetically to measure inhibition.

### Cell-free protein synthesis (CFPS)

CFPS makes protein in a tube — no living cells. A cell extract supplies the transcription
and translation machinery; you add a DNA template and the reaction reads it into protein
in a few hours. (The kit protocol says ~6 h, but green signal has appeared as early as
~30 min.)

### Reading out expression — sfGFP

TEM-1 is expressed *fused* to superfolder GFP (sfGFP), so green fluorescence tells you
protein was actually made. That green signal is the go / no-go gate in Part 2.

### Reading out activity — nitrocefin (Part 3)

Nitrocefin is a chromogenic substrate: intact it's yellow, and when TEM-1 cleaves it, it
turns red (read at A490). The **initial slope of A490 vs. time is the enzyme's velocity**
— inhibit the enzyme and the slope drops.

### The three conditions on this plate

| Condition | Template (DNA) | What it tells you |
|-----------|----------------|-------------------|
| **Positive control** | ~2450 bp plasmid expressing sfGFP only; carries chloramphenicol resistance; supplied at 200 nM (≈323 ng/µL). | The CFPS reaction works — green fluorescence, but *no* β-lactamase activity. |
| **Sample** | The same vector with a cDNA insert encoding an **sfGFP–β-lactamase (TEM-1) fusion**, made by conventional cloning. | The actual enzyme you screen against — green *and* β-lactamase active. |
| **Negative control** | No template (no DNA). | Background — confirms the signal needs DNA and isn't from the extract alone. |

The positive control and sample templates share the same backbone; the sample just adds
the β-lactamase coding sequence to the GFP reporter. That's why both glow green, but only
the sample can chew through nitrocefin in Part 3.

---

## Kit recipe (per 10 µL reference reaction)

The workflow scales these to your chosen per-well volume.

| Reagent | Positive ctrl | Negative ctrl | Sample |
|---------|---------------|---------------|--------|
| Extract (3.33X) | 3 | 3 | 3 |
| Buffer (2.5X) | 4 | 4 | 4 |
| Control DNA (200 nM) | 0.2 | — | — |
| Sample DNA (plasmid) | — | — | derived from stock/final conc. |
| Additives / Water | 2.8 | 3 | fills to 10 |
| **Total** | **10** | **10** | **10** |

DNA rows are **pre-loaded by hand** into the mix tubes (too small to pipette on-deck).
The robot pipettes Extract, Buffer, and Water.

*OpenCFPS™ (SepiaBio) setup.*
