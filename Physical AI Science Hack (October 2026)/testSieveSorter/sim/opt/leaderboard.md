# Leaderboard: Demo set: surrogate grains (pasta + chickpea / rice / quinoa)

Generated 2026-10-25 10:58 by `sim/optimize.py` (study `demo`). 329 candidates, 4365 sim runs so far.

**The sim ranks designs; it does not predict real percentages.** It is uncalibrated until `calibrate.py` has bench counts, has no water, rigid particles, and about 80 particles per run. Sizes are simulated at the as-printed opening, nominal - 0.15 mm (ASSUMED until the hole gauge is measured).

Ranked by the robust score (mean - 1 sd) over 3 friction sets x 3 seeds at the full 30 s run. Score per run = min over classes of min(purity, recovery), minus 0.5 x jammed share, 1.0 x lost share and 0.05 x t90/duration. Failed (unstable) runs score -1. Only candidates promoted to the full run are ranked; screened-only ones are in the log. Solver: dt 0.25 ms, contact timeconst 0.5 ms (stiffer than sorter.py's default; see optimize.py). Friction sets: mu 0.3, mu 0.4, mu 0.5.

| # | id | family | robust | mean +/- sd | worst mu set | big (pasta, chickpea) pur / rec | rice pur / rec | quinoa pur / rec | jammed | lost | t90 s | flags | design (CAD, nominal mm) | sim spec (as printed) | stroke |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | P-b192da7c | plinko | **1.000** | 1.000 +/- 0.000 | 1.000 | 100% / 100% | 100% / 100% | 100% / 100% | 0.0 | 0.0 | 0.2 (9/9) | ok | rods L1 gap 4.7 (rod 2.6 wide, 2.2 tall) / L2 gap 1.6 (rod 2.3, 3.2) | `plinko` | tool sine 37 Hz, 2.1 g (0.38 mm), 25 deg up |
| 2 | P-e6f1f8db | plinko | **0.999** | 1.000 +/- 0.000 | 0.999 | 100% / 100% | 100% / 100% | 100% / 100% | 0.0 | 0.0 | 0.3 (9/9) | PEN 2/9 (clr 0.26, pen 0.150) | rods L1 gap 4.3 (rod 1.8 wide, 1.8 tall) / L2 gap 1.5 (rod 2.6, 3.2) | `plinko` | tool sine 35 Hz, 2.0 g (0.41 mm), 35 deg up |
| 3 | P-ae394887 | plinko | **0.999** | 0.999 +/- 0.000 | 0.999 | 100% / 100% | 100% / 100% | 100% / 100% | 0.0 | 0.0 | 0.4 (9/9) | PEN 1/9 (clr 0.26, pen 0.153) | rods L1 gap 3.7 (rod 2.6 wide, 1.6 tall) / L2 gap 1.5 (rod 1.8, 2.4) | `plinko` | tool sine 48 Hz, 2.2 g (0.24 mm), 20 deg up |
| 4 | P-7dd9222c | plinko | **0.999** | 0.999 +/- 0.000 | 0.999 | 100% / 100% | 100% / 100% | 100% / 100% | 0.0 | 0.0 | 0.4 (9/9) | PEN 5/9 (clr 0.24, pen 0.218) | rods L1 gap 3.6 (rod 2.1 wide, 1.8 tall) / L2 gap 1.6 (rod 2, 2.8) | `plinko` | tool sine 20 Hz, 2.1 g (1.30 mm), along the tray |
| 5 | P-cbc9ed5d | plinko | **0.999** | 0.999 +/- 0.000 | 0.999 | 100% / 100% | 100% / 100% | 100% / 100% | 0.0 | 0.0 | 0.5 (9/9) | PEN 4/9 (clr 0.24, pen 0.167) | rods L1 gap 3.3 (rod 2.7 wide, 1.8 tall) / L2 gap 1.6 (rod 2.4, 3) | `plinko` | tool sine 15 Hz, 1.8 g (1.99 mm), 5 deg up |
| 6 | P-668db784 | plinko | **0.998** | 0.998 +/- 0.000 | 0.998 | 100% / 100% | 100% / 100% | 100% / 100% | 0.0 | 0.0 | 0.9 (9/9) | PEN 3/9 (clr 0.24, pen 0.205) | rods L1 gap 3.5 (rod 3.7 wide, 2 tall) / L2 gap 1.6 (rod 2.9, 2.2) | `plinko` | tool sine 14 Hz, 2.0 g (2.54 mm), along the tray |
| 7 | G-a1ecf9bb | gated_mid | **0.985** | 0.988 +/- 0.003 | 0.987 | 100% / 100% | 100% / 100% | 100% / 100% | 0.0 | 0.0 | 7.1 (9/9) | ok | L1 t3.5 / L2 t1.6; slope 2.7 deg, tunnel width 5, tooth 0.8, L1 gate at x 22.2 with slot 8.1, L2 at x 53, unflipped | `gated:2.7,t3p35,t1p45,tw=4.85,tooth=0.95,slot=8.1/7,gx=22.2/53,flip=0` | tool sine 48 Hz, 3.7 g (0.40 mm), 30 deg up |
| 8 | P-6e03ce14 | plinko | **0.958** | 0.980 +/- 0.022 | 0.975 | 99% / 100% | 99% / 100% | 100% / 99% | 0.0 | 0.0 | 1.6 (9/9) | ok | rods L1 gap 4.1 (rod 1.7 wide, 2.2 tall) / L2 gap 1.6 (rod 2.1, 3.2) | `plinko` | firmware 9 mm at 50 mm/s, 25 deg up |
| 9 | G-060cecb0 | gated_mid | **0.955** | 0.972 +/- 0.017 | 0.965 | 100% / 100% | 100% / 99% | 99% / 100% | 0.0 | 0.0 | 7.8 (9/9) | PEN 9/9 (clr 0.04, pen 0.130) | L1 w3.1x3.1 / L2 t1.8; slope 0.3 deg, tunnel width 8.3, tooth 1.1, L1 gate at x 31.8 with slot 7.4, L2 at x 53, unflipped | `gated:0.3,w2p95x2p95,t1p65,tw=8.15,tooth=1.25,slot=7.4/7,gx=31.8/53,flip=0` | tool sine 28 Hz, 4.3 g (1.36 mm), 10 deg up |
| 10 | G-e5083752 | gated | **0.950** | 0.972 +/- 0.022 | 0.964 | 99% / 100% | 100% / 100% | 100% / 99% | 0.0 | 0.0 | 10.4 (9/9) | ok | L1 t5.3 / L2 t1.6; slope 3.1 deg, tunnel width 8.3, tooth 1.7, slot 7.2 | `gated:3.1,t5p15,t1p45,tw=8.15,tooth=1.85,slot=7.2` | tool sine 38 Hz, 4.8 g (0.83 mm), along the tray |

## Best of each family (style)

| # | id | family | robust | mean +/- sd | worst mu set | big (pasta, chickpea) pur / rec | rice pur / rec | quinoa pur / rec | jammed | lost | t90 s | flags | design (CAD, nominal mm) | sim spec (as printed) | stroke |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 10 | G-e5083752 | gated | **0.950** | 0.972 +/- 0.022 | 0.964 | 99% / 100% | 100% / 100% | 100% / 99% | 0.0 | 0.0 | 10.4 (9/9) | ok | L1 t5.3 / L2 t1.6; slope 3.1 deg, tunnel width 8.3, tooth 1.7, slot 7.2 | `gated:3.1,t5p15,t1p45,tw=8.15,tooth=1.85,slot=7.2` | tool sine 38 Hz, 4.8 g (0.83 mm), along the tray |
| 7 | G-a1ecf9bb | gated_mid | **0.985** | 0.988 +/- 0.003 | 0.987 | 100% / 100% | 100% / 100% | 100% / 100% | 0.0 | 0.0 | 7.1 (9/9) | ok | L1 t3.5 / L2 t1.6; slope 2.7 deg, tunnel width 5, tooth 0.8, L1 gate at x 22.2 with slot 8.1, L2 at x 53, unflipped | `gated:2.7,t3p35,t1p45,tw=4.85,tooth=0.95,slot=8.1/7,gx=22.2/53,flip=0` | tool sine 48 Hz, 3.7 g (0.40 mm), 30 deg up |
| 1 | P-b192da7c | plinko | **1.000** | 1.000 +/- 0.000 | 1.000 | 100% / 100% | 100% / 100% | 100% / 100% | 0.0 | 0.0 | 0.2 (9/9) | ok | rods L1 gap 4.7 (rod 2.6 wide, 2.2 tall) / L2 gap 1.6 (rod 2.3, 3.2) | `plinko` | tool sine 37 Hz, 2.1 g (0.38 mm), 25 deg up |
| 29 | I-f660966d | inserts | **0.714** | 0.824 +/- 0.110 | 0.729 | 89% / 100% | 98% / 88% | 89% / 92% | 0.0 | 0.0 | 7.7 (6/9) | PEN 9/9 (clr 0.01, pen 0.178) | square holes 5 (bar 1.2) / 2 (bar 1) | `inserts:h4p85b1p35,h1p85b1p15` | firmware 10 mm at 50 mm/s, along the tray |
| 42 | C-243bf513 | current | **0.523** | 0.608 +/- 0.085 | 0.575 | 100% / 100% | 100% / 67% | 78% / 94% | 3.2 | 0.0 | 5.0 (1/9) | PEN 6/9 (clr 0.12, pen 0.153) | TODAY on the bench: glued mesh inserts mesh5 / mesh2, firmware cap stroke | `inserts:mesh5,mesh2` | firmware 10 mm at 50 mm/s, along the tray |
| 45 | D-e018f15d | demo_rig | **0.499** | 0.499 +/- 0.000 | 0.499 | 100% / 100% | 50% / 100% | 50% / 100% | 0.0 | 0.0 | 0.6 (9/9) | ok | one level of the demo rig: the 5 mm tray alone over a catch pan, up and down (sine 20 Hz, 2 g, 90 deg). The full rig is the stacked baseline above | `inserts:5mm` | tool sine 20 Hz, 2.0 g (1.24 mm), 90 deg up |

## References (fixed, not tuned)

| id | what | robust | mean +/- sd | worst mu set | big (pasta, chickpea) pur / rec | rice pur / rec | quinoa pur / rec | jammed | lost | t90 s | flags | spec |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| G-c0121ff0 | README final design: gated, 2 deg, existing strips w5.0 / t1.4, firmware cap stroke | -0.074 | -0.035 +/- 0.039 | -0.059 | 29% / 100% | 66% / 39% | 44% / 3% | 2.8 | 0.0 | - (0/9) | ok | `gated:2,w4p85x7p85,t1p25,tw=7.85,tooth=2.15,slot=7` |
| G-e1861ffb | gatecalc plan (skill): gated, t3.8 / t1.6 nominal (its t1.55 on the 0.1 mm grid), firmware cap | -0.024 | 0.051 +/- 0.074 | -0.019 | 31% / 100% | 79% / 51% | 89% / 11% | 1.0 | 0.0 | - (0/9) | ok | `gated:2,t3p65,t1p45,tw=7.85,tooth=2.15,slot=7` |
| P-99a23702 | plinko_layers.py as in the repo: rods 5.0 / 1.4, firmware cap stroke | 0.670 | 0.810 +/- 0.141 | 0.721 | 100% / 100% | 86% / 100% | 100% / 83% | 0.0 | 0.0 | 6.2 (7/9) | PEN 2/9 (clr 0.16, pen 0.093) | `plinko` |
| I-f660966d | printed inserts as in the repo: 5 mm / 2 mm square holes, firmware cap stroke | 0.714 | 0.824 +/- 0.110 | 0.729 | 89% / 100% | 98% / 88% | 89% / 92% | 0.0 | 0.0 | 7.7 (6/9) | PEN 9/9 (clr 0.01, pen 0.178) | `inserts:h4p85b1p35,h1p85b1p15` |
| C-243bf513 | TODAY on the bench: glued mesh inserts mesh5 / mesh2, firmware cap stroke | 0.523 | 0.608 +/- 0.085 | 0.575 | 100% / 100% | 100% / 67% | 78% / 94% | 3.2 | 0.0 | 5.0 (1/9) | PEN 6/9 (clr 0.12, pen 0.153) | `inserts:mesh5,mesh2` |
| D-e018f15d | one level of the demo rig: the 5 mm tray alone over a catch pan, up and down (sine 20 Hz, 2 g, 90 deg). The full rig is the stacked baseline above | 0.499 | 0.499 +/- 0.000 | 0.499 | 100% / 100% | 50% / 100% | 50% / 100% | 0.0 | 0.0 | 0.6 (9/9) | ok | `inserts:5mm` |
| I-8145d10d | DEMO RIG the team built: stacked printed 5 mm / 2 mm trays (inserts:5mm,2mm), shaken up and down (sine 20 Hz, 2 g, 90 deg; assumed tool motion, sim/VERTICAL.md) | 0.460 | 0.562 +/- 0.103 | 0.550 | 100% / 100% | 100% / 61% | 72% / 100% | 0.0 | 0.0 | 2.7 (1/9) | BEYOND 2 (particles past an opening they can't fit); PEN 9/9 (clr 0.01, pen 0.181) | `inserts:h4p85b1p35,h1p85b1p15` |
| G-02f5688b | README final design: gated, 2 deg, existing strips w5.0 / t1.4, firmware cap stroke | -0.061 | -0.048 +/- 0.013 | -0.057 | 25% / 100% | 85% / 33% | 11% / 0% | 0.3 | 0.0 | - (0/9) | PEN 1/9 (clr 0.16, pen 0.099) | `gated:2,w4p85x7p85,t1p25,tw=7.85,tooth=2.15,slot=7` |
| G-1ef5b30a | gatecalc plan (skill): gated, t3.8 / t1.6 nominal (its t1.55 on the 0.1 mm grid), firmware cap | -0.050 | -0.050 +/- 0.000 | -0.050 | 26% / 100% | 79% / 39% | 0% / 0% | 0.0 | 0.0 | - (0/9) | ok | `gated:2,t3p65,t1p45,tw=7.85,tooth=2.15,slot=7` |
| P-b5751e2d | plinko_layers.py as in the repo: rods 5.0 / 1.4, firmware cap stroke | 0.408 | 0.542 +/- 0.134 | 0.506 | 86% / 100% | 75% / 97% | 100% / 59% | 0.0 | 0.0 | - (0/9) | PEN 1/9 (clr 0.16, pen 0.093) | `plinko` |
| I-d26e2901 | printed inserts as in the repo: 5 mm / 2 mm square holes, firmware cap stroke | 0.359 | 0.424 +/- 0.065 | 0.389 | 52% / 100% | 80% / 75% | 84% / 48% | 0.0 | 0.0 | - (0/9) | PEN 9/9 (clr 0.01, pen 0.172) | `inserts:h4p85b1p35,h1p85b1p15` |
| I-d26e2901 | DEMO RIG the team built: stacked printed 5 mm / 2 mm trays (inserts:5mm,2mm), shaken up and down (sine 20 Hz, 2 g, 90 deg; assumed tool motion, sim/VERTICAL.md) | 0.359 | 0.424 +/- 0.065 | 0.389 | 52% / 100% | 80% / 75% | 84% / 48% | 0.0 | 0.0 | - (0/9) | PEN 9/9 (clr 0.01, pen 0.172) | `inserts:h4p85b1p35,h1p85b1p15` |
| C-1f16dae6 | TODAY on the bench: glued mesh inserts mesh5 / mesh2, seesaw (default 10 deg, 1.6 s, long axis) | 0.480 | 0.556 +/- 0.077 | 0.544 | 100% / 100% | 100% / 65% | 79% / 89% | 6.3 | 0.0 | - (0/9) | PEN 3/9 (clr 0.12, pen 0.122) | `inserts:mesh5,mesh2` |
| D-ef26c8c7 | one level of the demo rig: the 5 mm tray alone over a catch pan, seesaw (default 10 deg, 1.6 s, long axis) | 0.387 | 0.410 +/- 0.023 | 0.396 | 53% / 100% | 54% / 83% | 46% / 70% | 0.0 | 0.0 | - (0/9) | ok | `inserts:5mm` |

## Stress test: the leaders under the two biggest unknowns

**Stroke reversal.** The firmware reverses at constant speed with no ramp; how sharp the real reversal is depends on the stage and is unmeasured (sweep.py FIRMWARE assumes 0.01 s). Transport depends on it. **Print size.** Openings are simulated at nominal - 0.15 mm (assumed); a printer that makes them 0.1 mm tighter or looser shifts every cut. Each column reruns the design with one of these changed (full length, same 3 friction sets x 3 seeds; robust score). A design whose score holds across columns is safer to print.

| id | family | as ranked (ramp 0.01 s, undersize 0.15 mm) | ramp 0.005 s | ramp 0.02 s | undersize 0.05 mm | undersize 0.25 mm | worst | design |
|---|---|---|---|---|---|---|---|---|
| P-b192da7c | plinko | 1.000 | - | - | 0.937 | 0.999 | **0.937** | rods L1 gap 4.7 (rod 2.6 wide, 2.2 tall) / L2 gap 1.6 (rod 2.3, 3.2) |
| P-e6f1f8db | plinko | 0.999 | - | - | 1.000 | 0.999 | **0.999** | rods L1 gap 4.3 (rod 1.8 wide, 1.8 tall) / L2 gap 1.5 (rod 2.6, 3.2) |
| P-ae394887 | plinko | 0.999 | - | - | 0.978 | 0.997 | **0.978** | rods L1 gap 3.7 (rod 2.6 wide, 1.6 tall) / L2 gap 1.5 (rod 1.8, 2.4) |
| P-7dd9222c | plinko | 0.999 | - | - | 0.937 | 0.999 | **0.937** | rods L1 gap 3.6 (rod 2.1 wide, 1.8 tall) / L2 gap 1.6 (rod 2, 2.8) |
| P-cbc9ed5d | plinko | 0.999 | - | - | 0.937 | 0.998 | **0.937** | rods L1 gap 3.3 (rod 2.7 wide, 1.8 tall) / L2 gap 1.6 (rod 2.4, 3) |
| P-668db784 | plinko | 0.998 | - | - | 0.937 | 0.997 | **0.937** | rods L1 gap 3.5 (rod 3.7 wide, 2 tall) / L2 gap 1.6 (rod 2.9, 2.2) |
| G-a1ecf9bb | gated_mid | 0.985 | - | - | 0.925 | 0.965 | **0.925** | L1 t3.5 / L2 t1.6; slope 2.7 deg, tunnel width 5, tooth 0.8, L1 gate at x 22.2 with slot 8.1, L2 at x 53, unflipped |
| P-6e03ce14 | plinko | 0.958 | 0.983 | 0.826 | 0.937 | 0.936 | **0.826** | rods L1 gap 4.1 (rod 1.7 wide, 2.2 tall) / L2 gap 1.6 (rod 2.1, 3.2) |
| G-060cecb0 | gated_mid | 0.955 | - | - | 0.760 | 0.954 | **0.760** | L1 w3.1x3.1 / L2 t1.8; slope 0.3 deg, tunnel width 8.3, tooth 1.1, L1 gate at x 31.8 with slot 7.4, L2 at x 53, unflipped |
| G-e5083752 | gated | 0.950 | - | - | 0.947 | 0.893 | **0.893** | L1 t5.3 / L2 t1.6; slope 3.1 deg, tunnel width 8.3, tooth 1.7, slot 7.2 |
| G-d726c2e8 | gated | 0.946 | - | - | 0.839 | 0.956 | **0.839** | L1 t4.4 / L2 t1.8; slope 2.4 deg, tunnel width 8, tooth 1.1, slot 6 |
| P-fdf86953 | plinko | 0.937 | - | - | 0.650 | 0.977 | **0.650** | rods L1 gap 5.1 (rod 2.4 wide, 3.4 tall) / L2 gap 1.7 (rod 2.3, 3.2) |
| P-547508e5 | plinko | 0.937 | - | - | 0.630 | 0.964 | **0.630** | rods L1 gap 3.1 (rod 2.8 wide, 1.8 tall) / L2 gap 1.7 (rod 2.3, 1.8) |
| P-ba5dd6b3 | plinko | 0.929 | 0.971 | 0.892 | 0.930 | 0.870 | **0.870** | rods L1 gap 5.6 (rod 1.8 wide, 2.6 tall) / L2 gap 1.6 (rod 2.2, 2.8) |
| P-0fb6775d | plinko | 0.929 | 0.953 | 0.813 | 0.922 | 0.875 | **0.813** | rods L1 gap 4 (rod 2.8 wide, 1.6 tall) / L2 gap 1.6 (rod 2.7, 2.8) |
| P-cbe7dbec | plinko | 0.891 | 0.938 | 0.681 | 0.654 | 0.852 | **0.654** | rods L1 gap 5.1 (rod 1.4 wide, 1.6 tall) / L2 gap 1.7 (rod 1.9, 3.2) |
| I-f660966d | inserts | 0.714 | 0.729 | 0.655 | 0.599 | 0.710 | **0.599** | square holes 5 (bar 1.2) / 2 (bar 1) |
| P-99a23702 | plinko | 0.670 | 0.934 | 0.530 | 0.799 | 0.485 | **0.485** | rods L1 gap 5 (rod 2.4 wide, 3 tall) / L2 gap 1.4 (rod 2, 2.6) |
| C-243bf513 | current | 0.523 | 0.518 | 0.522 | 0.523 | 0.523 | **0.518** | TODAY on the bench: glued mesh inserts mesh5 / mesh2, firmware cap stroke |
| D-e018f15d | demo_rig | 0.499 | - | - | 0.499 | 0.499 | **0.499** | one level of the demo rig: the 5 mm tray alone over a catch pan, up and down (sine 20 Hz, 2 g, 90 deg). The full rig is the stacked baseline above |
| I-8145d10d | inserts | 0.460 | - | - | -0.000 | 0.810 | **-0.000** | square holes 5 (bar 1.2) / 2 (bar 1) |
| G-e1861ffb | gated | -0.024 | -0.062 | -0.073 | -0.028 | -0.065 | **-0.073** | L1 t3.8 / L2 t1.6; slope 2 deg, tunnel width 8, tooth 2, slot 7 |
| G-c0121ff0 | gated | -0.074 | -0.067 | -0.074 | -0.055 | -0.078 | **-0.078** | L1 w5x8 / L2 t1.4; slope 2 deg, tunnel width 8, tooth 2, slot 7 |

## Verification of flagged leaders at stiffer contacts

Rerun at dt 0.125 ms and contact timeconst 0.25 ms (half the overlap of the standard solver), same 3 friction sets x 3 seeds, 30 s. A design that comes back with no flagged or failed run counts as clean for `winners.json`, ranked by the lower of its two scores.

| id | family | robust (standard) | flags (standard) | robust (stiff) | flags (stiff) | verdict | design |
|---|---|---|---|---|---|---|---|
| P-e6f1f8db | plinko | 0.999 | PEN 2/9 (clr 0.26, pen 0.150) | 0.999 | PEN 1/9 (clr 0.26, pen 0.169) | still flagged | rods L1 gap 4.3 (rod 1.8 wide, 1.8 tall) / L2 gap 1.5 (rod 2.6, 3.2) |
| P-ae394887 | plinko | 0.999 | PEN 1/9 (clr 0.26, pen 0.153) | 0.999 | ok | clean | rods L1 gap 3.7 (rod 2.6 wide, 1.6 tall) / L2 gap 1.5 (rod 1.8, 2.4) |
| P-7dd9222c | plinko | 0.999 | PEN 5/9 (clr 0.24, pen 0.218) | 0.999 | PEN 5/9 (clr 0.24, pen 0.306) | still flagged | rods L1 gap 3.6 (rod 2.1 wide, 1.8 tall) / L2 gap 1.6 (rod 2, 2.8) |
| P-cbc9ed5d | plinko | 0.999 | PEN 4/9 (clr 0.24, pen 0.167) | 0.999 | PEN 2/9 (clr 0.24, pen 0.136) | still flagged | rods L1 gap 3.3 (rod 2.7 wide, 1.8 tall) / L2 gap 1.6 (rod 2.4, 3) |
| P-668db784 | plinko | 0.998 | PEN 3/9 (clr 0.24, pen 0.205) | 0.998 | PEN 1/9 (clr 0.24, pen 0.125) | still flagged | rods L1 gap 3.5 (rod 3.7 wide, 2 tall) / L2 gap 1.6 (rod 2.9, 2.2) |
| G-060cecb0 | gated_mid | 0.955 | PEN 9/9 (clr 0.04, pen 0.130) | 0.934 | PEN 9/9 (clr 0.04, pen 0.083) | still flagged | L1 w3.1x3.1 / L2 t1.8; slope 0.3 deg, tunnel width 8.3, tooth 1.1, L1 gate at x 31.8 with slot 7.4, L2 at x 53, unflipped |
| G-d726c2e8 | gated | 0.946 | PEN 9/9 (clr 0.04, pen 0.110) | 0.937 | PEN 7/9 (clr 0.04, pen 0.059) | still flagged | L1 t4.4 / L2 t1.8; slope 2.4 deg, tunnel width 8, tooth 1.1, slot 6 |
| P-547508e5 | plinko | 0.937 | PEN 1/9 (clr 0.14, pen 0.098) | 0.937 | ok | clean | rods L1 gap 3.1 (rod 2.8 wide, 1.8 tall) / L2 gap 1.7 (rod 2.3, 1.8) |

## Best per drive

BioKEA's stage can only run the firmware stroke (constant speed); the demo rig is a vibrating tool (sine). Best full-run design for each, whether or not it is flagged:

| drive | id | family | robust | flags | design (CAD, nominal mm) | stroke |
|---|---|---|---|---|---|---|
| seesaw (the rig's current rocking motor; ends tip, axis y) | P-fccdb05e | plinko | 0.705 | PEN 2/9 (clr 0.14, pen 0.101) | rods L1 gap 3.3 (rod 2 wide, 3.8 tall) / L2 gap 1.7 (rod 2.8, 2.8) | seesaw +/-14.5 deg about the tray's short axis, 0.9 s per cycle |
| firmware (BioKEA's stage) | P-6e03ce14 | plinko | 0.958 | ok | rods L1 gap 4.1 (rod 1.7 wide, 2.2 tall) / L2 gap 1.6 (rod 2.1, 3.2) | firmware 9 mm at 50 mm/s, 25 deg up |
| vibrating tool (demo rig) | P-b192da7c | plinko | 1.000 | ok | rods L1 gap 4.7 (rod 2.6 wide, 2.2 tall) / L2 gap 1.6 (rod 2.3, 3.2) | tool sine 37 Hz, 2.1 g (0.38 mm), 25 deg up |

## Count matrices of the top 3 (summed over the 9 full runs)

**1. P-b192da7c (plinko) rods L1 gap 4.7 (rod 2.6 wide, 2.2 tall) / L2 gap 1.6 (rod 2.3, 3.2); sim `plinko`**

| class \ ended in | layer_1_rods | layer_2_rods | layer_3_catch | between | lost |
|---|---|---|---|---|---|
| big (pasta, chickpea) | 144 | 0 | 0 | 0 | 0 |
| rice | 0 | 270 | 0 | 0 | 0 |
| quinoa | 0 | 0 | 270 | 0 | 0 |

**2. P-e6f1f8db (plinko) rods L1 gap 4.3 (rod 1.8 wide, 1.8 tall) / L2 gap 1.5 (rod 2.6, 3.2); sim `plinko`**

| class \ ended in | layer_1_rods | layer_2_rods | layer_3_catch | between | lost |
|---|---|---|---|---|---|
| big (pasta, chickpea) | 144 | 0 | 0 | 0 | 0 |
| rice | 0 | 270 | 0 | 0 | 0 |
| quinoa | 0 | 0 | 270 | 0 | 0 |

**3. P-ae394887 (plinko) rods L1 gap 3.7 (rod 2.6 wide, 1.6 tall) / L2 gap 1.5 (rod 1.8, 2.4); sim `plinko`**

| class \ ended in | layer_1_rods | layer_2_rods | layer_3_catch | between | lost |
|---|---|---|---|---|---|
| big (pasta, chickpea) | 144 | 0 | 0 | 0 | 0 |
| rice | 0 | 270 | 0 | 0 | 0 |
| quinoa | 0 | 0 | 270 | 0 | 0 |


Columns: purity = share of a bin's contents that belong to its class; recovery = share of a class that ends in its bin; jammed = particles per run stuck between bins (in a strip, slot or on a ledge); lost = out of the machine; t90 = seconds until 90% of the sample sits in its target bin (n/9 = runs that got there). Flags: FAIL = runs that went unstable or errored; PEN = particle-vs-gate overlap at or over 0.5 x the tightest gate clearance (near-size results untrustworthy); BEYOND = particles that ended past an opening their own size can't pass (soft contacts squeezed them through; should be 0, and is shown whenever it isn't).
