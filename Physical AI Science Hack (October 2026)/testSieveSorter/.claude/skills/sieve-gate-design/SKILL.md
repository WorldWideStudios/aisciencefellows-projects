---
name: sieve-gate-design
description: Size-sort a sample with 3D-printed sieve gates for BioKEA's BugSorter tower (testSieveSorter repo). Use it to go from sample information (item sizes, counts, target plate, desired classes) to gate sizes per tower level, printable gate strips from the CadQuery scripts, a MuJoCo sim check, a bench test, and a logged iteration. Use it whenever someone asks to pick gate, gap, tunnel or hole sizes for a sample; to design filters or sieve layers for insects, grains or any mix; to decide what fits a 96-well plate well; to test a new sieve or gate size in the sim; to print or bench-test gate strips; or to continue a gate_runs log. That includes casual asks like "what gap should I print for these bugs", "will rice and quinoa separate", or "try a 2.4 mm gate".
---

# Sieve gate design loop

**The design.** BugSorter is a tower of holder boxes, shaken along the box's long axis, with spray from above.
- Each level holds a **gated container** (`cad/gated_container.py`): a solid floor slopes 2° to a swappable gate strip, with a one-way drop slot just past it.
- What passes the strip drops to the level below. What can't pass stays and is lifted out.
- Width strips (`w`) cut by the width of a flat-lying item; tunnel strips (`t`) cut by its thickness.

**This skill turns sample information into one gate per level.** It uses a fast geometric calculator first, then checks transport and jams in the sim, then prints, bench-tests and logs, so the next agent can continue.

**Ground rules**
- Work from the repo root `C:\Users\ajfil\Documents\Github\testSieveSorter`. `<py>` = `C:\Users\ajfil\Documents\Github\testSieveSorter\.venv\Scripts\python.exe` (the repo venv). Run each script from its own folder and show `pwd`.
- **`sim\` belongs to the sim session.** Read it, run it, never edit it. Gate sizes reach the sim through `cad\sieve_system.py` STRIPS. Read `sim\README.md` and `sorter.py --help` before running: flags change.
- **Tag every number in the log** as measured, executed, cited or assumed. Most item sizes and the print undersize are assumptions until the bench measures them.
- No test suites. Sim batches over about 15 min of wall time need the user's OK.
- No emoji anywhere.

## Step 0: Open or continue a run folder

- Use `gate_runs\<sample>\` for each sample.
- **If `LOG.md` exists**, read its Status block and last "Decision and next" first, and continue from there.
- **Otherwise:**
  - copy `templates\sample-spec.toml` to `spec.toml` (pantry grains);
  - or copy `templates\malaise-spec.toml` (insects, well-fit first cut);
  - copy `templates\LOG-template.md` to `LOG.md`.

## Step 1: Write the sample spec

Fill `spec.toml` (TOML; the template explains every field) from what the user gave:
- **items**: L >= W >= T ranges, `{mean, sd}`, or caliper CSV rows; counts; `fragile`; `span` for legs; `sim_kind`;
- **condition**: dry, wet or ethanol;
- **target plate**;
- **classes, top level first.** Classes filter by item names, `well = "fits"/"too_big"`, and min/max of length, width or thickness.

Ask at most three questions, and only for what changes the answer:
1. Which plate and fit rule? Below the rim or submerged; is leaning OK?
2. Which classes, in which order?
3. Are there measured sizes?

Otherwise use the template defaults and mark them assumed. **Measure in the sorting condition**: wet grains swell and preserved specimens stiffen.

## Step 2: Plan the gates (seconds; no sim yet)

```
<py> .claude\skills\sieve-gate-design\scripts\gatecalc.py plan gate_runs\<sample>\spec.toml --log gate_runs\<sample>\LOG.md
```

**How to read the output:**
- **Gate sequence**: each level's gate at its printed (effective) size and at its CAD (nominal) size.
  - "Same-score window" is the robust range; a wide window is good.
  - "Worst-case misroutes" is the score at ± print tolerance, with the margins and p_roll applied.
- **Predicted routing**: the percentage of each item at each level, with flat-only vs any-roll bounds.
- **Classes**: recovery and purity per level.
- **Warnings**, which are the point of the exercise:
  - on-edge roll leaks, and whether a window gate would fix them;
  - near-size wedging;
  - snagging appendages;
  - fragile items in a tunnel;
  - items that reach a "fits" level but are too long or deep for the well (gates can't cut length);
  - sim kinds whose sizes differ from the spec.

**Compare alternatives with `check`**:
```
<py> .claude\skills\sieve-gate-design\scripts\gatecalc.py check gate_runs\<sample>\spec.toml --gates w5.0,t1.4 --log gate_runs\<sample>\LOG.md
```
- Start with the strips that already exist: `w5.0 w3.0 w2.0 t1.2 t1.4 t1.6`. They need no printing.
- For a quick single-item answer: `gatecalc.py item 6.5x2.0x1.7 --gates w2.0,t1.4 --plate std96_flat`.

**Iterate on the spec**, not on intuition: classes, `gate_menu`, margins.
- Add `"o"` or `"sq"` to `gate_menu` to see whether a round hole or square window would do better. Those need CAD that the gated container doesn't have yet.
- The rules and their derivation are in `references/passability.md`; the 96-well rules and sources in `references/well-fit.md`.

## Step 3: Generate the printable parts

Add the STRIPS lines that `plan` prints to `cad\gated_container.py` (one line per new size). Then:
```
cd cad
<py> gated_container.py gate_t1p55 gate_w4p5
<py> slice.py gate_t1p55 --printer P1S
```

- **Accept a part only if** `out\<name>_checks.json` has valid_solid, single_solid, watertight_mesh and fits_bed all true, and `opening_mm` is what you intended. Look at the PNG.
- **Kinds that aren't built yet** (window, pillar comb, round hole) are proposals: `references/sim-and-cad.md` section 6. Propose them to the user and log them; don't improvise geometry in shared CAD files.
- **Log** each part's STRIPS line, checks and print estimate.

## Step 4: Check the sequence in the sim

The sim has no gated-container design yet. Use the **pool** proxy (`pool:<g1>,<g2>`): the same strip openings, two gates, terraced floor.

1. Add the pool strips that `plan` prints to `cad\sieve_system.py` STRIPS, at the **effective** (as-printed) size. Log the mapping.
2. Run 3 seeds x 30 s on the firmware cap stroke, in parallel, from `sim\`:
   ```
   <py> sorter.py --design pool:<g1>,<g2> --mix <from plan> --stroke constant_speed:amp_mm=10,speed_mm_s=50,ramp_s=0.01 --duration 30 --seed 0 --fps 0 --out out\runs\<sample>\itNN_s0
   ```
   - Run the same with the current strips as the **baseline**.
   - Add the 5 mm/s stroke with `--spray default` and the sine stroke only when transport is the question. Spray is about 50x slower.
   - With 3 or more gates, run consecutive pairs.
3. Summarise and log:
   ```
   <py> .claude\skills\sieve-gate-design\scripts\gatecalc.py sim sim\out\runs\<sample>\itNN_s0 ... --log gate_runs\<sample>\LOG.md
   ```
4. **Read it with the table in `references/sim-and-cad.md` section 2:**
   - "upstream (transport)" means change the stroke, spray or duration, not the gate size;
   - "rolled through" gives a p_roll estimate to put back into the spec;
   - "beyond geometry" must be 0.

The sim ranks designs; it does not predict real percentages. It is uncalibrated, has no liquid, uses rigid insects, and caps at about 80 particles. The full list is in `references/sim-and-cad.md` section 5. Say so whenever you report sim numbers.

## Step 5: Refine, print, bench-test, feed back

1. **Refine.** Update the spec (p_roll from the sim; margins if near-size items jammed), re-plan or re-check, and re-simulate only the levels that changed. **Stop refining in the sim** when two candidates differ by less than the seed sd; the bench decides from there.
2. **Print.**
   - Print `cad\hole_gauge.py` first; put its measured sizes in `[print] gauge`.
   - Print strips flat, as exported, and the container right side up.
   - In Bambu Studio, open one file per window, or import as separate objects and press A (Arrange). **Never load several STLs as a single object**: it stacks them.
3. **Measure** 10 openings per strip, bed side included, into `sim\bench\openings.csv`. Re-run `check --effective` with the measured sizes.
4. **Bench-test** with `sim\BENCH.md`: a counted mix, fixed time, 3 repeats, every item counted including jammed and lost, and one holdout configuration.
   - Gated-tower rows go to `gate_runs\<sample>\bench_counts.csv`.
   - Pool or insert rows go to `sim\bench\bench_counts.csv` so the sim session's `calibrate.py` can fit them.
5. **Feed back** into the spec: the gauge table, measured item dims (`measured = ...`), the observed p_roll and the clearance. Then loop to step 2.

## Step 6: Record

- Every iteration gets one section in `gate_runs\<sample>\LOG.md`, following `templates/LOG-template.md`: spec changes, plan, CAD, sim, print, bench, decision and next. `--log` appends the calculator's sections; write the rest.
- **Update the Status block at the top** before you stop, so the next agent can continue without asking.
- Commit only `gate_runs\<sample>\` (spec, LOG, bench CSVs) and any CAD STRIPS lines you added. Sim output stays in the gitignored `sim\out\`. Follow the repo's commit rules.

## Reference files

| File | Read when |
|---|---|
| `references/passability.md` | choosing a gate kind, explaining a leak or a jam, changing margins |
| `references/well-fit.md` | the target is a 96-well plate, or length or depth matters |
| `references/sim-and-cad.md` | building parts, running or reading the sim, printing, bench, calibration, proposals |
| `templates/sample-spec.toml`, `templates/malaise-spec.toml` | starting a spec (field reference inside) |
| `templates/LOG-template.md` | starting a log |
| `scripts/gatecalc.py` | `--help`; module docstring has the rule summary |
