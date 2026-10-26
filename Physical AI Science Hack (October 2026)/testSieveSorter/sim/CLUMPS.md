# Clumps in the sim: breaking up the real input

Clump session, 2026-10-25. Task: [docs/sessions/clump-breakup.md](../docs/sessions/clump-breakup.md) part A, under [docs/SYSTEM.md](../docs/SYSTEM.md). A Malaise sample arrives as a compacted ball of tangled insects mixed with leaves, twigs and dirt, and breaking it apart gently is the system's real job. Code: `clumps.py`, a few hooks in `sorter.py`, and `clump_study.py` for the comparisons.

**Everything about bond strength is assumed.** Nobody has measured what holds a Malaise clump together, so every number below ranks motions and designs against each other. None of it predicts a real break-up time (SYSTEM.md §5).

## The model

### The clump
- **What's in it.** Any mix of `insects.py` kinds (`insect_elongate`, `insect_compact`, `insect_longleg`) or `grains.py` surrogates (rice, quinoa, pasta, chickpea), plus debris. Every specimen is its own free rigid body, so a freed one is an ordinary particle.
- **Packing.** A short pre-sim of the clump alone, before the run. With no gravity, every body is pulled toward the clump's centre of mass at 3 g, with its speed damped, for 0.4 s. Each leaf is then laid against the ball's surface (mostly the upper half) and pressed on for 0.15 s, so it sticks to the outside instead of splitting the ball. Finally the pull is switched off and the pile relaxes for 0.12 s while its contacts stiffen in four steps from 2 ms to the run's own time constant (and timestep), so the run starts with no contact loaded. Grains end with no overlap left; interlocked insect legs keep about 0.1 mm. Grains pack with MuJoCo's CG solver, 6× faster there; insects pack with Newton, because CG blew up on their legs.
- **Bonds.** Every pair of bodies whose geoms come within 0.3 mm of each other gets a MuJoCo equality: `connect` by default (a ball joint at the contact point: it carries force, not torque, like tangled legs or a liquid bridge), or `weld` (`type=weld`, which also locks orientation). The bonds are made at the packed pose, which becomes the model's `qpos0`, so they start exactly satisfied. The demo clump (50 rice, 50 quinoa, 6 pasta, 1 leaf, 2 twigs, 10 dirt) packs to a ball about 20 mm across, with 407 bonds (about 7 per specimen) under the first relax and 432 under the staged one.
- **Breaking.** After every step, a bond's load is the norm of its three position rows in `d.efc_force` (a weld adds its rotation rows divided by the bond's radius). Once the load exceeds

  `bond_N(w) = sigma · r_pair · (1 − k_wet · w)`

  `d.eq_active` goes to 0 and stays there. Here `r_pair = 2 r1 r2 / (r1 + r2)` is the harmonic mean of the two bodies' half widths. A capillary bridge pulls with 2πγR, so strength per mm of radius is the natural unit. `w` is the mean wetness of the two bodies from `spray.py` (0 without spray), and `k_wet` = 0.6 (ASSUMED) is how much full wetting weakens a bond.
- **The settle sets the clump down; it doesn't drop it.** `sorter.py`'s settle damps every speed to about 100 mm/s, and a brittle ball landing on stiff contacts even at that speed shatters (468 of 470 bonds broke in the settle on the first try). So bonds can't break before the shake starts, and loads during the settle aren't counted.

### Bond sets (ASSUMED)
| set | sigma (µN per mm of r_pair) | rice–rice bond (r_pair 1 mm) | × a rice grain's weight | where it sits |
|---|---|---|---|---|
| weak | 5,000 | 5 mN | 30 | just above the clump's own weight at rest |
| medium | 10,000 | 10 mN | 60 | p99 of the load over one ±10° cycle |
| strong | 25,000 | 25 mN | 150 | the maximum load over one ±10° cycle |

The sets sit on the loads the clump itself sees, so they bracket the break-up by construction. With unbreakable bonds, a bond's peak load over r_pair, in µN/mm (demo clump, `inserts:5mm,2mm`):

| case | p50 | p90 | p99 | max |
|---|---|---|---|---|
| lying still on the 5 mm tray (pitch 85, no stroke) | 140 | 600 | 2,130 | 4,530 |
| one ±10°, 2 s seesaw cycle (pitch 85) | 1,340 | 4,680 | 10,060 | 25,700 |
| one ±25°, 2 s seesaw cycle (pitch 110) | 3,040 | 12,270 | | |

- **Weaker than about 5,000 isn't a clump.** It falls apart under its own weight as soon as it is set down. That includes my first sets (150–1,500, from the capillary-bridge estimate). At ±10°, sigma 300 frees every specimen within 18 ms of the shake starting and 1,000 within 35 ms: in that time the trays turn less than 1°. Even 3,000 leaves a few bonds overloaded at rest, and the failure cascades (79% free, t50 0.12 s).
- **Fully wet, the sets drop by 60%** (k_wet 0.6): strong to 10,000 (medium), and medium to 4,000, below what holds the clump up. So spray should matter.
- **For insects these numbers are only a start.** A 3 mg fly weighs about 1/6 of a rice grain, and its bonds have about half the radius, so the same sigma holds it about 3× more strongly for its weight. The insect clump has its own calibration below.

### Debris
| kind | shape | size | density (g/mm³) | notes |
|---|---|---|---|---|
| `leaf` | thin box | 12–30 mm long, 0.5–0.9 as wide, 0.2 mm thick | 0.8e-3 | **Rigid.** Real leaf bits bend and wrap round the clump and the bars. |
| `twig` | capsule | 1–3 mm across, 10–30 mm long | 0.75e-3 | wet wood |
| `dirt` | sphere | 0.5–1 mm across | 2.6e-3 | Real soil goes down to 0.1 mm. Grains under 0.5 mm need a smaller timestep and pass every screen anyway, so they're left out. |

Debris can be part of the clump (`--clump ...,leaf=1`) or loose (`--mix leaf=2`).

### Metrics (`results["clumps"]`)
- **Break-up.** `free_frac`: the share of the clump's specimens with no live bond, over time (`timeseries`). `t50_s` / `t90_s`: seconds from the start of the shake until half / 90% are free (null if never). `largest_cluster`: the most specimens still bonded together at the end. Debris counts as glue in a cluster, but only specimens are counted.
- **Damage proxy.** The peak contact normal force on each specimen over the shake (sum of the pyramid edge forces of each contact), as p50 / p90 / max, plus the share over `fragile_mN` (default 5 mN, ASSUMED, a parameter). The same numbers are also given counted only while the specimen is still bonded (`bonded_*`): that's what the break-up itself does, as against the drops between levels once a specimen is free. A landing gives roughly m·v / timeconst, so these peaks scale with the contact stiffness. They rank strokes and designs; don't quote them as newtons.
- **Leaf blinding.** The share of each printed screen's holes that lie under a leaf lying flat on it: within 2 mm of the top surface and tilted less than 30° from it, tested in that level's own (rocking) frame.
- **Sort.** For the clump's specimens, the share in their ideal zone by kind, and where the debris went. The run's usual `counts` and `recovery` cover every particle.

### Solver
The run itself uses Newton. On the seesaw tower the driven trays weigh 1e6 g against milligram grains. There CG and PGS hit their iteration cap, and their constraint forces disagree with Newton's: in the same 0.3 s, the bond-load p90 was 5.7 mN with CG, 0.9 with PGS and 1.4 with Newton. Those forces are exactly what breaks bonds, so clump runs keep Newton (`solver=` switches). It costs about 12 ms per step for a 120-body clump: a 10 s seesaw run takes about 20 minutes on one core.

## Running it

```
wsl: cd sim
python sorter.py --design breaker:open=8,bar=1.6,pin_d=2.5,pin_h=12,pitch=10,tip=round --mix "" \
    --clump rice=50,quinoa=50,pasta=6,leaf=1,twig=2,dirt=10,bond=medium --spray default \
    --stroke seesaw:deg=10,period_s=2,vib_mm=0.3 --duration 4 --dt 0.000125 --timeconst 0.00025 --fps 30 --out out/runs/brk_grain_spray
python viewer.py out/runs/brk_grain_spray --rig bugsorter
python clump_study.py --name spray10 --duration 6 --record  # bond sets x spray on/off on inserts:5mm,2mm,pitch=85, +/-10 deg
python clumps.py rice=50,quinoa=50,pasta=6,leaf=1           # pack one clump and print it
```

`--clump` takes the kinds and these options: `bond` (weak / medium / strong, or sigma in µN/mm), `k_wet`, `type` (connect / weld), `gap_mm`, `timeconst` (bond softness, s), `fragile_mN`, `pull_g`, `seed`, `solver`. From Python, `RunConfig(clump={"kinds": {...}, "bond": "medium", ...})` or `clumps.parse("rice=50,...")`.

## Results

All on the demo stack `inserts:5mm,2mm` (5 mm over 2 mm over the catch pan), seesaw with neighbours alternating, constant angular speed, 2 s per cycle, dt 0.125 ms, contact time constant 0.25 ms, friction 0.4, one seed. The demo clump is the bench surrogate: 50 rice, 50 quinoa, 6 pasta, 1 leaf, 2 twigs, 10 dirt. It's about 20 mm across, with 407 or 432 bonds (two packings: see the note under the table in section 3).

### 1. It builds and breaks: the first run (±25°, PR #17)
Pitch 110, sigma 3,000 (below what now counts as weak), 10 s: 10.4 min wall, no unstable resets, overlap ≤ 0.18 mm.
- 84% of the specimens are free by 0.4 s and 89% by 5 s. t50 0.09 s; t90 never. Clusters of up to 8 specimens stay bonded to the end.
- Freed grains sort as on the plain seesaw tower: rice 34/50 on 2 mm, quinoa 26/50 in the catch, pasta 6/6 on 5 mm. 17 quinoa are still on 5 mm, in the leftover clusters and on the rails SEESAW.md describes.
- Replay: `out/runs/clump_seesaw/view.html`. The ball sits on 5 mm, grains rain through as it breaks, and freed rice and quinoa spread over 2 mm.
- **SYSTEM.md has since moved the default to ±10°** (the user found ±25° too wide), and the bond sets were re-placed (above). Everything below is at ±10°, pitch 85.

### 2. The break-up is a brittle cascade
| stroke | sigma | free after | t50 | largest cluster left |
|---|---|---|---|---|
| ±10°, pitch 85, 5 s | 300 | 100% | 0.01 s | 1 |
| | 1,000 | 100% | 0.02 s | 1 |
| | 3,000 | 79% | 0.12 s | 10 |
| ±25°, pitch 110, 2 s | 3,000 | 85% (89% at 10 s) | 0.09 s | 8 |
| | 10,000 | 6% | never | 100 |
| | 30,000 | 0% | never | 106 |
| | 100,000 | 0% | never | 106 |

Between 3,000 and 10,000 the clump goes from shattering at the first motion to barely chipping. Once a few bonds fail, their load moves onto their neighbours and the network unzips: in the 3,000 run at ±10°, the first bond went at the first step of the shake (it was already over its limit at rest), and 323 of the 367 that broke went within one 50 ms window. That's the nature of brittle bonds with no ductility or fatigue. Real tangled legs probably fail more gradually, which the model can't show yet.

### 3. Spray on vs off, three bond sets, ±10°
`clump_study.py --name spray10 --duration 6 --record`: the demo clump on `inserts:5mm,2mm,pitch=85`, `seesaw:deg=10,period_s=2`, 6 s (3 cycles). Spray is the design's placeholder jets: two jets 60 mm above the top surface, straight down, 5 mL/s of water each. No unstable resets in any run.

| bond | spray | free at 1 s | free at 2 s | free at 6 s | largest cluster left (of 106) | bonds broken | peak force p90, all / in the clump (mN) | over 5 mN, all / in the clump |
|---|---|---|---|---|---|---|---|---|
| weak | off | 14% | 14% | **14%** | 89 | 177 / 407 | 104 / 46 | 65% / 62% |
| weak | on | 36% | 49% | **49%** | 52 | 307 / 407 | 163 / 34 | 92% / 82% |
| medium | off | 0% | 0% | **1%** | 105 | 55 / 407 | 34 / 34 | 45% / 45% |
| medium | on | 0% | 0% | **1%** | 105 | 84 / 432* | 32 / 32 | 72% / 72% |
| strong | off | 0% | 0% | **0%** | 106 | 5 / 432* | 47 / 47 | 59% / 59% |
| strong | on | 0% | 0% | **0%** | 106 | 13 / 432* | 44 / 44 | 68% / 68% |

\* **Two packings.** A fix to the packing relax (stiffening the contacts in stages, for insects) landed while the study was running. The study spawns a fresh process per run, so the runs that started after it packed a slightly different clump: 432 bonds and 20.2 mm across, against 407 and 20.7 mm. Each spray on/off pair stays within one packing for weak (407) and strong (432). Medium crosses packings, but both medium runs free 1%.

Where things ended (weak bonds):
- **Spray off:** rice 41 on 5 mm, 7 on 2 mm, 2 in the catch. Quinoa 49 on 5 mm, 1 in the catch. Pasta 6 on 5 mm.
- **Spray on:** rice 19 on 5 mm, 30 on 2 mm, 1 in the catch. Quinoa 42 on 5 mm, 7 in the catch, 1 on 2 mm. Pasta 6 on 5 mm.

The leaf stayed stuck to the clump in every run, so leaf blinding stayed at 0%. It needs a run with loose leaves (`--mix leaf=2`).

What the table says:
1. **The break-up happens in the first tilt, then stalls.** Each run frees what it will within 1–2 s, and nothing more comes off over the next two cycles. The ball doesn't roll. In the weak, spray-off run, the bonded ball's centre stays within 2 mm of where it landed, over the top tray's pivot, for all 6 s, while the tray tips ±10° under it. Its lower grains sit in the 5 mm holes. ±10° is well under the ~22° at which grains slide on plastic, so once the first tilt has shed what was loose, nothing more hits or loads the ball. **The seesaw alone doesn't finish a clump.** That's the job of the pins (the breaker layer) or of a faster component in the motion (seesaw + vibration).
2. **Spray roughly triples what's freed** with weak bonds (49% against 14%). The largest cluster drops from 89 to 52. Wetting takes up to 60% off a bond (k_wet), and it reaches only the outside of the clump, so the spray peels the ball from the top. It's the only thing in this table that keeps working after the first tilt (36% → 49% between 1 and 2 s).
3. **Medium and strong bonds survive the plain seesaw,** spray or not: 1% and 0% freed, largest cluster 105–106. Spray breaks a few more strong bonds (13 against 5 of 432), but not enough to free anything.
4. **Most of the damage proxy comes from falling, not from breaking.** In the clump, p90 is 34–46 mN. Once freed grains fall 85 mm between levels, it rises to 104–163 mN. More freeing means more drops, so a lower fall between levels (pitch) or a softer landing may matter more for gentleness than the breaker itself.

### 4. With the breaker layer and the buzz
The CAD default breaker (`breaker:open=8,bar=1.6,pin_d=2.5,pin_h=12,pitch=10,tip=round`, a holder box on top of the 5 mm / 2 mm trays, 85 mm apart) on the ±10°, 2 s seesaw plus the tool's 0.3 mm, 40 Hz vertical buzz (`vib_mm=0.3`, 1.9 g). Demo clump (432-bond packing), **medium** bonds, 4 s. On `main`'s faster seesaw these runs took 7.5 min each.

| | spray | free at 1 s | free at 2 s | free at 4 s | t50 | t90 | largest cluster | peak force p90, all / in the clump (mN) |
|---|---|---|---|---|---|---|---|---|
| plain seesaw, no breaker (section 3) | off | 0% | 0% | 1% | never | never | 105 | 34 / 34 |
| breaker + buzz | off | 77% | 81% | **81%** | 0.49 s | never | 17 | 299 / 142 |
| breaker + buzz | on | 84% | 92% | **92%** | 0.19 s | 1.37 s | 8 | 246 / 101 |

- **The pins and the buzz do the breaking.** The same medium clump goes from 1% freed to 81–92%. That agrees with the optimizer's round 0, which uses PR #17's weaker sets: 31% without a breaker and 85% with the CAD default breaker and buzz.
- **Spray helps on the breaker too:** 92% against 81%. It halves t50 and brings t90 within reach (1.4 s). It also lowers the peaks, probably because a wetter clump breaks sooner and is hammered less.
- **The price is gentleness.** In the clump, the peak-force p90 goes from 34 mN on the plain seesaw to 100–140 mN, and every specimen passes 5 mN while still bonded. A 1.9 g buzz throws the clump onto the pins at 40 Hz. Somewhere between "doesn't break" and "hammers" is the stroke to look for, and the optimizer's gentleness term should drive that search.
- **Sort:** the leaf stays on the breaker (scalped) and pasta stays on 5 mm (4–5 of 6; 1–2 are held on the breaker). With the buzz, most rice goes on through 2 mm to the catch (28–31 of 50), corner to corner, where the sim's ideal rule puts it anyway. Quinoa reaches the catch (34–41 of 50).
- Replays: `out/runs/brk_grain_dry/view.html`, `out/runs/brk_grain_spray/view.html`.

### 5. An insect clump
The real input is insects. The clump: 40 `insect_elongate` (flies, wasps, ants), 10 `insect_compact` (beetles, mites), 10 `insect_longleg` (mosquitoes, crane flies, spiders), 1 leaf, 1 twig and 5 dirt, from `insects.py` as it stands. **That mix has too few small specimens:** INSECT_AUDIT.md says real Malaise samples are 56–58% under 1.5 mm. The physics session's `insect_malaise` kinds (now on `main`) have the real shares, and they pack too (below); the next insect runs use them.
- **Packing:** 45 s, with Newton (CG blew up on the interlocked legs within 0.03 s). The ball is 16 mm across (38 mm counting the leaf and twig), with 273 bonds, 8.4 per specimen. Interlocked legs keep about 0.1 mm of overlap after the relax.
- **Loads with unbreakable bonds,** over r_pair in µN/mm:

  | case | p50 | p90 | p99 | max |
  |---|---|---|---|---|
  | lying still on 5 mm | 27 | 146 | 389 | 413 |
  | one ±10° cycle | 4,700 | 17,200 | 29,200 | 43,500 |

  At rest the bonds carry almost nothing, because insects are light. But one gentle cycle loads them about 100× more, and more than the grain clump (p50 1,340). The likely cause is legs. A leg that drops into a 5 mm hole gets dragged by the driven tray as it turns, and the bonds pass that pull to the rest of the clump. The audit's note that the glued mesh jams 17 specimens per run points the same way. In the sim, **legs catching on the grid are what loads an insect clump**, so pins and grid geometry should matter even more for insects than for grains.
- On these loads the grain sets also span the insect clump: weak (5,000) ≈ the cycle's p50, medium ≈ p75, strong ≈ p95.
- **Breakable, medium bonds, ±10°, 4 s (2 cycles), spray off:** 7% free and the largest cluster is 56 of 60 (10 min wall, no unstable resets, ≤ 0.05 mm on the tray). Like the grain clump, the plain seesaw sheds a few specimens and stops. Replay: `out/runs/insect_medium_dry/view.html`.
- **The real Malaise mix (`insect_malaise=40`) needs half the timestep.** It packs to an 11 mm ball with 125 bonds. At dt 0.125 ms, though, every run had MuJoCo resetting the state within the first 0.23–0.33 s of the settle, again and again, so **those results aren't valid**. Tried:

  | setup | contacts | dt (ms) | resets |
  |---|---|---|---|
  | on the breaker + buzz, with debris, spray off / on | 0.25 ms | 0.125 | 3 / 4 |
  | on the breaker + buzz, with debris | 0.5 ms | 0.125 | 3 |
  | on the breaker + buzz, no debris | 0.25 ms | 0.125 | 6 |
  | plain tower (no breaker), with debris | 0.25 ms | 0.125 | 4 |
  | on the breaker + buzz, with debris | 0.25 ms | **0.0625** | **none** |

  It's not the breaker, the debris or the contact stiffness: **dt 0.0625 ms fixes it.** The likely cause is the mix's tiny specimens (down to 0.3 mm long), whose bonds are anchored out on legs around very small rotational inertia. **Run `insect_malaise` clumps at `--dt 0.0000625`.** That doubles the cost: 1.5 s took 2.6 min. The old kinds (`insect_elongate` / `_compact` / `_longleg`) run at 0.125 ms.
- **The real Malaise mix on the breaker + buzz** (`insect_malaise=40,leaf=1,twig=1,dirt=5`, medium bonds, dt 0.0625 ms, 4 s, as in section 4). Both runs were stable, at 6–9 min wall:

  | spray | free at 1 s | free at 2 s | free at 3 s | free at 4 s | t50 | largest cluster (of 40) | where they ended |
  |---|---|---|---|---|---|---|---|
  | off | 28% | 35% | 35% | **35%** | never | 22 | 27 on the breaker, 11 in the catch, 2 between levels |
  | on | 30% | 43% | 53% | **60%** | 2.8 s | 10 | 22 on the breaker, 3 on 5 mm, 1 on 2 mm, 10 in the catch, 4 between levels |

  - **Insects come apart more slowly than grains** on the same breaker and stroke: 35% dry against 81%, and 60% wet against 92%. The legs keep specimens hooked to each other and to the pins.
  - **Spray matters more for insects.** Dry, the break-up stops at 2 s. With spray it's still going at 4 s (43% → 53% → 60%), so a longer run with spray would free more. Of everything tried, this is the clearest case for keeping the jets on.
  - Freed insects mostly drop through to the catch or are still falling between levels: 13 of 14 dry, 14 of 24 with spray. Real Malaise specimens are mostly under 2 mm, so that's where most belong. The 27 / 22 "on the breaker" are mostly specimens still in clusters (26 / 16 of them are still bonded).
  - Replays: `out/runs/brk_malaise_none/view.html`, `out/runs/brk_malaise_default/view.html`.
- **Don't read the insect damage proxy yet.** Lying still, the insect clump already shows a contact p90 of 26 mN. That's the 0.1 mm of leg overlap left by packing, pushing against stiff contacts. It's not damage, and it hides the real peaks. The fix is a longer or softer relax for insect clumps, or running them with softer contacts. Until then, use the break-up numbers only.

### 6. The breaker that's being printed (B-164f355a), spray on vs off
The optimizer's verified Malaise #1, sliced for the P1S (print_plan.md): `breaker:open=11.3,bar=1.6,pin_d=3.1,pin_h=8,pitch=8.5,tip=round`, on its stroke, a ±7° seesaw at 1.1 s with a 0.35 mm, 40 Hz buzz. Medium bonds (this PR's sets), 4 s, one seed. Grains at dt 0.125 ms; insects at 0.0625 ms. No unstable resets; 4–4.5 min wall each.

| clump | spray | free at 1 s | 2 s | 3 s | 4 s | t50 | t90 | largest cluster | peak p90 in the clump (mN) |
|---|---|---|---|---|---|---|---|---|---|
| grain surrogate (106) | off | 69% | 92% | 92% | **92%** | 0.24 s | 1.36 s | 7 | 94 |
| grain surrogate | on | 100% | 100% | 100% | **100%** | 0.21 s | 0.59 s | 1 | 115 |
| `insect_malaise` (40) | off | 18% | 23% | 25% | **25%** | never | never | 30 | 27 |
| `insect_malaise` | on | 13% | 20% | 33% | **90%** | 3.25 s | 3.84 s | 2 | 61 |

- **On the printed breaker, spray takes the real-mix insect clump from 25% to 90% freed.** Dry, the break-up stops at 2 s. Wet, it holds for 3 s and then collapses (33% → 90% between 3 and 4 s): the wetting builds up until enough bonds are weak for the network to cascade. One seed: read it as "spray is what finishes an insect clump", not as a percentage.
- **For grains it beats the CAD default** (92% / 100% against 81% / 92% in section 4), on a gentler tilt (±7° against ±10°) and with a lower in-clump peak dry (94 against 142 mN).
- **Where things went (spray on).** Grains: rice 39 of 50 and quinoa 44 of 50 in the catch, pasta 6 of 6 on 5 mm, and the leaf held on the breaker. Insects: 15 in the catch, 12 on 2 mm, 6 on 5 mm, and 2 still on the breaker.
- Replays: `out/runs/pr_grain_default/view.html`, `out/runs/pr_malaise_default/view.html` (and `_none` for dry).

## What it means for the breaker and the optimizer
- **Headline: on the breaker being printed, with the buzz and the spray on, the sim frees 100% of the grain surrogate clump and 90% of a real-mix insect clump in 4 s. Without spray, the insect clump stops at 25%.** That's one seed, with assumed bond strengths. It's a ranking, not a prediction.
- **The ±10° seesaw shifts the clump once, then holds it still.** In the sim, a clump that can hold itself up comes through three ±10° cycles mostly intact, so the break-up has to come from something else: the **breaker's pins** (they load the ball wherever it sits), a **fast component** in the motion (the seesaw + vibration stroke), a **steeper or faster tilt**, or **spray**. Without those, `study malaise` will mostly measure how much of the clump falls off in the first tilt.
- **The breaker and the buzz do the work, and spray finishes it.** On the CAD default breaker with the 0.3 mm, 40 Hz buzz, a medium clump is 81% freed dry and 92% with spray (1% on the plain seesaw). Spray is the only thing in these runs that keeps freeing specimens after the first second or two, so keep it on.
- **But the buzz hammers.** In the clump, the peak-force p90 rises from about 34 mN to 100–140 mN on breaker + buzz. The stroke to look for frees the clump with the least buzz, and the gentleness term is what should find it.
- **Insects need the spray most.** The real-mix insect clump on breaker + buzz frees 35% dry and 60% wet, and wet it's still freeing at the end of the run. Grains: 81% and 92%. A Malaise study scored dry will undersell the rig.
- **Score gentleness on the fall too.** The damage proxy is dominated by the 85 mm drops between levels, not by the break-up. A design that frees more specimens also drops more of them. Use `damage.bonded_*` for "did the breaker hurt them" and `damage.p90_mN` / `share_over` for the whole trip.
- **For `study malaise`:** with `main`'s faster seesaw, a 4 s run of this 120-body clump on the breaker takes about 7.5 min on one core at dt 0.125 ms (it was 10–30 min for 6 s before). Use one seed per bond set, or a smaller clump (e.g. 30 specimens). Rank by `free_frac`, then `largest_cluster`, then the damage numbers. t50 / t90 are often null on a plain seesaw.
- **The optimizer's Malaise round 0 (PR #27) agrees:** a medium-bond grain clump sits whole without a breaker, and breaker + seesaw + buzz frees it.
- **Insect clumps pack now.** On PR #17's code, insect clumps blew up while packing: the optimizer's LOG reports a 75 m "diameter" with 12 bonds for `insect_malaise=40`. Two changes fix it. Insects now pack with Newton (CG blew up within 0.03 s), and the relax stiffens the contacts in four stages instead of jumping to the run's stiffness. With them, `insect_malaise=40` packs to 11 mm with 125 bonds, and `insect_malaise_2to6=30,insect_malaise_gt6=5,leaf=1,twig=1,dirt=5` packs to 20 mm with 148 bonds (both at contact time constant 0.25 ms; about 30 s each). **But `insect_malaise` clumps need dt 0.0625 ms** (section 5): at 0.125 ms they go unstable in the settle.
- **Next to run here:** the optimizer's leader B-32a7c82c with spray on and off; loose leaves for blinding; and more seeds.

## Limits
- **Bond strength, k_wet and the fragility threshold are assumptions,** and the sets are placed on the sim's own loads. The ranking across designs is what to use. Absolute times aren't.
- **Brittle bonds:** a bond holds fully until it snaps, with no stretching, no fatigue and no re-bonding when specimens touch again. Real tangled legs and liquid bridges are more ductile, and wet specimens re-stick. So this model overstates cascades and understates re-clumping.
- **Rigid specimens, rigid leaves:** legs don't snap, leaves don't fold. The damage proxy stands in for broken legs.
- **No liquid in the tray:** the spray pushes and wets (spray.py), but nothing floats or drains, and nothing has drag in air or in ethanol. So landings in the sim are probably harder than real ones, especially for insects, which in liquid weigh only 5–13% of their dry weight (INSECT_AUDIT.md).
- **The settle is a numerical set-down.** Real clumps are tipped onto the tray from a jar, which is harsher than the sim's 100 mm/s set-down.
- **Cost:** in these runs, Newton took about 12–19 ms per step for a 120-body clump, so a 6 s ±10° run took 10–35 min on one core, depending on the load. `main` has since put the seesaw's level bodies before the particles (about 20× faster per step for the seesaw), and these runs predate that. The optimizer gets about 3.5 min per 4 s run at dt 0.25 ms.
