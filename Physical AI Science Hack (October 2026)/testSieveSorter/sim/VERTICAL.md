# Vertical and angled strokes on the demo tray

Physics session, 2026-10-25. Task: `docs/sessions/demo-rig.md` parts A and B. Raw runs are in `sim\out\sweeps\vertical*\` (gitignored); each folder has `report.html` and `summary.csv`.

> **The demo rig is a stack of trays** (5 mm over 2 mm over a catch pan; 06:20 correction in `demo-rig.md`). Its results are in [Result: the stacked rig](#result-the-stacked-rig-inserts5mm2mm). The single-tray results right below cover the top level only.

## What changed

- **`angle_deg` on the stroke** (`sorter.py`, function `stroke_axis`). 0 means along the design's flow axis, which is the old behaviour. 90 means straight up. Anything in between is an angled throw, as in lab vibratory sieve shakers. It works anywhere a stroke dict goes:
  - CLI: `--stroke sine:amp_mm=1.24,freq_hz=20,angle_deg=90`
  - Python, sweeps and the optimizer: `{"profile": "sine", "amp_mm": 1.24, "freq_hz": 20, "angle_deg": 45}`
  - `stroke["axis"]` (a 3-vector) still works from Python. Giving both is an error.

  The tray-frame gravity is `-a(t)*axis - g*z`, which is exact for any translation of the tray. So a vertical stroke only needs the axis; nothing else changed.
- **The demo tray is `inserts:5mm`**: one holder box with the 5 mm printed square-hole insert (`cad/sieve_insert.py`), on a catch pan. Zones are `on_5mm` (pasta should stay here) and `catch` (rice should end here). It already built; nothing was added.
- **`sweep.py vertical`**: the comparison below. `--mix` overrides the demo mix; `--quick` runs 2 seeds of 2 s.
- **Only the tray, the grains and the stroke are modelled.** The DeWalt tool isn't: no geometry, motor or hand dynamics. It's just what moves the tray.

## Assumptions (not measurements)

| | Value | Why |
|---|---|---|
| Profile | sine, 20 Hz | A smooth throw, like a vibratory sieve shaker (those run at about 50 Hz, 1–3 mm). The tool's real motion at the tray is unknown, and Forum's clip shows the tool idle. |
| Peak acceleration | 2 g and 4 g | Above 1 g a vertical stroke throws the grains off the screen. 2–4 g is the usual sieve-shaker range. |
| Amplitude | 1.24 mm (2 g), 2.48 mm (4 g) | `amp = peak * g / (2 pi f)^2` |
| Equal peak acceleration across directions | yes | Within a block, every direction gets the same sine, so any difference comes from the direction. |
| Demo mix | pasta (ditalini) 15 + rice 40 | Forum's photos. The heavy load (pasta 30 + rice 150) is the heap seen in IMG_1315. |
| Dark grains | not modelled | Colour doesn't matter to the sim. If they're wild rice (long and thin, about 1.5–2 mm thick), they pass a 5 mm hole like rice. |
| Grain sizes | `grains.py` typical values | rice 6.5 x 2.0 x 1.7 mm; ditalini 6.5 mm across x 6.0 mm long. Not yet caliper-measured. |
| Contact | dt 0.25 ms, timeconst 0.5 ms; friction 0.3 / 0.4 / 0.5 | Production settings. There's no `calibration.json` yet, so the three friction sets are the defaults. |
| Run | 1 s settle, then 10 s shake, 6 seeds per friction set | 108 runs |

## Result: demo tray, demo mix (pasta 15 + rice 40)

Every one of the 108 runs ends with **pasta 1.00 and rice 1.00 recovery**, with no jams, no losses, no contamination and no unstable resets. The 5 mm holes leave a lot of room either way: rice is about 2 mm across, and ditalini are at least 6 mm, which is over 1 mm too big for the hole at any tilt. So direction can only show up in speed and contact overlap.

t50 and t90 are seconds from the start of the shake until 50% / 90% of the rice is in the catch. Values are means over 18 runs (6 seeds x 3 friction sets). "Overlap" is the largest particle-into-tray overlap per run, as a mean.

| Peak accel. | Direction | t50 rice | t90 rice (sd) | t90 at friction 0.3 / 0.4 / 0.5 | Overlap, tray | Overlap, particle-particle |
|---|---|---|---|---|---|---|
| 2 g | 0° along the flow axis | 0.03 s | **0.21 s** (0.02) | 0.22 / 0.20 / 0.20 | 0.14 mm | 0.05 mm |
| 2 g | 45° throw | 0.03 s | 0.28 s (0.06) | 0.28 / 0.28 / 0.27 | 0.14 mm | 0.13 mm |
| 2 g | 90° straight up | 0.09 s | 0.62 s (0.12) | 0.60 / 0.58 / 0.67 | 0.17 mm | 0.13 mm |
| 4 g | 0° along the flow axis | 0.04 s | **0.33 s** (0.08) | 0.35 / 0.32 / 0.33 | 0.14 mm | 0.10 mm |
| 4 g | 45° throw | 0.06 s | 0.93 s (0.43) | 0.78 / 0.90 / 1.10 | 0.22 mm | 0.22 mm |
| 4 g | 90° straight up | 0.07 s | 0.71 s (0.26) | 0.65 / 0.62 / 0.85 | 0.24 mm | 0.19 mm |

What this says:
1. **On the demo tray, the shake direction doesn't change the outcome.** Every direction sorts perfectly within about 1 s. Most rice falls through during the 1 s settle, before the shake starts, which is why t50 is near 0. The demo insert is very forgiving for pasta vs rice.
2. **Along the flow axis is fastest at clearing the last rice:** 2–3x quicker t90 than vertical at the same peak acceleration, and the least sensitive to friction. Sliding sweeps stray rice grains over holes. A vertical throw lifts them and drops them back about where they were.
3. **More acceleration doesn't help here:** at 4 g the 45° and 90° strokes get slower and more spread (t90 sd 0.26–0.43 s), because grains spend longer in the air.
4. **Vertical strokes press harder into the tray:** the overlap is 0.22–0.24 mm at 4 g, against 0.14 mm for horizontal. That's harmless on the 5 mm demo insert. For tight gates, see Stability below.
5. **Answer for the demo:** up-and-down shaking (as in the video) works for pasta vs rice on the 5 mm insert. It's just slower to clear the last grains than shaking along the tray. If the demo shows the motion from the video, the sim agrees it will sort.

## Result: heavy load (pasta 30 + rice 150)

The heap from Forum's IMG_1315: 180 particles, 1 s settle + 5 s shake, 4 seeds x 3 friction sets = 12 runs per row, 72 runs in all. There were 0 resets and 0 errors.

| Peak accel. | Direction | Recovery rice / pasta | t90 rice (sd) | t90 at friction 0.3 / 0.4 / 0.5 | Rice left on the screen (contamination of `on_5mm`) | Stuck in holes (`between`, per run) | Overlap tray / particle-particle |
|---|---|---|---|---|---|---|---|
| 2 g | 0° | 1.00 / 1.00 | **0.23 s** (0.05) | 0.23 / 0.25 / 0.23 | 0.00 | 0.00 | 0.18 / 0.13 mm |
| 2 g | 45° | 0.99 / 1.00 | 0.35 s (0.10) | 0.30 / 0.33 / 0.42 | 0.04 | 0.00 | 0.17 / 0.14 mm |
| 2 g | 90° | 1.00 / 1.00 | 0.59 s (0.07) | 0.60 / 0.57 / 0.60 | 0.00 | 0.00 | 0.18 / 0.17 mm |
| 4 g | 0° | 1.00 / 1.00 | **0.40 s** (0.04) | 0.38 / 0.42 / 0.40 | 0.00 | 0.00 | 0.18 / 0.13 mm |
| 4 g | 45° | 0.99 / 1.00 | 1.06 s (0.40) | 0.93 / 0.85 / 1.40 | 0.03 | 0.00 | 0.21 / 0.24 mm |
| 4 g | 90° | 1.00 / 1.00 | 0.83 s (0.13) | 0.78 / 0.75 / 0.97 | 0.01 | 0.08 | 0.25 / 0.26 mm |

Four times the load gives the same ranking, with the first imperfections:
- **Along the flow axis** stays perfect and fastest, and is barely slowed by the bigger heap (t90 0.23 s against 0.21 s).
- **The 45° throw leaves about 1% of the rice on the screen** with the pasta after 5 s. A likely cause, not checked frame by frame, is that grains thrown forward and up keep landing back in the pasta layer. It's also the most friction-sensitive stroke (t90 0.85–1.40 s at 4 g).
- **Straight up at 4 g** occasionally wedges a rice grain in a hole (0.08 per run) and has the highest overlap.

So the answer holds: **direction doesn't decide whether the demo sorts, but along the tray is the best stroke for it.** Up-and-down shaking works, at 2–3x the time to clear the last rice. A 45° throw is the worst choice for this insert.

## Result: the stacked rig (`inserts:5mm,2mm`)

The rig the team built is separate trays stacked one above the other: the 5 mm printed insert over the 2 mm one over the catch pan, with the whole stack shaken. Each class should end on its own level: pasta on 5 mm, rice on 2 mm, quinoa in the catch.

**Setup:**
- The same strokes as above: 20 Hz sine at 2 g and 4 g, at 0°, 45° and 90°.
- Mix: pasta 15 + rice 40 + quinoa 40.
- Each run is a 1 s settle, then 10 s of shaking. 6 seeds x 3 friction sets = 18 runs per row.
- Contacts: dt 0.125 ms / tc 0.25 ms (the 2 mm level is near-size, see below). All 108 runs were repeated at production contacts (0.25 / 0.5 ms).
- 216 runs in all, 0 resets, 0 errors.

**What the sizes allow.** At the nominal 2 mm hole, `designs_holder.py`'s size rule lets 37 of 40 rice grains through end-first, the same as quinoa: their 2.0 x 1.7 mm cross-section fits the square corner to corner. So the 2 mm tray holds rice only while the grains lie flat, and whether they stay flat depends on the shaking.

| Peak accel. | Direction | Pasta on 5 mm | Rice on 2 mm, after 1 / 2 / 5 / 10 s | Quinoa in the catch | Quinoa t90 | Stuck between trays, per run | Net moves back up, per run | Rice on 2 mm at 10 s, production contacts |
|---|---|---|---|---|---|---|---|---|
| 2 g | 0°, along the tray | 1.00 | 0.87 / 0.87 / 0.86 / **0.86** | 1.00 | 1.0 s | 0.00 | 0.7 | 0.85 |
| 2 g | 45° | 1.00 | 0.80 / 0.66 / 0.45 / **0.24** | 1.00 | 1.2 s | 0.00 | 3.7 | 0.28 |
| 2 g | 90°, straight up | 1.00 | 0.74 / 0.63 / 0.33 / **0.16** | 0.99 | 2.4 s | 0.06 | 5.1 | 0.12 |
| 4 g | 0° | 1.00 | 0.92 / 0.92 / 0.92 / **0.90** | 0.96 | 4.6 s | 0.00 | 2.7 | 0.92 |
| 4 g | 45° | 1.00 | 0.82 / 0.86 / 0.87 / **0.84** | 0.93 | 5.8 s (15 of 18 runs) | 0.06 | 3.4 | 0.84 |
| 4 g | 90° | 1.00 | 0.83 / 0.88 / 0.86 / **0.79** | 0.98 | 3.3 s | 0.00 | 4.2 | 0.76 |

Fractions are means over 18 runs. Quinoa t90 is the median time from the start of the shake until 90% of the quinoa is in the catch. "Net moves back up" counts drops in each class's total depth (level index x grains) between the 10 Hz zone counts, summed over the run; it's a lower bound on grains going back up a level.

What this says:
1. **Pasta always ends on the 5 mm tray**, in every run.
2. **On the 2 mm tray the direction decides the outcome**, unlike on the single tray.
   - Along the tray, rice stays: 86% at 2 g and 90% at 4 g, flat from 1 s on.
   - At 2 g, a 45° throw or a straight-up stroke stands rice on end. It keeps leaking through, down to 16% after 10 s straight up, and still falling.
3. **At 4 g the throws keep most of the rice** (79–84%), the opposite of what 2 g suggests. This wasn't checked frame by frame. A likely cause: at 4 g the grains spend most of each cycle in the air and land flat, while at 2 g they stay on the screen, where a grain on end finds a hole. Check it on the bench before relying on it.
4. **Quinoa clears into the catch in 1–2.4 s at 2 g.** At 4 g it's slower (3–6 s), and 2–7% stays on the 2 mm tray with the rice.
5. **Bouncing back up and jams are rare:**
   - At most about 5 net moves back up per run, out of 95 grains.
   - At most 0.06 grains per run stuck between the trays (0.11 at production contacts).
6. **The contacts don't decide it.** Production contacts give the same counts per level, within 1–2 grains (last column), with a maximum tray overlap of 0.35 mm against 0.18 mm.

**As printed.** The optimizer assumes printed holes come out 0.15 mm under nominal. At 1.85 mm, the size rule blocks about half the rice even end-first (18 of 40 fit). The check: `inserts:h4p85b1p35,h1p85b1p15` (built with `optimize.py`'s `inserts_inject`), 2 g, stiff contacts, 18 runs per direction, 0 failures.

| Direction | Pasta on 5 mm | Rice on 2 mm at 10 s | Quinoa in the catch |
|---|---|---|---|
| 0°, along the tray | 1.00 | **0.94** | 0.99 |
| 45° | 1.00 | 0.75 | 0.97 |
| 90°, straight up | 1.00 | 0.64 | 0.96 |

The printed hole size moves the numbers a lot but not the order: along the tray is still best. The hole gauge (`cad/hole_gauge.py`) settles which case the rig is in.

**For the demo:**
- Shaking the stack up and down, as in the video, does these at 2 g:
  - Puts the pasta on the top tray at once.
  - Gets the quinoa into the catch within about 2 s.
  - Keeps feeding rice through the 2 mm tray after that.
- To keep the rice on its tray, do one of these:
  - stop after 1–2 s;
  - shake harder (4 g keeps about 80%);
  - shake along the tray (86–94% stays).
- This is the uncalibrated sim. The grain sizes aren't caliper-measured, and the tool's motion (a 20 Hz sine) is assumed.

## Stability under vertical impacts

Probe: `instab.py`. The run stops at the first MuJoCo state reset, and the per-run maximum overlap is recorded. **0 resets in 840 runs**:
- 384 runs with the old horizontal stroke across 4 designs x 3 mixes x 4 solver settings. These used the first version of the probe, which watched only the QACC warning; the other 456 runs catch any reset.
- 360 runs with vertical 2/4/8 g, a 45° 4 g throw and the horizontal baseline, on `inserts:5mm`, `inserts:mesh5,mesh2` and `pool:w5p0,t1p4` (the 1.4 mm tunnel, 0.3 mm quinoa clearance), with the demo and insect mixes;
- 96 runs of vertical strokes with stiffer contacts.

Vertical strokes don't go unstable, but they push contacts deeper. Median per-run maximum overlap with the tray (8 runs per cell, demo and insect mixes):

| Stroke | dt 0.5 ms, tc 2 ms (old default) | dt 0.25 ms, tc 0.5 ms (production) | dt 0.125 ms, tc 0.5 ms | dt 0.125 ms, tc 0.25 ms | dt 0.0625 ms, tc 0.125 ms |
|---|---|---|---|---|---|
| horizontal firmware, 50 mm/s | 0.47 | 0.10 | 0.10 | | |
| vertical 2 g | 0.44–0.75 | 0.15–0.19 | 0.12–0.15 | 0.08 | 0.04–0.05 |
| vertical 4 g | 0.89–0.96 | 0.22–0.27 (p90 up to 0.74) | 0.19 | 0.12–0.13 | 0.06–0.08 |
| vertical 8 g | 1.55 | 0.47 | 0.42 | | |

- **The contact time constant controls the overlap, not dt.** Halving dt at the same tc barely helps. tc has to stay at least 2 dt, so stiffer contacts cost a smaller dt.
- **Cost:** each halving of dt costs about 2.3–2.7x wall time (run alone: 8.4 s to 22.6 s per 3 s demo run at 4 g).
- **Recommendation (first version; superseded by the Contact rule below):**
  - The demo tray (`inserts:5mm`, at least 1 mm of slack) and mesh or rice-scale gates are fine at production settings (dt 0.25 ms, tc 0.5 ms).
  - Tight gates, where the clearance is about 0.3 mm or less (the 1.4 mm tunnel for quinoa), need **dt 0.125 ms, tc 0.25 ms** for vertical strokes up to 4 g. That brings the median overlap to about 0.12 mm, at about 2.5x the runtime.
  - Never use the old default (0.5 ms / 2 ms) with vertical strokes: about 1 mm of overlap would let grains squeeze through gates they can't pass.
  - 8 g is too violent for tight gates at any setting tried.
- **Unstable runs are no longer silent:** each MuJoCo reset is listed in `results["unstable_resets"]`, `sorter.py` prints `UNSTABLE`, and the sweep log tags the run (see `PERF.md`).

## Contact rule (`contact_rule.py`)

The table above measured the overlap tray-wide (any tray geom) and only every 10th step, on two designs. Neither is what decides whether a grain gets through an opening it shouldn't pass. So I measured it again, on the surfaces that bound an opening, and turned the result into a helper that picks the contacts for a run.

**Measurement** (`instab.py`, which now records the worst overlap per tray role after the settle, read every step):
- Designs and their opening surfaces:
  - `inserts:5mm`: the screen.
  - `pool:w5p0,t1p4`: the gates, and the floor under them. Its 1.4 mm tunnel leaves quinoa 0.3 mm, and a grain sunk into the floor clears a lower ceiling.
  - `plinko` (the repo's rods): the rods.
- Mixes: `grains76` (the optimizer's demo mix) and `insects70`, 3 seeds each, 2 s of shaking after a 1 s settle.
- Strokes: the firmware stroke (10 mm at 50 mm/s) at 0, 45 and 90°, and 20 Hz sines at 2 g (90°), 4 g (45°, 90°) and 8 g (90°).
- Settings: (dt, tc) = (0.25, 0.5), (0.125, 0.25) and (0.0625, 0.125) ms.
- **378 runs, 0 resets, 0 errors.**

**Worst design's median overlap on the opening surfaces, mm** (the worst design in brackets; this is `MEASURED` in `contact_rule.py`):

| Stroke | dt 0.25 / tc 0.5 ms (production) | 0.125 / 0.25 ms | 0.0625 / 0.125 ms |
|---|---|---|---|
| firmware, along the tray (1.03 g, 50 mm/s) | 0.092 (plinko) | 0.047 (plinko) | 0.023 (plinko) |
| firmware, 45° | 0.093 (plinko) | 0.048 (plinko) | 0.021 (plinko) |
| firmware, straight up | 0.023 (plinko) | 0.020 (plinko) | 0.005 (plinko) |
| sine 2 g, straight up | 0.236 (insert) | 0.129 (pool) | 0.080 (pool) |
| sine 4 g, 45° | 0.390 (pool) | 0.345 (pool) | 0.144 (pool) |
| sine 4 g, straight up | 0.521 (pool) | 0.244 (pool) | 0.194 (pool) |
| sine 8 g, straight up | 0.661 (pool) | 0.612 (pool) | 0.242 (pool) |
| Wall time | 1x | 1.9x | 3.8x |

What this shows:
1. **Grains dropping onto plinko rods press hardest under the firmware stroke:** 0.092 mm at production, against 0.04–0.05 mm on the insert screen and the pool tunnel. That's more than half of a 0.14 mm clearance, which is what the optimizer's plinko leaders have at L2 (rice held by 1.55 mm rod gaps).
2. **The firmware stroke never throws the grains, so pointing it up presses *less*** (0.023 mm): its reversals peak at 1.03 g, and it's the sideways knocks at each reversal that press. Peak acceleration alone doesn't predict the overlap. A sine that throws the grains (2 g and up, vertical) presses hardest, through the landings.
3. **Reading every 10th step misses part of each impact.** On identical runs (MuJoCo is deterministic here: all 133 tray-wide maxima matched exactly), the gate overlap read every step is 1.2–1.5x the every-10th-step reading in the median, and 2.6–3.4x at p90. `sorter.py`'s `max_penetration_mm` and `optimize.py`'s gate overlap both read every 10th step, so their flags read low.
4. **Tray-wide overlap is mostly surfaces that don't gate anything.** On `inserts:5mm` under the firmware stroke, the catch pan takes 0.18 mm (rice landing after it drops through), against 0.04 mm on the screen.
5. The pool's gates and floor show a fixed 0.116 mm maximum at every setting. That's a grain wedged from the start, not contact softness, so it doesn't move the medians.
6. **Revised recommendation for vertical strokes.** At 0.3 mm clearance, a 2 g vertical sine still needs dt 0.125 / tc 0.25 ms (0.129 mm). A 4 g vertical sine isn't trustworthy at any setting tried (0.19 mm at the stiffest). The first version above said 0.125 / 0.25 ms was enough up to 4 g, but it measured tray-wide every 10th step, on fewer designs.

**The rule.** Take the cheapest setting whose expected overlap is at most 0.5 x the design's tightest clearance (the optimizer's `PEN_FLAG`).
- The expected overlap is looked up among measured strokes of the same profile, at the gentlest measured level whose peak acceleration *and* peak speed are both at least the stroke's, interpolated in angle. Peak speed matters because a lower frequency at the same acceleration moves faster and lands harder: a 2 g sine at 10 Hz looks up the 4 g level.
- A stroke between two measured levels gets the harder level's value.
- An unmeasured stroke gets the stiffest setting as a precaution. That covers horizontal sines, sawtooth and csv strokes for now.

```
python contact_rule.py --clearance 0.14 --stroke constant_speed:amp_mm=14,speed_mm_s=41,ramp_s=0.01
--dt 0.000125 --timeconst 0.00025    # clearance 0.14 mm: expected overlap 0.047 mm <= 0.070 mm (measured at 1.03 g, 50 mm/s, 0/45/90 deg), 1.9x production wall time
```

| Case | Pick |
|---|---|
| The optimizer's plinko leaders (clearance 0.14 mm, firmware stroke) | 0.125 / 0.25 ms. Production (0.092 mm expected) is over the 0.07 mm limit. |
| Firmware stroke on a 0.3 mm gate | production |
| Sine 2 g straight up on a 0.3 mm gate | 0.125 / 0.25 ms |
| Sine 4 g straight up on a 0.3 mm gate | none is enough; stiffest, flagged "untrustworthy" |
| Demo tray, any of these strokes (1.1 mm clearance) | production |

From Python: `dt, tc, why = contact_rule.pick(clearance_mm, stroke)`. The rule picks the setting; it doesn't replace checking each run's own overlap and `unstable_resets`. `verify.py` lists the rule's pick next to the contacts it measures on each design.

**Checked against those measurements** (each design probed on its own stroke, [opt/VERIFY.md](opt/VERIFY.md)):
- **The firmware plinkos:** the rule matches (0.125 / 0.25 ms).
- **The gated tower on a 37 Hz, 2.5 g sine at 45°:** the rule is safe but costly. It reads the 4 g level and picks the stiffest; production was enough.
- **The stacked rig `inserts:5mm,2mm` with the firmware stroke:** the rule picks **too soft** a setting.
  - The stack's 2 mm screen takes 0.179 / 0.076 / 0.045 mm at the three settings, about twice the single-tray designs in the table.
  - The rule's 0.125 / 0.25 ms gives 0.076 mm against a 0.065 mm limit (0.13 mm clearance).
  - Run the stack at 0.0625 / 0.125 ms until the grid is rerun with it.

## Reproduce (from `sim\` in the WSL venv; see `docs/sessions/README.md`)

```
python sweep.py vertical --dt 0.00025 --timeconst 0.0005
python sweep.py vertical --mix pasta=30,rice=150 --seeds 4 --duration 5 --dt 0.00025 --timeconst 0.0005 --name vertical_heavy
python sweep.py vertical --design inserts:5mm,2mm --mix pasta=15,rice=40,quinoa=40 --dt 0.000125 --timeconst 0.00025 --workers 8 --name vertical_stack
python sweep.py vertical --design inserts:5mm,2mm --mix pasta=15,rice=40,quinoa=40 --dt 0.00025 --timeconst 0.0005 --workers 8 --name vertical_stack_prod
    (as printed: the same 2 g strokes on inserts:h4p85b1p35,h1p85b1p15, which only builds with optimize.py's
     inserts_inject, so run it through optimize.run_job once design-opt is on main)
python instab.py --seeds 4 --duration 2 --designs "inserts:5mm;inserts:mesh5,mesh2;pool:w5p0,t1p4" --mixes demo,insects70 \
  --strokes "sine:amp_mm=1.242,freq_hz=20,angle_deg=90;sine:amp_mm=2.485,freq_hz=20,angle_deg=90;sine:amp_mm=4.970,freq_hz=20,angle_deg=90;sine:amp_mm=2.485,freq_hz=20,angle_deg=45;constant_speed:amp_mm=10,speed_mm_s=50,ramp_s=0.01" \
  --solver "0.0005,0.002;0.00025,0.0005;0.000125,0.0005" --out out/instab/vertical.jsonl
FW=constant_speed:amp_mm=10,speed_mm_s=50,ramp_s=0.01                                 (the contact rule's table)
python instab.py --seeds 3 --duration 2 --designs "inserts:5mm;pool:w5p0,t1p4" --mixes grains76,insects70 \
  --strokes "$FW;$FW,angle_deg=45;$FW,angle_deg=90;sine:amp_mm=1.242,freq_hz=20,angle_deg=90;sine:amp_mm=2.485,freq_hz=20,angle_deg=45;sine:amp_mm=2.485,freq_hz=20,angle_deg=90;sine:amp_mm=4.970,freq_hz=20,angle_deg=90" \
  --solver "0.00025,0.0005;0.000125,0.00025;0.0000625,0.000125" --out out/instab/rule2.jsonl
python instab.py ... --designs plinko --out out/instab/rule2_plinko.jsonl                (the same strokes and settings)
python contact_rule.py --rebuild out/instab/rule2.jsonl out/instab/rule2_plinko.jsonl
python sorter.py --design inserts:5mm --mix pasta=15,rice=40 --stroke sine:amp_mm=1.24,freq_hz=20,angle_deg=90 \
  --duration 10 --dt 0.00025 --timeconst 0.0005 --out out/runs/demo_vertical     (a run for the viewer)
python sorter.py --design inserts:5mm,2mm --mix pasta=15,rice=40,quinoa=40 --stroke sine:amp_mm=1.242,freq_hz=20,angle_deg=90 \
  --duration 10 --dt 0.000125 --timeconst 0.00025 --out out/runs/stack_vertical  (the stacked rig for the viewer; the
                                                    rice is mostly through the 2 mm tray by 5 s, so a short clip
                                                    shows the best sort)
```

## For the optimizer

- `angle_deg` from 0 to 90 is a plain stroke key, so it can go into the search space next to `amp_mm` and `freq_hz`.
- Compare at equal peak acceleration (`amp * (2 pi f)^2`), or the angle gets confounded with how hard the tray is shaken.
- Pick each candidate's contacts with `contact_rule.pick(clearance, stroke)` (see Contact rule). For the current plinko leaders that's dt 0.125 ms / tc 0.25 ms, even with the firmware stroke along the tray. Check `results["unstable_resets"]` and drop or flag any run that has resets.
- The gate-overlap flag reads every 10th step, which misses part of each impact (1.2–1.5x low in the median). Reading every step costs little; `verify.py`'s `run_job` shows how without editing `optimize.py`.
- That reading passed the firmware plinko P-ba5dd6b3 at production contacts. Read every step, it sits over the flag line (0.093 against 0.080 mm), and at stiffer contacts it holds more quinoa on layer 2 (mean 0.960 → 0.888 → 0.857; [opt/VERIFY.md](opt/VERIFY.md)).
- The demo baseline is the stacked rig, `inserts:5mm,2mm`, with all three classes. The single tray (`inserts:5mm`, pasta + rice) is saturated at recovery 1.00.
- For the rice / quinoa split on a 2 mm square-hole tray, the stroke direction matters: rice stays when the shake runs along the tray and leaks through end-first under a 2 g throw (Result: the stacked rig).
