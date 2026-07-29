# Future experiments — TEM-1 nitrocefin screen

**Owner:** Philip (pvjthomas)  
**Context:** Plate design for fixed compound list on 96-well format (50 µL/well, nitrocefin kinetics).  
**Related:** [ASSAY_WORKFLOW.md](ASSAY_WORKFLOW.md) · [COMPOUND_SELECTION.md](pvjthomas/COMPOUND_SELECTION.md) · [NITROCEFIN_ASSAY.md](pvjthomas/NITROCEFIN_ASSAY.md)

Grouped by **when to run** and **what decision each experiment supports**. Assumes a fixed compound set, 50 µL/well, nitrocefin kinetics, 3 replicates unless noted.

---

## Phase 0 — Assay validation (run before discovery)

| # | Experiment | Wells | What you vary | Pass if | Decision |
|---|------------|-------|---------------|---------|----------|
| **E0.1** | Vehicle control | 4 | TEM-1 + DMSO + nitrocefin | Strong linear A490 slope | Assay has enzyme activity |
| **E0.2** | No-TEM-1 background | 2 | Nitrocefin, no enzyme | Flat slope | Signal is enzymatic |
| **E0.3** | Positive control | 2 | Clavulanate T19860 @ 50 µM | ≥50% inhibition vs vehicle | Inhibition is detectable |
| **E0.4** | Optional substrate demo | 2 | Ampicillin T1005 @ 50 µM | <20% inhibition | Mechanism story works (not required to pass) |

**Gate:** E0.1–E0.3 pass → proceed to discovery. If E0.3 fails, fix protocol (DMSO, pre-incubation, enzyme prep) before using extra wells for anything else.

---

## Phase 1 — Core discovery screen (fixed compound list)

| # | Experiment | Compounds | Conc | Reps | Purpose |
|---|------------|-----------|------|------|---------|
| **E1.1** | Tier-1 inhibitor panel | T19860, T1262, T6685, T14081 | 50 µM | 3 | Confirm known positives; compare relative potency |
| **E1.2** | Substrate negative panel | e.g. T1005, T1008, T0224, T0985 | 50 µM | 3 | Confirm antibiotics don’t inhibit nitrocefin cleavage |
| **E1.3** | Unknown / diverse picks | Remaining slots (e.g. T0138, T8390, …) | 50 µM | 3 | Discovery — look for surprise hits |
| **E1.4** | On-plate controls (every plate) | Vehicle, no-TEM-1, clavulanate | 0 / 0 / 50 µM | 4–6 / 2–4 / 1–2 | Normalization + QC |

**Primary readout:** `pct_inhibition` vs vehicle (same plate).

**Classification rules:**

- ≥50% → hit → candidate for R2 characterization
- 20–50% → borderline → retest or mini-DR
- <20% + substrate class → confirmed negative
- ≥50% + substrate class → **surprise hit** → prioritize in R2

---

## Phase 2 — Use extra wells (same compounds only)

Run after E1 is laid out, filling empty rows in priority order. No new compound IDs.

| # | Experiment | Compound(s) | Design | Wells (typ.) | Scientific output |
|---|------------|---------------|--------|--------------|-------------------|
| **E2.1** | Clavulanate mini dose-response | T19860 only | 3, 12, 100, 200 µM × 3 reps *(50 µM from E1.1)* | 12–15 | Partial IC50 curve vs literature Ki (~0.85 µM) |
| **E2.2** | Tier-1 replicate boost | T19860, T1262, T6685, T14081 | 50 µM × 4th rep each | 4 | Tighter stats on positives |
| **E2.3** | Unknown replicate boost | 2–3 uncertain picks from E1.3 | 50 µM × 4th rep | 2–3 | Better call on borderline compounds |
| **E2.4** | Dual-conc confirm (unknowns only) | 1–2 picks from E1.3 | 5 µM × 3 reps *(50 µM from E1.3)* | 3–6 | Dose-dependent vs artifact; skip on substrates |
| **E2.5** | Plate-position QC | Vehicle + clavulanate | Scatter in rows D–F | 4–6 | Catch edge/row drift |
| **E2.6** | Pre-incubation comparison *(stretch)* | T19860 only | 1 min vs 10 min pre-incub @ 50 µM × 3 | 6 | Suicide-inhibitor mechanism (optional) |

**Recommended fill order:** E2.1 → E2.2 → E2.4 (on unknowns) → E2.5 → E2.3 → E2.6.

---

## Phase 3 — Round 2 (data-driven; after E1 analysis)

| # | Experiment | Trigger | Design | Output |
|---|------------|---------|--------|--------|
| **E3.1** | Full inhibitor dose-response | Any Tier-1 ≥50% @ 50 µM | 8-point log scale: 3–400 µM on best inhibitor | IC50 + fit vs literature |
| **E3.2** | Comparative DR | Clear potency spread among Tier-1 | 8-point on top 2 inhibitors | Rank clavulanate vs tazobactam vs enmetazobactam |
| **E3.3** | Surprise-hit DR | Substrate-class compound ≥50% | 8-point DR on that compound | Novel finding + follow-up story |
| **E3.4** | Borderline retest | 20–50% @ 50 µM | Single-point @ 10 µM × 3 | Confirm weak hit vs noise |
| **E3.5** | Assay debug panel | Tier-1 fails but vehicle OK | Repeat E0.1–E0.3 + enzyme prep variants | Fix protocol before interpreting E1 |

R2 plate should look visibly different from R1 (dose-response layout vs single-point grid) — closed-loop demo.

---

## Phase 4 — Analysis & closed-loop outputs

| # | Experiment | Input | Deliverable |
|---|------------|-------|-------------|
| **E4.1** | Enrichment analysis | E1.1 vs E1.2 results | Hit rate Tier-1 vs substrates |
| **E4.2** | Agent validation | Predicted `functional_class` vs measured | “Predicted negative, confirmed” table |
| **E4.3** | Hero curve | E2.1 or E3.1 kinetics | IC50 plot for pitch |
| **E4.4** | Heatmap | All E1 compounds × reps | Inhibition matrix by bucket |
| **E4.5** | R2 plate design | E4.1–E4.2 | Agent-generated `plate_map_r2.json` |

---

## Minimum viable set (if time/wells are tight)

1. **E0.1–E0.3** — validation
2. **E1.1 + E1.2 + E1.3 + E1.4** — core discovery
3. **E2.1** — clavulanate mini-DR on spare wells
4. **E3.1** — full DR on best inhibitor after analysis

That gives: assay proof → inhibitor/substrate contrast → one kinetic curve → closed loop.

---

## Suggested well budget (one 96-well plate)

| Block | Experiments | ~Wells |
|-------|-------------|--------|
| Row A | E1.4 controls | 12 |
| Rows B–D | E1.1 + E1.2 + E1.3 (11 compounds × 3) | 33 |
| Rows E–F | E2.1 clavulanate mini-DR | 12–15 |
| Row G | E2.2 + E2.4 + E2.5 | 10–15 |
| Row H | Empty or E2.6 stretch | 0–6 |

Adjust row assignments to exact compound count; experiment IDs stay the same.

---

## Design notes (from plate planning)

- **Single-point @ 50 µM** is the primary R1 screen; dual 50 + 5 µM is only worth it on 1–2 uncertain picks, not on substrate controls.
- **Extra wells without new compounds:** prioritize clavulanate mini-DR, then Tier-1 extra reps, then QC controls.
- **Most interesting scientific output:** inhibitor vs substrate contrast in R1, then dose-response on the best inhibitor (or surprise hit) in R2.
