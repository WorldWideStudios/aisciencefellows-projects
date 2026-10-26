# EXPLORATORY: clump break-up leaderboard (study malaise)

Updated 2026-10-25 13:29 by `sim/opt_malaise.py` (31 candidates, 147 runs).

**EXPLORATORY. The sim ranks designs; it isn't calibrated against bench counts.** The clump's bond strengths are assumed (clumps.py) and so is the 5 mN damage line. Read the scores as a ranking, not as percentages.

**The clump is the bench-demo grain surrogate, not insects.** Every insect clump (`insect_malaise` and its class kinds, `insect_compact` + `insect_elongate`) blew up in `clumps.pack`'s pre-sim at 12:55 (QACC NaN), so the real Malaise clump waits for that fix.

- **Clump:** rice 30, quinoa 20, pasta 4, leaf 1, twig 2, dirt 6. Robust = mean - sd over the three bond sets (weak / medium / strong) at friction 0.4, seed 0, 4 s of seesaw after a 1 s settle, no spray (dry bonds: the hardest case).
- **Tower:** the breaker in a holder box on top of the demo rig's trays (5mm over 2mm over the catch pan), 85 mm apart. Every level rocks on its own hinge across its middle, and neighbours alternate (rocking.py).
- **Score per run:** 0.5 x break-up (0.75 x free share + 0.25 x speed from t90) + 0.3 x gentleness (half: share never over 5 mN while still in the clump; half: the peak-force p90 on a log scale, 1 at 5 mN, 0 at 500 mN) + 0.2 x sort (specimens in their ideal zone). A failed run scores -1.
- **Winners** are verified designs only (rerun on freshly packed clumps, seeds 1-2), ranked by the lower of the seed-0 robust and the robust over every seed. The top-10 table is seed 0 only.

## Winners (verified on fresh clumps)

| # | id | design and stroke | winner score | robust, all seeds | free, fresh seeds | breaker for the CAD |
|---|---|---|---|---|---|---|
| 1 | B-164f355a | grid 11.3 mm (bars 1.6), pins 3.1 x 8 mm round every 12.9 mm; seesaw +/-7 deg, 1.1 s + 0.35 mm buzz at 40 Hz | **0.630** | 0.630 | 94% | `breaker:open=11.3,bar=1.6,pin_d=3.1,pin_h=8,pitch=8.5,tip=round` |
| 2 | B-87f42099 | grid 8.9 mm (bars 1.2), pins 2 x 7.6 mm flat every 10.1 mm; seesaw +/-8 deg, 3.5 s + 0.35 mm buzz at 40 Hz | **0.605** | 0.605 | 94% | `breaker:open=8.9,bar=1.2,pin_d=2,pin_h=7.6,pitch=11.8,tip=flat` |
| 3 | B-32a7c82c | grid 11.4 mm (bars 2.3), pins 1.4 x 6.8 mm round every 13.7 mm; seesaw +/-12 deg, 2.5 s + 0.35 mm buzz at 40 Hz | **0.554** | 0.554 | 91% | `breaker:open=11.4,bar=2.3,pin_d=1.4,pin_h=6.8,pitch=8,tip=round` |

## Top 10 (seed 0)

| # | id | design and stroke | robust | mean | free | break | gentle | sort | largest cluster | peak force p90 (mN) | fails |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | B-31c4ea6d | grid 12 mm (bars 1.9), pins 2.8 x 6 mm round every 13.9 mm; seesaw +/-10.5 deg, 3.6 s + 0.3 mm buzz at 40 Hz | 0.700 | 0.759 | 100% | 0.98 | 30% | 90% | 1.0 | 255.07 | 0 |
| 2 | B-87f42099 | grid 8.9 mm (bars 1.2), pins 2 x 7.6 mm flat every 10.1 mm; seesaw +/-8 deg, 3.5 s + 0.35 mm buzz at 40 Hz | 0.683 | 0.756 | 100% | 0.97 | 31% | 90% | 1.0 | 274.79 | 0 |
| 3 | B-164f355a | grid 11.3 mm (bars 1.6), pins 3.1 x 8 mm round every 12.9 mm; seesaw +/-7 deg, 1.1 s + 0.35 mm buzz at 40 Hz | 0.672 | 0.748 | 99% | 0.96 | 27% | 94% | 1.3 | 341.51 | 0 |
| 4 | B-c5be78ea | grid 10.7 mm (bars 1.9), pins 3.6 x 4 mm flat every 12.6 mm; seesaw +/-10 deg, 4.3 s + 0.3 mm buzz at 40 Hz | 0.641 | 0.725 | 98% | 0.92 | 31% | 87% | 1.3 | 231.82 | 0 |
| 5 | B-32a7c82c | grid 11.4 mm (bars 2.3), pins 1.4 x 6.8 mm round every 13.7 mm; seesaw +/-12 deg, 2.5 s + 0.35 mm buzz at 40 Hz | 0.638 | 0.726 | 97% | 0.94 | 29% | 85% | 1.7 | 236.98 | 0 |
| 6 | B-8a2ce165 | grid 10.2 mm (bars 2.1), pins 2.7 x 8.8 mm round every 12.3 mm; seesaw +/-8.5 deg, 1.2 s + 0.35 mm buzz at 40 Hz | 0.619 | 0.729 | 96% | 0.92 | 32% | 87% | 1.7 | 216.99 | 0 |
| 7 | B-515884fb | grid 12 mm (bars 2.2), pins 4 x 6.8 mm round every 14.2 mm; seesaw +/-11 deg, 3.3 s + 0.35 mm buzz at 40 Hz | 0.618 | 0.728 | 98% | 0.92 | 32% | 86% | 1.3 | 244.37 | 0 |
| 8 | B-fb9b5e72 | grid 12 mm (bars 1.6), pins 2.7 x 5 mm flat every 13.6 mm; seesaw +/-6.5 deg, 2.6 s + 0.3 mm buzz at 40 Hz | 0.610 | 0.714 | 95% | 0.91 | 27% | 88% | 1.3 | 256.15 | 0 |
| 9 | B-767be363 | grid 6.6 mm (bars 1.4), pins 3.6 x 5.6 mm round every 8.0 mm; seesaw +/-11.5 deg, 0.4 s + 0.4 mm buzz at 40 Hz | 0.526 | 0.678 | 93% | 0.89 | 30% | 72% | 4.3 | 250.15 | 0 |
| 10 | B-9759b7ac | grid 5.3 mm (bars 2.1), pins 3.8 x 4.8 mm round every 7.4 mm; seesaw +/-6.5 deg, 5.1 s + 0.35 mm buzz at 40 Hz | 0.516 | 0.695 | 87% | 0.84 | 37% | 81% | 7.7 | 160.84 | 0 |

## References

| # | id | design and stroke | robust | mean | free | break | gentle | sort | largest cluster | peak force p90 (mN) | fails |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | B-5405ea9b | NO BREAKER: the clump straight onto the demo rig's 5 mm / 2 mm trays, default seesaw (+/-10 deg, 2 s) | 0.217 | 0.419 | 31% | 0.32 | 76% | 17% | 36.3 | 33.98 | 0 |
| 2 | B-75f277ad | cad/breaker_layer.py default (open 8, pins 2.5 x 12 every 10, round) on the default seesaw | 0.287 | 0.507 | 65% | 0.65 | 46% | 22% | 19.0 | 155.67 | 0 |
| 3 | B-9dcf5153 | the CAD default breaker, default seesaw + 0.3 mm buzz at 40 Hz (1.9 g, the tool's) | 0.479 | 0.672 | 85% | 0.84 | 35% | 75% | 8.7 | 131.46 | 0 |

## Verified on fresh clumps

Each seed packs a different clump. The same 3 bond sets per seed; robust (all seeds) pools seed 0 with the fresh ones.

| id | design and stroke | robust, seed 0 | robust, fresh seeds | robust, all seeds | free, fresh seeds | fails |
|---|---|---|---|---|---|---|
| B-31c4ea6d | grid 12 mm (bars 1.9), pins 2.8 x 6 mm round every 13.9 mm; seesaw +/-10.5 deg, 3.6 s + 0.3 mm buzz at 40 Hz | 0.700 | 0.336 (seeds 1, 2) | **0.422** | 76% | 0 |
| B-87f42099 | grid 8.9 mm (bars 1.2), pins 2 x 7.6 mm flat every 10.1 mm; seesaw +/-8 deg, 3.5 s + 0.35 mm buzz at 40 Hz | 0.683 | 0.575 (seeds 1, 2) | **0.605** | 94% | 0 |
| B-164f355a | grid 11.3 mm (bars 1.6), pins 3.1 x 8 mm round every 12.9 mm; seesaw +/-7 deg, 1.1 s + 0.35 mm buzz at 40 Hz | 0.672 | 0.612 (seeds 1, 2) | **0.630** | 94% | 0 |
| B-c5be78ea | grid 10.7 mm (bars 1.9), pins 3.6 x 4 mm flat every 12.6 mm; seesaw +/-10 deg, 4.3 s + 0.3 mm buzz at 40 Hz | 0.641 | 0.372 (seeds 1, 2) | **0.441** | 81% | 0 |
| B-32a7c82c | grid 11.4 mm (bars 2.3), pins 1.4 x 6.8 mm round every 13.7 mm; seesaw +/-12 deg, 2.5 s + 0.35 mm buzz at 40 Hz | 0.638 | 0.521 (seeds 1, 2) | **0.554** | 91% | 0 |
| B-8a2ce165 | grid 10.2 mm (bars 2.1), pins 2.7 x 8.8 mm round every 12.3 mm; seesaw +/-8.5 deg, 1.2 s + 0.35 mm buzz at 40 Hz | 0.619 | 0.494 (seeds 1, 2) | **0.530** | 89% | 0 |
| B-5405ea9b | NO BREAKER: the clump straight onto the demo rig's 5 mm / 2 mm trays, default seesaw (+/-10 deg, 2 s) | 0.217 | 0.235 (seeds 1, 2) | **0.229** | 48% | 0 |
| B-75f277ad | cad/breaker_layer.py default (open 8, pins 2.5 x 12 every 10, round) on the default seesaw | 0.287 | 0.188 (seeds 1, 2) | **0.216** | 34% | 0 |
| B-9dcf5153 | the CAD default breaker, default seesaw + 0.3 mm buzz at 40 Hz (1.9 g, the tool's) | 0.479 | 0.440 (seeds 1, 2) | **0.452** | 84% | 0 |

## Per bond set, top 3 and the no-breaker reference

**B-31c4ea6d**: grid 12 mm (bars 1.9), pins 2.8 x 6 mm round every 13.9 mm; seesaw +/-10.5 deg, 3.6 s + 0.3 mm buzz at 40 Hz

| bond | score | free | t50 (s) | t90 (s) | largest | over 5 mN | in the clump over 5 mN | sort | lost | debris |
|---|---|---|---|---|---|---|---|---|---|---|
| weak | 0.824 | 100% | 0.02 | 0.05 | 1 | 100% | 19% | 91% | 2 | leaf: on_5mm 1; twig: on_5mm 2; dirt: catch 4, lost 2 |
| medium | 0.771 | 100% | 0.05 | 0.25 | 1 | 100% | 50% | 91% | 0 | leaf: on_breaker 1; twig: on_breaker 1, on_5mm 1; dirt: catch 6 |
| strong | 0.682 | 100% | 0.70 | 0.70 | 1 | 100% | 94% | 87% | 2 | leaf: on_breaker 1; twig: on_breaker 1, on_5mm 1; dirt: catch 3, lost 2, on_5mm 1 |

**B-87f42099**: grid 8.9 mm (bars 1.2), pins 2 x 7.6 mm flat every 10.1 mm; seesaw +/-8 deg, 3.5 s + 0.35 mm buzz at 40 Hz

| bond | score | free | t50 (s) | t90 (s) | largest | over 5 mN | in the clump over 5 mN | sort | lost | debris |
|---|---|---|---|---|---|---|---|---|---|---|
| weak | 0.831 | 100% | 0.02 | 0.05 | 1 | 100% | 13% | 89% | 1 | leaf: on_breaker 1; twig: on_breaker 1, on_5mm 1; dirt: catch 5, on_5mm 1 |
| medium | 0.779 | 100% | 0.06 | 0.12 | 1 | 100% | 46% | 93% | 0 | leaf: on_breaker 1; twig: on_breaker 1, on_5mm 1; dirt: catch 6 |
| strong | 0.657 | 100% | 0.44 | 1.39 | 1 | 100% | 96% | 89% | 1 | leaf: on_breaker 1; twig: on_5mm 2; dirt: catch 6 |

**B-164f355a**: grid 11.3 mm (bars 1.6), pins 3.1 x 8 mm round every 12.9 mm; seesaw +/-7 deg, 1.1 s + 0.35 mm buzz at 40 Hz

| bond | score | free | t50 (s) | t90 (s) | largest | over 5 mN | in the clump over 5 mN | sort | lost | debris |
|---|---|---|---|---|---|---|---|---|---|---|
| weak | 0.846 | 100% | 0.03 | 0.06 | 1 | 100% | 11% | 96% | 2 | leaf: on_5mm 1; twig: on_breaker 1, on_2mm 1; dirt: catch 5, lost 1 |
| medium | 0.736 | 100% | 0.06 | 0.22 | 1 | 100% | 65% | 94% | 1 | leaf: on_5mm 1; twig: on_breaker 1, on_2mm 1; dirt: catch 6 |
| strong | 0.661 | 96% | 0.20 | 1.27 | 2 | 100% | 93% | 93% | 1 | leaf: on_5mm 1; twig: on_breaker 2; dirt: catch 6 |

**B-5405ea9b**: no breaker; seesaw +/-10 deg, 2 s

| bond | score | free | t50 (s) | t90 (s) | largest | over 5 mN | in the clump over 5 mN | sort | lost | debris |
|---|---|---|---|---|---|---|---|---|---|---|
| weak | 0.704 | 93% | 0.04 | 0.19 | 2 | 94% | 28% | 35% | 0 | leaf: on_5mm 1; twig: on_5mm 1, on_2mm 1; dirt: catch 6 |
| medium | 0.258 | 2% | - | - | 53 | 20% | 19% | 7% | 0 | leaf: on_5mm 1; twig: on_5mm 1, on_2mm 1; dirt: on_5mm 6 |
| strong | 0.295 | 0% | - | - | 54 | 11% | 11% | 7% | 0 | leaf: on_5mm 1; twig: on_5mm 2; dirt: on_5mm 6 |

## Why the losers lost

- free at the end: top half 0.93, bottom half 0.76
- gentleness: top half 0.32, bottom half 0.36
- in the ideal zone: top half 0.83, bottom half 0.52
- largest cluster left: top half 4.02, bottom half 12.81
- peak force p90, mN: top half 228.96, bottom half 150.38
- rank correlation with the robust score (+ helps): vib_mm +0.50, open +0.43, bar +0.37, pin_h -0.33, pin_d +0.27, tip=round +0.25
