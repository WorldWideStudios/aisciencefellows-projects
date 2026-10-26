# Leaderboard: EXPLORATORY: generated insects in BugPicker's body-length classes

Generated 2026-10-25 07:59 by `sim/optimize.py` (study `insects`). 33 candidates, 396 sim runs so far.

**EXPLORATORY.** No real specimen has been measured: the insects are generated from textbook sizes (`sim/insects.py`), and the classes use body length, which no gate cuts directly.

**The sim ranks designs; it does not predict real percentages.** It is uncalibrated until `calibrate.py` has bench counts, has no water, rigid particles, and about 80 particles per run. Sizes are simulated at the as-printed opening, nominal - 0.15 mm (ASSUMED until the hole gauge is measured).

Ranked by the robust score (mean - 1 sd) over 3 friction sets x 3 seeds at the full 30 s run. Score per run = min over classes of min(purity, recovery), minus 0.5 x jammed share, 1.0 x lost share and 0.05 x t90/duration. Failed (unstable) runs score -1. Only candidates promoted to the full run are ranked; screened-only ones are in the log. Solver: dt 0.25 ms, contact timeconst 0.5 ms (stiffer than sorter.py's default; see optimize.py). Friction sets: mu 0.3, mu 0.4, mu 0.5.

| # | id | family | robust | mean +/- sd | worst mu set | > 6 mm pur / rec | 2-6 mm pur / rec | < 2 mm pur / rec | jammed | lost | t90 s | flags | design (CAD, nominal mm) | sim spec (as printed) | stroke |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | P-8d6849ce | plinko | **0.351** | 0.470 +/- 0.119 | 0.397 | 74% / 57% | 89% / 78% | 78% / 92% | 2.1 | 0.0 | 4.7 (9/9) | PEN 9/9 (clr 0.05, pen 0.706) | rods L1 gap 3.1 (rod 2.4 wide, 2.4 tall) / L2 gap 1.3 (rod 2.6, 3.4) | `plinko` | tool sine 32 Hz, 4.0 g (0.97 mm), 75 deg up |
| 2 | P-2ee377b0 | plinko | **0.267** | 0.398 +/- 0.132 | 0.390 | 50% / 66% | 82% / 67% | 80% / 67% | 8.1 | 0.0 | 2.6 (9/9) | PEN 2/9 (clr 0.16, pen 0.148) | rods L1 gap 4.2 (rod 2.4 wide, 3 tall) / L2 gap 1.4 (rod 2, 2.6) | `plinko` | firmware 10 mm at 50 mm/s, along the tray |
| 3 | P-2a281144 | plinko | **0.243** | 0.329 +/- 0.086 | 0.314 | 36% / 91% | 73% / 63% | 100% / 57% | 2.8 | 0.0 | 5.8 (9/9) | PEN 9/9 (clr 0.05, pen 0.579) | rods L1 gap 1.8 (rod 2.8 wide, 3.2 tall) / L2 gap 0.9 (rod 2.9, 2.2) | `plinko` | tool sine 35 Hz, 3.8 g (0.77 mm), 80 deg up |
| 4 | G-c46df8f7 | gated_mid | **0.226** | 0.351 +/- 0.125 | 0.334 | 37% / 92% | 88% / 64% | 92% / 85% | 0.4 | 0.0 | 10.9 (9/9) | BEYOND 1 (particles past an opening they can't fit); PEN 9/9 (clr 0.26, pen 0.894) | L1 w3.5x6.5 / L2 t1.5; slope 1.8 deg, tunnel width 6.9, tooth 2, L1 gate at x 22.5 with slot 13.4, L2 at x 53, unflipped | `gated:1.8,w3p35x6p35,t1p35,tw=6.75,tooth=2.15,slot=13.4/7,gx=22.5/53,flip=0` | tool sine 13 Hz, 4.1 g (6.03 mm), 10 deg up |
| 5 | G-917aa1ea | gated_mid | **0.200** | 0.289 +/- 0.089 | 0.286 | 32% / 99% | 81% / 54% | 99% / 74% | 1.6 | 0.0 | 9.4 (9/9) | PEN 9/9 (clr 0.05, pen 0.444) | L1 t2.6 / L2 w1.3x7.7; slope 1.7 deg, tunnel width 4.1, tooth 2.8, L1 gate at x 23.9 with slot 9.9, L2 at x 53, unflipped | `gated:1.7,t2p45,w1p15x7p55,tw=3.95,tooth=2.95,slot=9.9/7,gx=23.9/53,flip=0` | tool sine 42 Hz, 2.9 g (0.41 mm), 65 deg up |
| 6 | I-88c112b1 | inserts | **0.174** | 0.198 +/- 0.024 | 0.190 | 30% / 100% | 58% / 53% | 100% / 25% | 0.7 | 0.0 | 3.0 (9/9) | PEN 9/9 (clr 0.01, pen 1.250) | square holes 3.1 (bar 2) / 0.9 (bar 1.4) | `inserts:h2p95b2p15,h0p75b1p55` | tool sine 12 Hz, 3.6 g (6.21 mm), 5 deg up |
| 7 | I-fad46aab | inserts | **0.135** | 0.228 +/- 0.093 | 0.221 | 30% / 90% | 86% / 53% | 93% / 50% | 8.0 | 0.0 | 3.4 (9/9) | PEN 3/9 (clr 0.19, pen 0.221) | square holes 4.5 (bar 1.2) / 1.8 (bar 1) | `inserts:h4p35b1p35,h1p65b1p15` | firmware 10 mm at 50 mm/s, along the tray |
| 8 | G-a4d208e8 | gated | **-0.000** | -0.000 +/- 0.000 | -0.000 | 11% / 100% | 0% / 0% | 0% / 0% | 0.0 | 0.0 | 0.0 (9/9) | ok | L1 t2.9 / L2 w1.2x8; slope 2 deg, tunnel width 8, tooth 2, slot 7 | `gated:2,t2p75,w1p05x7p85,tw=7.85,tooth=2.15,slot=7` | firmware 10 mm at 50 mm/s, along the tray |
| 9 | G-127ae062 | gated | **-0.019** | -0.011 +/- 0.008 | -0.013 | 31% / 100% | 51% / 53% | 0% / 0% | 0.7 | 0.0 | 3.6 (9/9) | PEN 9/9 (clr 0.01, pen 0.369) | L1 t2.3 / L2 w1x1.4; slope 3.7 deg, tunnel width 4.7, tooth 0.9, slot 12.6 | `gated:3.7,t2p15,w0p85x1p25,tw=4.55,tooth=1.05,slot=12.6` | tool sine 35 Hz, 3.5 g (0.71 mm), 15 deg up |
| 10 | G-5f77a937 | gated | **-0.026** | -0.010 +/- 0.016 | -0.017 | 38% / 100% | 55% / 66% | 11% / 0% | 0.4 | 0.0 | 6.7 (9/9) | PEN 9/9 (clr 0.05, pen 0.576) | L1 t2.3 / L2 w0.9x3.5; slope 2.3 deg, tunnel width 9.6, tooth 2.2, slot 11.2 | `gated:2.3,t2p15,w0p75x3p35,tw=9.45,tooth=2.35,slot=11.2` | tool sine 36 Hz, 3.7 g (0.71 mm), 35 deg up |

## Best of each family (style)

| # | id | family | robust | mean +/- sd | worst mu set | > 6 mm pur / rec | 2-6 mm pur / rec | < 2 mm pur / rec | jammed | lost | t90 s | flags | design (CAD, nominal mm) | sim spec (as printed) | stroke |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 9 | G-a4d208e8 | gated | **-0.000** | -0.000 +/- 0.000 | -0.000 | 11% / 100% | 0% / 0% | 0% / 0% | 0.0 | 0.0 | 0.0 (9/9) | ok | L1 t2.9 / L2 w1.2x8; slope 2 deg, tunnel width 8, tooth 2, slot 7 | `gated:2,t2p75,w1p05x7p85,tw=7.85,tooth=2.15,slot=7` | firmware 10 mm at 50 mm/s, along the tray |
| 4 | G-c46df8f7 | gated_mid | **0.226** | 0.351 +/- 0.125 | 0.334 | 37% / 92% | 88% / 64% | 92% / 85% | 0.4 | 0.0 | 10.9 (9/9) | BEYOND 1 (particles past an opening they can't fit); PEN 9/9 (clr 0.26, pen 0.894) | L1 w3.5x6.5 / L2 t1.5; slope 1.8 deg, tunnel width 6.9, tooth 2, L1 gate at x 22.5 with slot 13.4, L2 at x 53, unflipped | `gated:1.8,w3p35x6p35,t1p35,tw=6.75,tooth=2.15,slot=13.4/7,gx=22.5/53,flip=0` | tool sine 13 Hz, 4.1 g (6.03 mm), 10 deg up |
| 1 | P-8d6849ce | plinko | **0.351** | 0.470 +/- 0.119 | 0.397 | 74% / 57% | 89% / 78% | 78% / 92% | 2.1 | 0.0 | 4.7 (9/9) | PEN 9/9 (clr 0.05, pen 0.706) | rods L1 gap 3.1 (rod 2.4 wide, 2.4 tall) / L2 gap 1.3 (rod 2.6, 3.4) | `plinko` | tool sine 32 Hz, 4.0 g (0.97 mm), 75 deg up |
| 6 | I-88c112b1 | inserts | **0.174** | 0.198 +/- 0.024 | 0.190 | 30% / 100% | 58% / 53% | 100% / 25% | 0.7 | 0.0 | 3.0 (9/9) | PEN 9/9 (clr 0.01, pen 1.250) | square holes 3.1 (bar 2) / 0.9 (bar 1.4) | `inserts:h2p95b2p15,h0p75b1p55` | tool sine 12 Hz, 3.6 g (6.21 mm), 5 deg up |
| 7 | C-243bf513 | current | **0.168** | 0.238 +/- 0.070 | 0.226 | 72% / 65% | 89% / 37% | 69% / 89% | 17.0 | 0.0 | 0.7 (9/9) | ok | TODAY on the bench: glued mesh inserts mesh5 / mesh2, firmware cap stroke | `inserts:mesh5,mesh2` | firmware 10 mm at 50 mm/s, along the tray |

## References (fixed, not tuned)

| id | what | robust | mean +/- sd | worst mu set | > 6 mm pur / rec | 2-6 mm pur / rec | < 2 mm pur / rec | jammed | lost | t90 s | flags | spec |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| G-a4d208e8 | gatecalc plan (skill) for the length classes: gated t2.9 / w1.2 (8 tall), firmware cap stroke | -0.000 | -0.000 +/- 0.000 | -0.000 | 11% / 100% | 0% / 0% | 0% / 0% | 0.0 | 0.0 | 0.0 (9/9) | ok | `gated:2,t2p75,w1p05x7p85,tw=7.85,tooth=2.15,slot=7` |
| P-2ee377b0 | plinko_layers.py as in the repo: rods 5.0 / 1.4, firmware cap stroke | 0.267 | 0.398 +/- 0.132 | 0.390 | 50% / 66% | 82% / 67% | 80% / 67% | 8.1 | 0.0 | 2.6 (9/9) | PEN 2/9 (clr 0.16, pen 0.148) | `plinko` |
| I-fad46aab | printed inserts as in the repo: 5 mm / 2 mm square holes, firmware cap stroke | 0.135 | 0.228 +/- 0.093 | 0.221 | 30% / 90% | 86% / 53% | 93% / 50% | 8.0 | 0.0 | 3.4 (9/9) | PEN 3/9 (clr 0.19, pen 0.221) | `inserts:h4p35b1p35,h1p65b1p15` |
| C-243bf513 | TODAY on the bench: glued mesh inserts mesh5 / mesh2, firmware cap stroke | 0.168 | 0.238 +/- 0.070 | 0.226 | 72% / 65% | 89% / 37% | 69% / 89% | 17.0 | 0.0 | 0.7 (9/9) | ok | `inserts:mesh5,mesh2` |

## Best per drive

BioKEA's stage can only run the firmware stroke (constant speed); the demo rig is a vibrating tool (sine). Best full-run design for each, whether or not it is flagged:

| drive | id | family | robust | flags | design (CAD, nominal mm) | stroke |
|---|---|---|---|---|---|---|
| firmware (BioKEA's stage) | P-2ee377b0 | plinko | 0.267 | PEN 2/9 (clr 0.16, pen 0.148) | rods L1 gap 4.2 (rod 2.4 wide, 3 tall) / L2 gap 1.4 (rod 2, 2.6) | firmware 10 mm at 50 mm/s, along the tray |
| vibrating tool (demo rig) | P-8d6849ce | plinko | 0.351 | PEN 9/9 (clr 0.05, pen 0.706) | rods L1 gap 3.1 (rod 2.4 wide, 2.4 tall) / L2 gap 1.3 (rod 2.6, 3.4) | tool sine 32 Hz, 4.0 g (0.97 mm), 75 deg up |

## Count matrices of the top 3 (summed over the 9 full runs)

**1. P-8d6849ce (plinko) rods L1 gap 3.1 (rod 2.4 wide, 2.4 tall) / L2 gap 1.3 (rod 2.6, 3.4); sim `plinko`**

| class \ ended in | layer_1_rods | layer_2_rods | layer_3_catch | between | lost |
|---|---|---|---|---|---|
| > 6 mm | 37 | 23 | 0 | 6 | 0 |
| 2-6 mm | 20 | 263 | 45 | 11 | 0 |
| < 2 mm | 0 | 11 | 167 | 2 | 0 |

**2. P-2ee377b0 (plinko) rods L1 gap 4.2 (rod 2.4 wide, 3 tall) / L2 gap 1.4 (rod 2, 2.6); sim `plinko`**

| class \ ended in | layer_1_rods | layer_2_rods | layer_3_catch | between | lost |
|---|---|---|---|---|---|
| > 6 mm | 45 | 12 | 0 | 9 | 0 |
| 2-6 mm | 37 | 226 | 27 | 49 | 0 |
| < 2 mm | 9 | 37 | 119 | 15 | 0 |

**3. P-2a281144 (plinko) rods L1 gap 1.8 (rod 2.8 wide, 3.2 tall) / L2 gap 0.9 (rod 2.9, 2.2); sim `plinko`**

| class \ ended in | layer_1_rods | layer_2_rods | layer_3_catch | between | lost |
|---|---|---|---|---|---|
| > 6 mm | 59 | 1 | 0 | 6 | 0 |
| 2-6 mm | 111 | 212 | 0 | 16 | 0 |
| < 2 mm | 0 | 74 | 103 | 3 | 0 |


Columns: purity = share of a bin's contents that belong to its class; recovery = share of a class that ends in its bin; jammed = particles per run stuck between bins (in a strip, slot or on a ledge); lost = out of the machine; t90 = seconds until 90% of the sample sits in its target bin (n/9 = runs that got there). Flags: FAIL = runs that went unstable or errored; PEN = particle-vs-gate overlap at or over 0.5 x the tightest gate clearance (near-size results untrustworthy); BEYOND = particles that ended past an opening their own size can't pass (soft contacts squeezed them through; should be 0, and is shown whenever it isn't).
