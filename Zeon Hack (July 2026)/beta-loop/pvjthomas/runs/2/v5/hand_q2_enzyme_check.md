# Hand protocol — Q2 fail (enzyme not working)

**Trigger:** Run 2 v5 decision tree **Q2 fails** — vehicle and no-TEM-1 look **similar** (both flat, both high, or no separation).

**Goal:** In one short session, answer: *Is TEM-1 active? Is the signal enzymatic?* Do **not** plate discovery compounds until this passes.

**Time:** ~45 min hands-on + 10 min reader kinetics  
**Wells:** **10/96** (single row, hand-pipetted)  
**Robot:** Do not use — mix and read by hand so you can vary enzyme batch and timing deliberately.

**Related:** [run2_decision_tree.md](run2_decision_tree.md) · [NITROCEFIN_ASSAY.md](../../../NITROCEFIN_ASSAY.md)

---

## What Q2 is asking

| Condition | Wells | Expect if enzyme OK |
|-----------|-------|---------------------|
| **Vehicle** (TEM-1 + DMSO + nitrocefin) | 3/3 | **HIGH** A490 slope |
| **No-TEM-1** (no enzyme + nitrocefin) | 3/3 | **LOW / flat** A490 slope |

Q2 fails when **3/3 vehicle** and **3/3 no-TEM-1** cannot be separated.

---

## Plate layout (row B, 50 µL final)

```
     1      2      3      4      5      6      7      8      9     10
B   V      V      V     NT     NT     NT    NF     NF    V+     NT+
    └─ vehicle ─┘  └─ no-TEM-1 ─┘ └ nitrocefin only ┘ └─ +enzyme after ─┘
```

| Well | Label | TEM-1 | Compound | Nitrocefin | Purpose |
|------|-------|-------|----------|------------|---------|
| B1–B3 | **V** | ✓ | DMSO (matched) | ✓ last | Primary vehicle (3/3) |
| B4–B6 | **NT** | ✗ | DMSO (matched) | ✓ last | Primary no-TEM-1 (3/3) |
| B7–B8 | **NF** | ✗ | — | ✓ only | Nitrocefin + buffer background (2/2) |
| B9 | **V+** | ✓ added **after** 10 min | DMSO | ✓ at t=0 | Late enzyme add — tests dead nitrocefin vs dead enzyme |
| B10 | **NT+** | ✗ | — | ✓ | Same as NT; paired sanity |

Use **fresh enzyme aliquot** for B1–B3 and B9 if the run-2 batch is suspect. Label tube on the plate map.

---

## Reagents (same as main screen)

| Component | Volume / well | Notes |
|-----------|---------------|--------|
| Assay buffer (BLB) | to 50 µL | Same batch as run 2 |
| TEM-1 enzyme | ~20 µL | **Try fresh thaw** if Q2 failed on robot plate |
| DMSO vehicle | 5 µL | Match clavulanic plates: same % as 5 µL of 10 mM stock path |
| Nitrocefin working soln | 25 µL | Add **last**, same stock as run 2 |

---

## Hand steps

1. **Pre-warm** plate to **25 °C** on reader (same as [kinetic_schedule.json](kinetic_schedule.json)).
2. To **B1–B3, B9** (vehicle): buffer + enzyme + DMSO → **10 min RT pre-incubation**.
3. To **B4–B6, B10** (no-TEM-1): buffer + DMSO only (no enzyme) → 10 min RT.
4. To **B7–B8** (nitrocefin-only): buffer only → 10 min RT.
5. **t = 0:** Add nitrocefin to **all 10 wells** as fast as possible (multichannel or repeat pipette).
6. **B9 only:** Immediately after nitrocefin, add enzyme (simulates “enzyme never worked in pre-mix”).
7. Close lid → **120 s equilibration** → kinetic read **A490 every 30 s for 600 s** (same as run 2).
8. Export CSV — need time column + A490.

---

## Pass / fail (this mini-plate)

Score slope in **180–480 s** window (same as run 2).

| Check | Wells | Pass |
|-------|-------|------|
| Vehicle active | 3/3 (B1–B3) | Median slope **clearly higher** than 3/3 no-TEM-1 |
| Signal enzymatic | 3/3 NT vs 2/2 NF | NT ≈ NF (both flat) — color is not “nitrocefin alone drifting” |
| Separation margin | 3/3 V vs 3/3 NT | Vehicle median at least **3×** no-TEM-1 slope (rule of thumb) |

**Pass Q2 repair:** **≥2/3** vehicle wells hot **and** **≥2/3** no-TEM-1 wells flat → enzyme OK; debug robot/DMSO on main plate separately.

**Fail:** still no separation → work through diagnosis table below before re-running run 2.

---

## Diagnosis — if still failing

| Pattern (wells) | Likely cause | Next fix |
|-----------------|--------------|----------|
| **10/10 flat** | Nitrocefin dead, wrong wavelength, or reader issue | New nitrocefin aliquot; confirm **490 nm**; read open-well color by eye (yellow → red?) |
| **10/10 high** | Non-enzymatic drift, buffer pH, contaminated buffer | Fresh BLB; check pH ~7; new plate |
| **V 3/3 flat, NT 3/3 flat** | Enzyme dead or not added | New enzyme prep; confirm concentration; test **B9** (late add) |
| **V 3/3 high, NT 3/3 high** | Enzyme in no-TEM-1 wells, or NT not truly enzyme-free | Re-pipette NT wells; new tips; separate reservoir |
| **V+ (B9) high, V (B1–B3) flat** | Pre-incubation enzyme unstable | Shorter pre-incub; add enzyme with nitrocefin instead |
| **NF (B7–B8) high** | Nitrocefin autohydrolysis / chemical background | Lower nitrocefin conc; fresh stock |
| **V hot, early compounds flat, pos ctrl flat** | Real inhibition on early-dosed wells | Normal — timing alignment confirms (see [run2_decision_tree.md](run2_decision_tree.md) Step 2b) |
| **V hot, early compounds flat, pos ctrl hot** | Stagger artifact on substrates | Shorten stagger or sync nitrocefin; see decision tree Step 2b (`timing_suspect`) |

Flat vs HOT criteria and `timing_suspect` labels: [run2_decision_tree.md](run2_decision_tree.md) § Signal classification.

---

## After pass

- Note enzyme lot, thaw time, and pre-incub time on the plate record.
- Re-run run 2 **only** if this hand plate passes Q2-equivalent checks.
- Link result in `data/assay/` or lab notebook — do not trust run 2 sample wells from the failed plate.

---

## Quick record sheet

| Well | Slope (180–480 s) | Notes |
|------|-------------------|-------|
| B1 | | |
| B2 | | |
| B3 | | |
| B4 | | |
| B5 | | |
| B6 | | |
| B7 | | |
| B8 | | |
| B9 | | |
| B10 | | |

**Outcome:** ☐ Q2 repaired (≥2/3 V hot, ≥2/3 NT flat) · ☐ Still failing — see diagnosis table
