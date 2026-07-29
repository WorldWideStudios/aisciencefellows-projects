# Hand protocol — Q3 fail (inhibition not detectable)

**Trigger:** Run 2 v5 decision tree **Q3 fails** — **Q2 passed** (3/3 vehicle hot, 3/3 no-TEM-1 flat) but **3/3 clavulanic pos ctrl** median inhibition score **< 50**.

**Goal:** Find why known inhibitor T19860 (clavulanic acid) is not suppressing nitrocefin turnover. Do **not** interpret the 9 discovery compounds until this passes.

**Time:** ~60 min hands-on + 10 min reader kinetics  
**Wells:** **12/96** (hand-pipetted)  
**Robot:** Do not use — you are testing DMSO match, pre-incubation, and clavulanic stock/concentration.

**Related:** [run2_decision_tree.md](run2_decision_tree.md) · [NITROCEFIN_ASSAY.md](../../../NITROCEFIN_ASSAY.md) · R1 validation pattern [`data/screens/1/v2/plate_map.json`](../../../../data/screens/1/v2/plate_map.json)

---

## What Q3 is asking

| Condition | Wells on run 2 | Expect |
|-----------|----------------|--------|
| Vehicle | 3/3 | Inhibition score **0** (reference) |
| No-TEM-1 | 3/3 | Inhibition score **100** (reference) |
| Clavulanic T19860 @ 50 µM | 3/3 | Median score **≥ 50** |

Q3 fails when clavulanic looks like vehicle (score < 20) or is weak/borderline (20–49) despite good enzyme activity.

---

## Plate layout (row C, 50 µL final)

```
     1      2      3      4      5      6      7      8      9     10    11    12
C   V      V      V     NT     NT     NT    CL50   CL50   CL50  CL200 CL200  DMSO
    └─ vehicle ─┘  └─ no-TEM-1 ─┘  └─ clav 50 µM ─┘ └ 200 µM ┘  high DMSO
```

| Well | Label | TEM-1 | Compound | Final conc | Purpose |
|------|-------|-------|----------|------------|---------|
| C1–C3 | **V** | ✓ | DMSO (5 µL matched) | 0 | Normalization (3/3) |
| C4–C6 | **NT** | ✗ | DMSO matched | 0 | Background (3/3) |
| C7–C9 | **CL50** | ✓ | T19860 clavulanic | **50 µM** | Same as run 2 pos ctrl (3/3) |
| C10–C11 | **CL200** | ✓ | T19860 clavulanic | **200 µM** | Diagnostic — should score **≥80** if binding works (2/2) |
| C12 | **DMSO** | ✓ | **Extra DMSO** (match CL200 solvent load) | 0 | Solvent stress control (1/1) |

**DMSO rule:** Every well with compound gets the same DMSO **volume and final %**. C12 gets the same DMSO load as C10–C11 so you can see if solvent alone kills enzyme.

Working solutions (10× final, 5 µL into 50 µL):

| Stock path | Working | Final in well |
|------------|---------|---------------|
| 10 mM T19860 in DMSO | 500 µM | 50 µM (C7–C9) |
| 10 mM T19860 in DMSO | 2 mM | 200 µM (C10–C11) |

---

## Hand steps

1. Pre-warm plate to **25 °C**.
2. Prepare all wells **except nitrocefin**:
   - **C1–C3, C7–C12:** buffer + enzyme + compound or DMSO.
   - **C4–C6:** buffer + DMSO only (no enzyme).
3. **Pre-incubate 10 min RT** — use a timer; this is the #1 Q3 failure mode on robot plates.
4. **t = 0:** Add nitrocefin (25 µL) to **all 12 wells** in one batch.
5. Reader: **120 s equilibration** → A490 kinetic **30 s interval, 600 s** @ 25 °C.
6. Score slopes **180–480 s**; compute inhibition score per well vs median **3/3 V** and **3/3 NT**.

---

## Pass / fail (this mini-plate)

```
score = 100 × (1 − (metric_sample − metric_no_tem1) / (metric_vehicle − metric_no_tem1))
```

Use median **3/3** vehicle and **3/3** no-TEM-1 from **this plate** (C1–C6).

| Check | Wells examined | Pass |
|-------|----------------|------|
| Q2 still OK | 3/3 V vs 3/3 NT | Vehicle hot, no-TEM-1 flat (same as before) |
| Pos ctrl @ 50 µM | 3/3 CL50 (C7–C9) | **Median score ≥ 50** |
| High-dose sanity | 2/2 CL200 (C10–C11) | **Median score ≥ 80** (confirms inhibitor can bind) |
| Not a DMSO artifact | 1/1 DMSO (C12) vs 3/3 V | C12 slope ≈ vehicle (within 2×) |

**Pass Q3 repair:** **≥2/3** CL50 wells score ≥50 **and** **≥1/2** CL200 wells score ≥80.

**Partial pass:** CL200 hits but CL50 misses → concentration or pre-incubation issue; extend pre-incub to 20 min and retest CL50 only (3 wells).

**Fail:** CL200 also flat (scores < 20) → wrong compound, degraded clavulanic, or enzyme not TEM-1 — see diagnosis table.

---

## Diagnosis — if still failing

| Pattern (wells) | Likely cause | Next fix |
|-----------------|--------------|----------|
| **CL50 3/3 flat, CL200 2/2 flat** | Wrong well/stock; clavulanic degraded; not TEM-1 enzyme | Re-pick T19860 from library plate; new DMSO stock; confirm enzyme identity |
| **CL50 3/3 flat, CL200 2/2 hit** | Pre-incub too short @ 50 µM; sub-saturating | **20 min** pre-incub; or raise screen conc to 100 µM for pos ctrl only |
| **CL50 3/3 borderline (20–49), CL200 2/2 hit** | Weak binding at 50 µM under your buffer conditions | Accept for substrate discrimination only if CL200 ≥80; fix robot pre-incub timing |
| **DMSO (C12) flat, V (C1–C3) hot** | DMSO % in compound wells kills enzyme | Match DMSO **exactly** to vehicle; reduce DMSO load if possible |
| **All 9/9 enzyme wells flat** | Enzyme died during setup | Fresh enzyme; shorter setup; cold nitrocefin on ice until add |
| **CL50 0/3, V high, NT flat** | Clavulanic not in well (pipetting) | Confirm source well PHD215176 h7; dye-check pipette |

---

## Variables to test (one at a time)

If first 12-well plate is ambiguous, run **only 3 wells** for the next iteration:

| Iteration | Change | Wells | Pass if |
|-----------|--------|-------|---------|
| A | Pre-incub **20 min** instead of 10 | 3/3 CL50 | Median score ≥ 50 |
| B | Clavulanic **100 µM** final | 3/3 | Median score ≥ 50 |
| C | Add enzyme **with** nitrocefin (no pre-incub) | 3/3 CL50 | Score ≥ 50 → robot pre-incub broken |
| D | Fresh T19860 pin from library | 3/3 CL50 @ 50 µM | Score ≥ 50 → old working solution bad |

---

## After pass

- Record: pre-incub time, clavulanic source well, working solution age, DMSO %.
- Fix robot workflow if hand pass used longer pre-incub or different DMSO match.
- Re-run run 2 discovery plate or accept run 2 data **only** if pos ctrl on original plate can be re-scored after a fix (usually repeat validation row).

---

## Quick record sheet

| Well | Label | Slope | Score | Notes |
|------|-------|-------|-------|-------|
| C1 | V | | 0 ref | |
| C2 | V | | | |
| C3 | V | | | |
| C4 | NT | | 100 ref | |
| C5 | NT | | | |
| C6 | NT | | | |
| C7 | CL50 | | | |
| C8 | CL50 | | | |
| C9 | CL50 | | | |
| C10 | CL200 | | | |
| C11 | CL200 | | | |
| C12 | DMSO | | | |

**Medians:** V = ___ · NT = ___ · CL50 = ___ (score ___) · CL200 = ___ (score ___)

**Outcome:** ☐ Q3 repaired · ☐ Partial — try iteration ___ · ☐ Still failing
