# CAD, sim, print and bench: exact commands

Paths are from the repo root `C:\Users\ajfil\Documents\Github\testSieveSorter`. `<py>` is `C:\Users\ajfil\Documents\Github\testSieveSorter\.venv\Scripts\python.exe` (the repo venv) (Python 3.12 with cadquery, trimesh, vtk, mujoco, numpy). Run each script from its own folder, as the repo's docstrings assume, and show `pwd`.

The sim is built and edited by another session; its flags and defaults change. Before running it, read `sim\README.md` and `<py> sorter.py --help`, and adjust the commands below if they differ. Treat `sim\` as read-only unless the user says otherwise.

## Contents
1. CAD: gate strips for the gated container
2. Sim: checking a gate sequence
3. Print
4. Bench test and calibration
5. What the sim can and cannot tell you
6. Proposals: CAD and sim additions not built yet

## 1. CAD: gate strips for the gated container

`cad\gated_container.py` is the target design. It is a drop-in box for the holder tower: a solid floor sloping 2° to a swappable strip at +X, and a 7 x 80 mm drop slot past it.
- **Strips exist today** for `gate_w5p0`, `gate_w3p0`, `gate_w2p0` (gaps, 8 tall) and `gate_t1p2`, `gate_t1p4`, `gate_t1p6` (tunnels, 8 wide). Check those with `gatecalc check` first; they need no new CAD.
- **New size:** add one line per strip to `STRIPS` in `cad\gated_container.py`, e.g. `"gate_t1p55": ("t", 1.55),`. This is the documented way to change sizes in every CAD script in this repo. `gatecalc plan` prints the lines.
- **Build only the new parts:**
  ```
  cd cad
  <py> gated_container.py gate_t1p55 gate_w2p45
  ```
  Each part writes `cad\out\<name>.step/.stl/.png/_checks.json` via `cadkit.export_all`. STL and STEP are gitignored; the PNG and checks are committed.
- **Accept a part only if** `_checks.json` has `valid_solid`, `single_solid`, `watertight_mesh` and `fits_bed` all true. Also check that `opening_mm` and `openings` are what you meant. A strip is 91.0 x 18 x 2 mm; the number of openings follows from the 80 mm drop-slot span. Look at the PNG.
- **Print time and filament** (headless Bambu Studio):
  ```
  <py> slice.py gate_t1p55 --printer P1S
  ```
  A strip takes about 7 minutes.
- **The container itself** only needs reprinting if its parameters change. One per tower level; flip it 180° on alternate levels.
- **Other filter types in the same holder tower:**
  - square-hole floors: `sieve_insert.py` INSERTS `(hole, bar, screen_t)`, token `sq`;
  - rod floors: `plinko_layers.py` LAYERS, token `slot`.
- Window, pillar-comb and round-hole gates are not built yet: see section 6. Don't invent their geometry silently; propose it to the user and log it.

## 2. Sim: checking a gate sequence

**Design to use.** The sim has no gated-container design yet (verified in `sim\designs.py` and `designs_holder.py`, 2026-10-24). The closest proxy is the **pool**: `pool:<gate1>,<gate2>`.
- What matches: it has the **same strip openings**. `cad\sieve_system.py` STRIPS kinds w/t, with `OPEN_H` = `TUNNEL_W` = 8 and `STRIP_T` = 2, are the same as `GATE_H` / `TUNNEL_W` / `STRIP_T` in `gated_container.py`. It also has the same longways stroke.
- What differs:
  - its floor is terraced (3 mm steps), not a 2° slope with a drop slot;
  - its footprint is a 24-well plate;
  - it takes exactly two gates.
- So it tests passage, jams and contamination at the gates, not the container's transport or the drop between levels.

**Gate sizes reach the sim through `cad\sieve_system.py` STRIPS**, which `sim\designs.py` reads. Add the pool strips `gatecalc` prints, e.g. `"pool_gate_t1p25": ("t", 1.25),`.
- Simulate the size the printer actually makes, i.e. the effective size, because the sim builds from CAD numbers.
- Record the mapping in the log, e.g. "sim t1p25 = printed t1.4 nominal".

**Pairs of gates.**
- 2 gates: one run with the full mix.
- 3 or more: run consecutive pairs (L1-L2, L2-L3, ...). Each pair gets the mix that reaches its first gate; `gatecalc` computes that mix.
- 1 gate: use `w5p0` as the second gate.

**Mix.** Only the sim's kinds exist: `rice`, `quinoa`, `chickpea`, `pasta`, `insect_compact`, `insect_elongate`, `insect_longleg`.
- Their sizes are the sim's own (`sim\grains.py` SIZES, `sim\insects.py` PLANS), not the spec's. `gatecalc plan` warns when they differ by more than 10%.
- Keep a run at 80 particles or fewer, or placement can fail ("no room to drop particle").

**Strokes** (from `sim\sweep.py` FIRMWARE and the `sorter.py` docstring):

| Name | `--stroke` | Use |
|---|---|---|
| firmware cap | `constant_speed:amp_mm=10,speed_mm_s=50,ramp_s=0.01` | Main check: BioKEA firmware, 2 cm stroke at its 50 mm/s cap |
| firmware default | `constant_speed:amp_mm=10,speed_mm_s=5,ramp_s=0.01` | Default speed. Dry grains probably don't move (reversal jolt about 0.1 g); add `--spray default` |
| vigorous | `sine:amp_mm=3,freq_hz=10` | About 1.2 g peak: an upper bound on agitation (README demo) |
| measured | `csv:csv=<abs path to t_s,x_mm csv>` | Once the stroke is filmed (BENCH.md step 1) |

`ramp_s` = 0.01 is a guess until the slow-motion video measures it.

**Seeds and duration.**
- **Screening:** 3 seeds x 30 s on the firmware cap stroke. In a 10 s run most grains never reach their zone: `pool_demo` left 50 of 76 particles upstream.
- **Decision:** 5 seeds x 30-60 s, run once with the candidate and once with the current strips as the baseline, on the same strokes and seeds.
- Add `--spray default` for at most one stroke. Spray is about 50x slower: a 3 s spray run took 167 s of wall time, against 48 s for a 10 s dry run (`sim\out\runs\*/results.json`).

**Commands.** Run from `sim\`. Use `--fps 0` for screening (counts only, smaller files) and `--fps 30` for one seed you want to watch.
```
cd sim
<py> sorter.py --design pool:w4p5,t1p25 --mix rice=30,quinoa=30,chickpea=8,pasta=8 --stroke constant_speed:amp_mm=10,speed_mm_s=50,ramp_s=0.01 --duration 30 --seed 0 --fps 0 --out out\runs\<sample>\it01_s0
```
- Repeat for seeds 1 and 2, as separate background processes in parallel (the machine has spare cores unless another sweep is running; check CPU first).
- Unloaded, 10 simulated seconds take about 48 s of wall time for 76 particles. Under load it is several times slower.
- Ask the user before any batch over about 15 minutes of wall time.

**Watch one run:** `<py> viewer.py out\runs\<sample>\it01_s0 --open`. This needs that run recorded at `--fps 30`.

**Summarise and log:**
```
cd <repo root>
<py> .claude\skills\sieve-gate-design\scripts\gatecalc.py sim sim\out\runs\<sample>\it01_s0 sim\out\runs\<sample>\it01_s1 sim\out\runs\<sample>\it01_s2 --log gate_runs\<sample>\LOG.md
```

**How to read it:**

| Output | Means | Do |
|---|---|---|
| count table, recovery | where each kind ended, mean ± sd over seeds; recovery uses the sim's ideal zone | compare candidate vs baseline; a difference smaller than the seed sd is noise |
| contamination per zone | share of a zone's contents that belongs elsewhere | the purity of each level |
| t90 | seconds until 90% of a kind is in its ideal zone | "not reached" means too short a run or too weak a stroke, not a wrong size |
| upstream (transport) | particles that geometry lets through but that hadn't got there | transport-limited: lengthen the run, change the stroke, add spray. **Don't shrink or enlarge gates for this.** |
| rolled through, p_roll estimate | items that only fit on edge, and how many made it | put it in the spec's `p_roll`, re-plan |
| beyond geometry | particles past an opening they can't fit | should be 0; otherwise soft contacts squeezed them through. Treat near-size results as unreliable |
| overlap vs tightest clearance | contact softness against the real clearance | over half the clearance: near-size results are suspect |
| between / lost | jams and escapes | jams at a gate point at wedging: consider pillars or more clearance |

**Decide:**
- Accept a sequence when:
  - each level's class recovery and contamination are at least as good as the baseline's, beyond the seed sd;
  - there are no jams;
  - "beyond geometry" is 0.
- If a level fails on geometry (leaks or blocks that the calculator also predicts), change the spec or the gate kind and re-plan.
- If it fails on transport, the gate size is not the problem.

## 3. Print

- **Print the hole gauge first** (`cad\hole_gauge.py`), and `pool_coupon` if you will bench the pool. Measure, then update the spec's `[print] gauge`.
- **Orientation:**
  - strips flat, as exported (they are modelled lying flat), so gap width and tunnel height are in XY;
  - the container right side up, no supports;
  - pillar combs (proposal) bar-down, pillars up, so the pillars come out round.
- **Bambu Studio:**
  - Open one STL per window, or import several as separate objects and press **A** (Arrange).
  - If it asks whether to load several files as a single object, click **No**. "Yes" stacks every part in one spot (README).
  - Use 0.2 mm layers and PLA at the default profile, unless the team's printer notes say otherwise. Send the real print from the app, on the bench printer.
- **After printing:** measure 10 openings per strip (pin gauges or drill shanks, bed side included) into `sim\bench\openings.csv`, and re-run `gatecalc check --effective` with the measured sizes.

## 4. Bench test and calibration

Follow `sim\BENCH.md`. The parts that matter here:

**Grains or specimens.**
- Measure 30 of each type into `sim\bench\grain_dims.csv` (length, width, thickness, mass).
- Point the spec's items at it with `measured = "..."`.

**Counted runs.**
- Use the same counted mix every time, a fixed 30-60 s, and 3 repeats.
- Count every item in every zone, including `between` (jammed) and `lost`.
- Run the **pool with the same strips you simulated** and write the rows to `sim\bench\bench_counts.csv` (design `pool:...`), so `calibrate.py` can fit them.
- Write runs of the **gated tower** to `gate_runs\<sample>\bench_counts.csv` with the same columns, design `gated:<nominal gates top first>`, and zones `L1`, `L2`, ..., `catch`, `between`, `lost`. They can't be calibrated until a `gated:` sim design exists (section 6).

**Hold one configuration out** (another strip size or speed), as BENCH.md step 5 says.

**Calibrate** (the sim session's tool): `<py> calibrate.py bench\bench_counts.csv --clear bench\clear_times.csv` from `sim\`. Then rerun your sim pairs with the fitted friction (`--friction <best>` from `sim\out\calibration\calibration.json`).

**Feed back into the spec:**
- `[print] gauge` and the measured strip openings;
- measured item dims;
- `p_roll`, from counting how many roll-only items passed;
- `pass_clearance_mm`, raised if near-size items wedged.

Log everything (SKILL.md step 6).

## 5. What the sim can and cannot tell you

**Can (relative ranking only, until calibrated and validated on a holdout):**
- whether items get to and through a gate under a given stroke, and how fast (t90, upstream);
- jams at the gate, and leaks by rolling (an estimate of p_roll);
- contamination and recovery between two strip choices under identical strokes and seeds;
- whether spray or stroke changes transport. The jets are placeholders until `bench\jets.csv` exists.

**Cannot, as of 2026-10-24:**
- **Absolute percentages.** The sim is uncalibrated (`sim\README.md`).
- **The gated container tower.** There is no design for it: the 2° slope, the drop slot, the flipped levels, landing on the next level, and long items bridging the 7 mm slot are all untested.
- **Liquid.**
  - There is no fluid solver: no buoyancy or settling, no water carried back through openings.
  - Spray is a force and wetting model (`sim\spray.py`).
  - EntoSieve's one-way water flow is exactly what is not modelled.
- **Printed sizes, automatically.** The sim uses CAD numbers. `openings.csv` and `grain_dims.csv` are not read by any sim code yet (verified by grep).
- **Real specimens.**
  - Insects are rigid bodies with no joints, so legs don't fold: snagging is over-predicted and damage is invisible.
  - Their sizes are textbook assumptions (`sim\insects.py`).
- **Load.** About 80 particles per run against thousands of specimens in a Malaise sample. Clogging and capacity are untested.
- **Contact softness.** Particles can overlap the tray by about 0.1-0.2 mm, so near-size passes inside that band are not trustworthy (check the overlap line).

## 6. Proposals: CAD and sim additions not built yet

These are proposals only. None of them is built, and none should be built without the owner of the file agreeing.

**CAD (`cad\gated_container.py` unless noted):**
1. **Window gates.** Accept a third STRIPS value for the gap height, e.g. `("w", 6.0, 5.0)`, and use it instead of `GATE_H`. It's a three-line change in `strip()`. It blocks rolled items only when s² + h² <= W² + T² of the kept items; `gatecalc` computes this.
2. **Pillar comb strip** (kind `p`).
   - A top bar, printed on the bed, carries a row of round or teardrop pillars (reuse `gate_coupon`'s `POST_R` and downstream `TAIL` from `sieve_system.py`). It is installed pillars-down in the existing rails.
   - The bar ends are 2 mm thick so they ride the 2.3 mm rail groove. The clear gap g is measured at the narrowest point, and the pillar length sets the opening height.
   - It gives a zero-length throat and two-point contact: less wedging, and gentler on specimens.
3. **Round-hole gate** (kind `o`). It is the exact filter for "fits a round well".
   - Either a strip with flat-bottomed arch openings (a round top, so flat-lying items can enter at floor level),
   - or a round-hole option in `sieve_insert.py` INSERTS for a perforated floor in the holder tower.
4. **Downstream relief on strip openings.** The strips are cut straight through today (verified in `strip()`). Chamfer the downstream face of each tooth, as the inserts' 8° relief does.

**Sim (`sim\`, the sim session's files):**
1. **A `gated:<g1>,<g2>,...` design** in `designs_holder.py`: a holder-box tower with one gated container per level (2° floor, strip at `GATE_X`, drop slot, ramp, alternate flip) and a catch pan. Zones `L1..Ln`, `catch`. This is the single most useful addition: it makes the target design simulable and calibratable.
2. **Numeric gate tokens** (`pool:w2.45,t1.25`) without STRIPS entries, and a switch to build openings from `bench\openings.csv` measurements.
3. **A generic particle kind** (e.g. `ellipsoid:6.5x2.0x1.7`, or kinds read from `bench\grain_dims.csv`), so a spec's measured items can be simulated at their real sizes.
4. **`--dampratio` on `sorter.py`.** `calibrate.py` fits it, but the CLI only takes `--friction` and `--timeconst`.
5. **A `sweep.py custom` preset**: any designs x strokes x seeds with the existing report. Today the presets are fixed (`dtcheck`, `compare`, `stroke`).
6. **Buoyancy and drag for a liquid bath.** Specimens are about 1.05 g/cm³, against water at 1.00 and ethanol at 0.79 (`sim\insects.py` RHO), so in the bath gravity barely acts on them.
