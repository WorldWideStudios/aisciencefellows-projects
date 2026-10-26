# More levels: one tray per size class

Multi-layer session, 2026-10-25, 14:00–14:30 PT. The user asked for "multiple layers not just three, for different sizes that could work". This note covers towers of 4 and 5 sieve trays (5 and 6 size classes with the catch pan) and gated towers of 3 and 4 levels, all on the seesaw (SYSTEM.md §3), with every one of the 10 grain kinds and the real Malaise insect mix.

**The sim ranks designs. It isn't calibrated, so it doesn't predict real percentages** (SYSTEM.md §5). Every run below is one seed (seed 1) with the default friction. Read the tables as "this tower puts this kind on this level", not as recovery rates to quote.

## The size classes

Each grain kind's smallest square hole was drawn for 800 grains per kind at the sim's spreads (`common.ellipse_fits`, cross-section only, the same rule as `ideal_zone`). Each cut sits in a gap between groups. All sizes are **as modelled**: the sim takes 0.15 mm off the printed size, so a hole printed at 2.4 mm is 2.25 in the sim. Printed sizes stay on 0.1 mm steps.

| Tray | Hole, as modelled (print) | Holds | Passes in principle |
|---|---|---|---|
| 1 | 4.85 (5.0) | pasta, chickpea | everything else |
| 2 | 2.25 (2.4) | black rice (91% held) | brown rice 98%, the rest 100% |
| 3 | 1.75 (1.9) | rice 88%, white rice 96%, brown rice 100% held | quinoa 91%, couscous 85%, wild rice 64% (end-first) |
| 4 | 1.25 (1.4) | quinoa 100%, couscous 74% held | chia 100% |
| catch | | chia, the smallest couscous | |

Smallest hole per kind, p5 / p50 / p95 in mm: chickpea 7.05 / 7.69 / 8.27, pasta 5.69 / 6.27 / 6.78, black rice 2.22 / 2.36 / 2.50, brown rice 1.88 / 2.03 / 2.19, white rice 1.76 / 1.92 / 2.07, rice 1.71 / 1.86 / 2.02, wild rice 1.54 / 1.72 / 1.86, quinoa 1.47 / 1.62 / 1.77, couscous 0.96 / 1.44 / 1.94, chia 1.02 / 1.09 / 1.17.

Where the groups overlap, so a size class won't be clean:
- **Brown vs white rice** differ by about 0.1 mm at the median. A 1.95 mm tray holds 82% of brown and 36% of white rice. That is the 5-tray run below: a sixth class needs calipers first (GRAINS.md, open questions 3).
- **Couscous** has a 21% size spread, so a quarter of it reaches the catch with the chia, and a few grains stay on 1.75.
- **Wild rice** has the smallest cross-section of the rices but is 10 mm long. It passes a hole only nearly upright, and on the seesaw it stays where it lands.

## The specs

Separate trays: ribs-across inserts (`_across`, ridges along Y only) on the centre-pivot seesaw holders, 55 mm apart, over the deep catch pan. At ±10° neighbours come within 6.07 mm of each other (`rocking.py ... --deg 10 --clear 5` asks for 54.05 mm), and that holds for any number of trays, since only neighbours close in.

```
best, 4 trays: inserts:h4p85b1p35_across,h2p25b1p15_across,h1p75b1p15_across,h1p25b1p15_across,pitch=55,holder=seesaw
first try:     inserts:h4p85b1p35_across,h2p15b1p15_across,h1p75b1p15_across,h1p25b1p15_across,pitch=55,holder=seesaw
5 trays:       inserts:h4p85b1p35_across,h2p15b1p15_across,h1p95b1p15_across,h1p75b1p15_across,h1p25b1p15_across,pitch=55,holder=seesaw
insects:       inserts:h2p85b1p15_across,h1p45b1p15_across,h0p95b1p15_across,pitch=55,holder=seesaw
stroke:        --stroke seesaw:deg=10,period_s=2,vib_mm=0.3,vib_hz=40
```

Bars are 1.35 mm on tray 1 and 1.15 mm on the others (1.2 and 1.0 printed, plus 0.15, as `optimize.py` names them).

Gated (one piece, through `render_site/run_onebox.py`, the optimizer's mid-slot ramp layout, levels not flipped, each slot dropping just upstream of the next gate):

```
3 levels: gated:2.7,t3p35,t1p45,t0p95,tw=4.85,tooth=0.95,slot=8.1/7/7,gx=22.2/38/53,flip=0
4 levels: gated:2.7,t3p35,w2p15x2p15,t1p45,t0p95,tw=4.85,tooth=0.95,slot=8/7/7/7,gx=15/28/41/53,flip=0
stroke:   --stroke seesaw:deg=10,period_s=2,vib_mm=0.4,vib_hz=48,vib_angle_deg=30
```

Every run: `--duration 12 --dt 0.000125 --timeconst 0.00025 --fps 60 --seed 1`, a 1 s settle, then 12 s of shaking. Grains: `pasta=10,chickpea=5,rice=12,white_rice=12,brown_rice=12,black_rice=12,wild_rice=10,quinoa=15,couscous=15,chia=15` (118). Insects: `insect_malaise=60`. Each run took 40–65 s of wall time on one core. There were no unstable resets.

### Code change

`designs_holder.insert_spec` now builds a custom printed screen from its name: `h<hole>b<bar>`, or `h<hole>b<bar>_across` for the ribs-across frame. Before, those names only built inside `optimize.py`'s `inserts_inject`, which plain `sorter.py` doesn't call. The name is added to `sieve_insert.INSERTS` (or `ACROSS`) on first use, with a 1.6 mm screen for holes of 3 mm and up and 1.4 mm below. Names that are already in those dicts (5mm, 2mm, the optimizer's injected ones) are untouched, so earlier runs build exactly as before. Nothing else changed: `inserts:` already took any number of boxes, and `gated:` already took any number of strips.

## Results: grains

Count per level at the end (t = 13 s). "Out" means the grain bounced out of the tower.

### Best: 4 trays, 2.25 mm tray 2 (`out/runs/layers_4tray_l2wide`)

| kind (n) | 4.85 | 2.25 | 1.75 | 1.25 | catch |
|---|---|---|---|---|---|
| pasta (10) | **10** | 0 | 0 | 0 | 0 |
| chickpea (5) | **5** | 0 | 0 | 0 | 0 |
| black_rice (12) | 0 | **12** | 0 | 0 | 0 |
| wild_rice (10) | 2 | 7 | 1 | 0 | 0 |
| rice (12) | 0 | 0 | **11** | 1 | 0 |
| white_rice (12) | 0 | 0 | **11** | 1 | 0 |
| brown_rice (12) | 0 | 0 | **12** | 0 | 0 |
| quinoa (15) | 0 | 0 | 0 | **15** | 0 |
| couscous (15) | 0 | 0 | 1 | **12** | 2 |
| chia (15) | 0 | 0 | 0 | 0 | **15** |

Every kind but wild rice lands on its own tray, with at most 3 strays per kind. Bold is the tray each kind is cut for: 104 of 118 grains ended there. Wild rice is cut for tray 3 but ends on tray 2 with the black rice. Overlap was at most 0.12 mm on the trays and 0.09 mm between particles.

### First try: 4 trays, 2.15 mm tray 2 (`out/runs/layers_4tray_grains`)

| kind (n) | 4.85 | 2.15 | 1.75 | 1.25 | catch | other |
|---|---|---|---|---|---|---|
| pasta (10) | 10 | 0 | 0 | 0 | 0 | |
| chickpea (5) | 5 | 0 | 0 | 0 | 0 | |
| black_rice (12) | 0 | 12 | 0 | 0 | 0 | |
| wild_rice (10) | 2 | 8 | 0 | 0 | 0 | |
| rice (12) | 0 | 0 | 11 | 1 | 0 | |
| white_rice (12) | 0 | 0 | 11 | 1 | 0 | |
| brown_rice (12) | 0 | 1 | 10 | 0 | 0 | 1 out |
| quinoa (15) | 0 | 0 | 0 | 15 | 0 | |
| couscous (15) | 0 | 0 | 1 | 12 | 2 | |
| chia (15) | 0 | 0 | 0 | 0 | 15 | |

Settled by about 7 s; only chia was still trickling into the catch. Widening tray 2 from 2.15 to 2.25 mm (one 0.1 mm print step) kept every black rice and moved the last brown rice down to tray 3, so it's the better cut.

### 5 trays: a 1.95 mm brown-rice tray (`out/runs/layers_5tray_grains`)

| kind (n) | 4.85 | 2.15 | 1.95 | 1.75 | 1.25 | catch |
|---|---|---|---|---|---|---|
| pasta (10) | 10 | 0 | 0 | 0 | 0 | 0 |
| chickpea (5) | 5 | 0 | 0 | 0 | 0 | 0 |
| black_rice (12) | 0 | 12 | 0 | 0 | 0 | 0 |
| wild_rice (10) | 1 | 9 | 0 | 0 | 0 | 0 |
| brown_rice (12) | 0 | 1 | **8** | 3 | 0 | 0 |
| white_rice (12) | 0 | 0 | **4** | 7 | 1 | 0 |
| rice (12) | 0 | 0 | 0 | 11 | 1 | 0 |
| quinoa (15) | 0 | 0 | 0 | 0 | 15 | 0 |
| couscous (15) | 0 | 0 | 1 | 0 | 12 | 2 |
| chia (15) | 0 | 0 | 0 | 0 | 0 | 15 |

The sixth class only half works: the 1.95 tray holds 8 brown rice but also 4 white rice. That matches the size table, so it comes from the grains, not the tower. Don't print it until calipers say brown rice is wider than the sim's 2.2 mm.

### 4 trays with the gated tower's angled shake (`out/runs/layers_4tray_precise`)

The same first-try tower shaken 0.4 mm at 48 Hz, thrown 30° up, instead of 0.3 mm straight up:

| kind (n) | 4.85 | 2.15 | 1.75 | 1.25 | catch | out |
|---|---|---|---|---|---|---|
| pasta (10) | 10 | 0 | 0 | 0 | 0 | 0 |
| chickpea (5) | 5 | 0 | 0 | 0 | 0 | 0 |
| black_rice (12) | 0 | 12 | 0 | 0 | 0 | 0 |
| wild_rice (10) | 3 | 7 | 0 | 0 | 0 | 0 |
| rice (12) | 0 | 2 | 10 | 0 | 0 | 0 |
| white_rice (12) | 0 | 6 | 6 | 0 | 0 | 0 |
| brown_rice (12) | 0 | 5 | 7 | 0 | 0 | 0 |
| quinoa (15) | 0 | 0 | 3 | 11 | 0 | 1 |
| couscous (15) | 0 | 0 | 3 | 8 | 2 | 2 |
| chia (15) | 0 | 0 | 0 | 4 | 9 | 2 |

Worse on every small class, and the overlap on the trays reached 0.30 mm. The gated tower needs the throw to walk grain to its gates; separate trays only need the grains lifted off the ribs. Keep the vertical 0.3 mm buzz for trays.

### Gated, 3 levels (`out/runs/layers_gated3_grains`)

| kind (n) | L1 t3.35 | L2 t1.45 | L3 t0.95 | catch |
|---|---|---|---|---|
| pasta (10) | **10** | 0 | 0 | 0 |
| chickpea (5) | **5** | 0 | 0 | 0 |
| rice (12) | 1 | **11** | 0 | 0 |
| white_rice (12) | 0 | **12** | 0 | 0 |
| brown_rice (12) | 0 | **12** | 0 | 0 |
| black_rice (12) | 1 | **11** | 0 | 0 |
| wild_rice (10) | 0 | **10** | 0 | 0 |
| quinoa (15) | 0 | 3 | **12** | 0 |
| couscous (15) | 0 | 8 | **7** | 0 |
| chia (15) | 0 | 2 | 4 | **9** |

Tunnels sort by thickness, which puts all five rices in one class, so the gated tower gives 4 classes from 3 levels. It keeps 56 of the 58 rice grains on L2, and it was still sorting at 12 s: chia reached the catch at about one grain a second and 8 couscous were still on L2. Give it 30 s before judging the fines.

### Gated, 4 levels with a window gate (`out/runs/layers_gated4_grains`)

| kind (n) | L1 t3.35 | L2 w2.15×2.15 | L3 t1.45 | L4 t0.95 | catch | other |
|---|---|---|---|---|---|---|
| pasta (10) | 10 | 0 | 0 | 0 | 0 | |
| chickpea (5) | 5 | 0 | 0 | 0 | 0 | |
| black_rice (12) | 1 | **11** | 0 | 0 | 0 | |
| wild_rice (10) | 0 | 8 | 1 | 0 | 0 | 1 between |
| rice (12) | 1 | 5 | 6 | 0 | 0 | |
| white_rice (12) | 1 | 5 | 6 | 0 | 0 | |
| brown_rice (12) | 2 | 6 | 4 | 0 | 0 | |
| quinoa (15) | 0 | 1 | 2 | 12 | 0 | |
| couscous (15) | 1 | 3 | 2 | 9 | 0 | |
| chia (15) | 0 | 0 | 1 | 3 | 11 | |

A square window in a gate strip is not a square hole in a floor. It holds the black rice, but grains reach it lying flat, and nothing tips them on end, so it also holds half of every other rice. A 4-level gated tower needs a different L2 (see below).

## Results: Malaise insects

60 specimens of `insect_malaise`, by body length, on two towers. "In holes" counts specimens left sunk into a hole of that tray (the sim reports them as `between`; their bodies sit at the screen's top surface, legs caught). "Out" means bounced out of the tower, most of them < 1 mm specimens light enough to fly off.

Body cross-section alone would put the cuts at about 2.8 mm (6 mm body), 1.45 mm (4 mm) and 0.7 mm (2 mm), and 0.3 mm (1 mm), from 2,500 drawn specimens. The last two are too small to print. Legs and wings hold specimens on holes 2–3 times wider than that.

### Insect-cut tower, 2.85 / 1.45 / 0.95 mm (`out/runs/layers_insect3_malaise`)

| body length | n | 2.85 | 1.45 | 0.95 | catch | out |
|---|---|---|---|---|---|---|
| > 6 mm | 3 | 3 (1 in holes) | 0 | 0 | 0 | 0 |
| 4–6 mm | 2 | 1 | 1 | 0 | 0 | 0 |
| 2–4 mm | 16 | 7 (2 in holes) | 9 (2 in holes) | 0 | 0 | 0 |
| 1–2 mm | 20 | 0 | 8 (5 in holes) | 9 (1 in holes) | 2 | 1 |
| < 1 mm | 19 | 0 | 0 | 1 | 13 | 5 |

The trays rank the specimens in the right order. Tray 1 gets everything over 6 mm and the larger 2–4 mm specimens. Tray 2 gets the rest of the 2–4 mm and the larger 1–2 mm. Tray 3 gets the other 1–2 mm, and the catch the < 1 mm. So the classes are close to BugPicker's finer split (> 6 with the large 2–4 / 2–4 / 1–2 / < 1 mm), with each boundary blurred by a few specimens. 11 specimens are snagged in holes, which a real tower would release with the spray, and which would hurt specimens if the shake were rougher. Overlap on the trays reached 0.59 mm (legs).

### The 4-tray grain tower (first try) (`out/runs/layers_4tray_malaise`)

| body length | n | 4.85 | 2.15 | 1.75 | 1.25 | catch | out |
|---|---|---|---|---|---|---|---|
| > 6 mm | 3 | 3 | 0 | 0 | 0 | 0 | 0 |
| 4–6 mm | 2 | 1 | 1 | 0 | 0 | 0 | 0 |
| 2–4 mm | 16 | 0 | 12 (5 in holes) | 2 | 2 (1 in holes) | 0 | 0 |
| 1–2 mm | 20 | 0 | 2 (1 in holes) | 2 (2 in holes) | 8 (6 in holes) | 8 | 0 |
| < 1 mm | 19 | 0 | 0 | 0 | 0 | 10 | 9 |

Grain-sized holes split insects into > 6 / 2–6 / < 2 mm only roughly, and 9 of the 19 smallest bounced out. Use insect-cut trays for insects.

## What I'd change next

1. **Wild rice.** No square hole fixes it: it ends with the black rice on tray 2 in every run. Options: accept a "dark rice" class (black + wild), or put long slots (about 2.0 × 12 mm, running along X) in tray 2 so the needles drop flat. Black rice would pass a 2.0 mm slot on edge too, so that needs a slot test first.
2. **Measure the grains** before adding a sixth class. Brown vs white rice is a 0.1 mm question (GRAINS.md, open questions 2–3).
3. **Gated 4-level.** Replace the window gate with a tunnel of a different width (`tw` is one value for every level today; a per-level `tw=` would let L2 hold black rice by width), or run the 3-level tower above the 4-tray tower's tray 2.
4. **Insects:** more seeds (one 60-specimen run has only 3 specimens over 6 mm), the spray on to free snagged specimens, and a lip or higher end walls so < 1 mm specimens don't bounce out.
5. **Longer runs** for the gated tower (30 s) and a second and third seed for the best tower before quoting any numbers. The ±10°, 2 s seesaw and the buzz are still assumptions (SYSTEM.md §3).

## Replays

All runs are in `sim/render_site/runs_def.py` under "More levels (multi-layer)", the first group in the Sieve Render Lab. Run folders are in `testSieveSorter-layers/sim/out/runs/` (gitignored, this laptop only).
