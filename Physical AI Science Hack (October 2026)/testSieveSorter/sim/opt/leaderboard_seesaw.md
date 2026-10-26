# Leaderboard: Demo set on the rig's seesaw: each tray rocks about its middle (the ends tip), neighbours alternate, +/-5-15 deg (rocking.py)

Generated 2026-10-25 13:44 by `sim/optimize.py` (study `seesaw`). 51 candidates, 292 sim runs so far.

**The sim ranks designs; it does not predict real percentages.** It is uncalibrated until `calibrate.py` has bench counts, has no water, rigid particles, and about 80 particles per run. Sizes are simulated at the as-printed opening, nominal - 0.15 mm (ASSUMED until the hole gauge is measured).

Ranked by the robust score (mean - 1 sd) over 3 friction sets x 2 seeds at the full 16 s run. Score per run = min over classes of min(purity, recovery), minus 0.5 x jammed share, 1.0 x lost share and 0.05 x t90/duration. Failed (unstable) runs score -1. Only candidates promoted to the full run are ranked; screened-only ones are in the log. Solver: dt 0.25 ms, contact timeconst 0.5 ms (stiffer than sorter.py's default; see optimize.py). Friction sets: mu 0.3, mu 0.4, mu 0.5.

| # | id | family | robust | mean +/- sd | worst mu set | big (pasta, chickpea) pur / rec | rice pur / rec | quinoa pur / rec | jammed | lost | t90 s | flags | design (CAD, nominal mm) | sim spec (as printed) | stroke |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | P-3bbfc231 | plinko | **0.998** | 0.998 +/- 0.000 | 0.998 | 100% / 100% | 100% / 100% | 100% / 100% | 0.0 | 0.0 | 0.6 (6/6) | ok | rods L1 gap 4.7 (rod 3.5 wide, 3.2 tall) / L2 gap 1.5 (rod 2.9, 2.2) | `plinko` | seesaw +/-14 deg (ends tip, neighbours alternate), 1.9 s per cycle, constant speed + 0.35 mm buzz at 40 Hz |
| 2 | P-3b817251 | plinko | **0.997** | 0.997 +/- 0.001 | 0.997 | 100% / 100% | 100% / 100% | 100% / 100% | 0.0 | 0.0 | 0.9 (6/6) | ok | rods L1 gap 4.5 (rod 2.3 wide, 2.8 tall) / L2 gap 1.4 (rod 2.2, 2.6) | `plinko` | seesaw +/-10.5 deg (ends tip, neighbours alternate), 1.5 s per cycle, constant speed + 0.2 mm buzz at 40 Hz |
| 3 | P-690b1645 | plinko | **0.974** | 0.990 +/- 0.016 | 0.977 | 100% / 100% | 100% / 99% | 100% / 100% | 0.2 | 0.0 | 1.0 (6/6) | PEN 6/6 (clr 0.16, pen 0.130) | rods L1 gap 4.9 (rod 3.4 wide, 3.8 tall) / L2 gap 1.4 (rod 2.2, 3.4) | `plinko` | seesaw +/-13 deg (ends tip, neighbours alternate), 2.1 s per cycle, constant speed + 0.4 mm buzz at 40 Hz |
| 4 | P-a822b277 | plinko | **0.962** | 0.987 +/- 0.025 | 0.966 | 99% / 100% | 100% / 99% | 100% / 100% | 0.0 | 0.0 | 1.2 (6/6) | PEN 4/6 (clr 0.16, pen 0.116) | rods L1 gap 3.5 (rod 3.5 wide, 3 tall) / L2 gap 1.4 (rod 2.5, 3.6) | `plinko` | seesaw +/-6 deg (ends tip, neighbours alternate), 4.3 s per cycle, constant speed + 0.3 mm buzz at 40 Hz |
| 5 | I-beceacfc | inserts | **0.630** | 0.674 +/- 0.043 | 0.650 | 100% / 100% | 79% / 100% | 100% / 72% | 0.0 | 0.2 | 12.5 (2/6) | BEYOND 3 (particles past an opening they can't fit); PEN 6/6 (clr 0.05, pen 0.260) | square holes 5.2 (bar 1.1) / 1.8 (bar 1.2) | `inserts:h5p05b1p25,h1p65b1p35,pitch=85` | seesaw +/-11.5 deg (ends tip, neighbours alternate), 1.9 s per cycle, sine + 0.35 mm buzz at 40 Hz |
| 6 | I-ea7fafd8 | inserts | **0.389** | 0.530 +/- 0.141 | 0.517 | 100% / 100% | 100% / 57% | 71% / 100% | 0.0 | 0.5 | 2.2 (2/6) | PEN 6/6 (clr 0.01, pen 0.295) | square holes 5 (bar 1.2) / 2 (bar 1) | `inserts:h4p85b1p35,h1p85b1p15,pitch=85` | seesaw +/-10 deg (ends tip, neighbours alternate), 2 s per cycle, constant speed + 0.3 mm buzz at 40 Hz |
| 7 | I-c7efd18f | inserts | **0.364** | 0.382 +/- 0.018 | 0.367 | 49% / 100% | 79% / 74% | 89% / 44% | 0.0 | 0.0 | - (0/6) | PEN 6/6 (clr 0.01, pen 0.283) | square holes 5 (bar 1.2) / 2 (bar 1) | `inserts:h4p85b1p35,h1p85b1p15,pitch=85` | seesaw +/-10 deg (ends tip, neighbours alternate), 2 s per cycle, constant speed |
| 8 | P-8e00372e | plinko | **0.345** | 0.400 +/- 0.055 | 0.350 | 57% / 100% | 80% / 91% | 100% / 45% | 0.0 | 0.0 | - (0/6) | ok | rods L1 gap 4.7 (rod 2.6 wide, 2.2 tall) / L2 gap 1.6 (rod 2.3, 3.2) | `plinko` | seesaw +/-10 deg (ends tip, neighbours alternate), 2 s per cycle, constant speed |
| 9 | P-19e01862 | plinko | **0.336** | 0.383 +/- 0.047 | 0.367 | 52% / 100% | 85% / 90% | 100% / 44% | 0.0 | 0.0 | - (0/6) | ok | rods L1 gap 4.8 (rod 3.9 wide, 3.6 tall) / L2 gap 1.5 (rod 2.4, 3.6) | `plinko` | seesaw +/-13.5 deg (ends tip, neighbours alternate), 2.5 s per cycle, sine |
| 10 | P-fd614143 | plinko | **0.297** | 0.322 +/- 0.025 | 0.317 | 58% / 100% | 76% / 89% | 95% / 37% | 0.0 | 0.0 | - (0/6) | ok | rods L1 gap 5.5 (rod 2.6 wide, 2 tall) / L2 gap 1.7 (rod 3, 2.6) | `plinko` | seesaw +/-13 deg (ends tip, neighbours alternate), 1.3 s per cycle, sine |

## Best of each family (style)

| # | id | family | robust | mean +/- sd | worst mu set | big (pasta, chickpea) pur / rec | rice pur / rec | quinoa pur / rec | jammed | lost | t90 s | flags | design (CAD, nominal mm) | sim spec (as printed) | stroke |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | P-3bbfc231 | plinko | **0.998** | 0.998 +/- 0.000 | 0.998 | 100% / 100% | 100% / 100% | 100% / 100% | 0.0 | 0.0 | 0.6 (6/6) | ok | rods L1 gap 4.7 (rod 3.5 wide, 3.2 tall) / L2 gap 1.5 (rod 2.9, 2.2) | `plinko` | seesaw +/-14 deg (ends tip, neighbours alternate), 1.9 s per cycle, constant speed + 0.35 mm buzz at 40 Hz |
| 5 | I-beceacfc | inserts | **0.630** | 0.674 +/- 0.043 | 0.650 | 100% / 100% | 79% / 100% | 100% / 72% | 0.0 | 0.2 | 12.5 (2/6) | BEYOND 3 (particles past an opening they can't fit); PEN 6/6 (clr 0.05, pen 0.260) | square holes 5.2 (bar 1.1) / 1.8 (bar 1.2) | `inserts:h5p05b1p25,h1p65b1p35,pitch=85` | seesaw +/-11.5 deg (ends tip, neighbours alternate), 1.9 s per cycle, sine + 0.35 mm buzz at 40 Hz |
| 7 | C-4a07a203 | current | **0.406** | 0.514 +/- 0.108 | 0.394 | 99% / 100% | 100% / 62% | 80% / 90% | 6.3 | 0.8 | - (0/6) | PEN 4/6 (clr 0.13, pen 0.204) | TODAY on the bench: glued mesh inserts mesh5 / mesh2, 85 mm apart, on the default seesaw (+/-10 deg, 2 s) | `inserts:mesh5,mesh2,pitch=85` | seesaw +/-10 deg (ends tip, neighbours alternate), 2 s per cycle, constant speed |
| 6 | A-860ce30b | across | **0.528** | 0.577 +/- 0.048 | 0.559 | 63% / 100% | 90% / 78% | 90% / 73% | 0.0 | 0.0 | - (0/6) | PEN 6/6 (clr 0.13, pen 0.288) | RIBS ACROSS (bambu): 5mm_across / 2mm_across in the seesaw holder, 85 mm apart, default seesaw (+/-10 deg, 2 s) | `inserts:5mm_across,2mm_across,pitch=85,holder=seesaw` | seesaw +/-10 deg (ends tip, neighbours alternate), 2 s per cycle, constant speed |

## References (fixed, not tuned)

| id | what | robust | mean +/- sd | worst mu set | big (pasta, chickpea) pur / rec | rice pur / rec | quinoa pur / rec | jammed | lost | t90 s | flags | spec |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P-7064526e | plinko_layers.py as in the repo: rods 5.0 / 1.4, one box on the default seesaw (+/-10 deg, 2 s) | 0.207 | 0.283 +/- 0.076 | 0.233 | 66% / 100% | 69% / 96% | 100% / 33% | 0.0 | 0.0 | - (0/6) | ok | `plinko` |
| P-8e00372e | the demo study's leader P-b192da7c (rods 4.7 / 1.6, made for a 37 Hz tool) on the default seesaw | 0.345 | 0.400 +/- 0.055 | 0.350 | 57% / 100% | 80% / 91% | 100% / 45% | 0.0 | 0.0 | - (0/6) | ok | `plinko` |
| I-c7efd18f | DEMO RIG the team built: printed 5 mm / 2 mm trays, 85 mm apart, on the default seesaw (+/-10 deg, 2 s, neighbours alternate) | 0.364 | 0.382 +/- 0.018 | 0.367 | 49% / 100% | 79% / 74% | 89% / 44% | 0.0 | 0.0 | - (0/6) | PEN 6/6 (clr 0.01, pen 0.283) | `inserts:h4p85b1p35,h1p85b1p15,pitch=85` |
| C-4a07a203 | TODAY on the bench: glued mesh inserts mesh5 / mesh2, 85 mm apart, on the default seesaw (+/-10 deg, 2 s) | 0.406 | 0.514 +/- 0.108 | 0.394 | 99% / 100% | 100% / 62% | 80% / 90% | 6.3 | 0.8 | - (0/6) | PEN 4/6 (clr 0.13, pen 0.204) | `inserts:mesh5,mesh2,pitch=85` |
| I-ea7fafd8 | DEMO RIG on the default seesaw + a 0.3 mm buzz at 40 Hz (1.9 g; SEESAW.md 12:30) | 0.389 | 0.530 +/- 0.141 | 0.517 | 100% / 100% | 100% / 57% | 71% / 100% | 0.0 | 0.5 | 2.2 (2/6) | PEN 6/6 (clr 0.01, pen 0.295) | `inserts:h4p85b1p35,h1p85b1p15,pitch=85` |
| A-860ce30b | RIBS ACROSS (bambu): 5mm_across / 2mm_across in the seesaw holder, 85 mm apart, default seesaw (+/-10 deg, 2 s) | 0.528 | 0.577 +/- 0.048 | 0.559 | 63% / 100% | 90% / 78% | 90% / 73% | 0.0 | 0.0 | - (0/6) | PEN 6/6 (clr 0.13, pen 0.288) | `inserts:5mm_across,2mm_across,pitch=85,holder=seesaw` |
| A-0f850e1f | RIBS ACROSS (bambu): 5mm_across / 2mm_across in the seesaw holder, 85 mm apart, default seesaw + 0.3 mm buzz at 40 Hz | -0.029 | -0.004 +/- 0.025 | -0.013 | 100% / 100% | 100% / 5% | 51% / 99% | 0.0 | 0.3 | - (0/6) | PEN 6/6 (clr 0.13, pen 0.316) | `inserts:5mm_across,2mm_across,pitch=85,holder=seesaw` |

## Verification of flagged leaders at stiffer contacts

Rerun at dt 0.125 ms and contact timeconst 0.25 ms (half the overlap of the standard solver), 3 friction sets x 3 seeds, 16 s. A design that comes back with no flagged or failed run counts as clean for `winners.json`, ranked by the lower of its two scores.

| id | family | robust (standard) | flags (standard) | robust (stiff) | flags (stiff) | verdict | design |
|---|---|---|---|---|---|---|---|
| P-690b1645 | plinko | 0.974 | PEN 6/6 (clr 0.16, pen 0.130) | 0.996 | PEN 1/9 (clr 0.16, pen 0.219) | still flagged | rods L1 gap 4.9 (rod 3.4 wide, 3.8 tall) / L2 gap 1.4 (rod 2.2, 3.4) |
| P-a822b277 | plinko | 0.962 | PEN 4/6 (clr 0.16, pen 0.116) | 0.947 | ok | clean | rods L1 gap 3.5 (rod 3.5 wide, 3 tall) / L2 gap 1.4 (rod 2.5, 3.6) |

## Best per drive

BioKEA's stage can only run the firmware stroke (constant speed); the demo rig is a vibrating tool (sine). Best full-run design for each, whether or not it is flagged:

| drive | id | family | robust | flags | design (CAD, nominal mm) | stroke |
|---|---|---|---|---|---|---|

## Count matrices of the top 3 (summed over the 6 full runs)

**1. P-3bbfc231 (plinko) rods L1 gap 4.7 (rod 3.5 wide, 3.2 tall) / L2 gap 1.5 (rod 2.9, 2.2); sim `plinko`**

| class \ ended in | layer_1_rods | layer_2_rods | layer_3_catch | between | lost |
|---|---|---|---|---|---|
| big (pasta, chickpea) | 96 | 0 | 0 | 0 | 0 |
| rice | 0 | 180 | 0 | 0 | 0 |
| quinoa | 0 | 0 | 180 | 0 | 0 |

**2. P-3b817251 (plinko) rods L1 gap 4.5 (rod 2.3 wide, 2.8 tall) / L2 gap 1.4 (rod 2.2, 2.6); sim `plinko`**

| class \ ended in | layer_1_rods | layer_2_rods | layer_3_catch | between | lost |
|---|---|---|---|---|---|
| big (pasta, chickpea) | 96 | 0 | 0 | 0 | 0 |
| rice | 0 | 180 | 0 | 0 | 0 |
| quinoa | 0 | 0 | 180 | 0 | 0 |

**3. P-690b1645 (plinko) rods L1 gap 4.9 (rod 3.4 wide, 3.8 tall) / L2 gap 1.4 (rod 2.2, 3.4); sim `plinko`**

| class \ ended in | layer_1_rods | layer_2_rods | layer_3_catch | between | lost |
|---|---|---|---|---|---|
| big (pasta, chickpea) | 96 | 0 | 0 | 0 | 0 |
| rice | 0 | 179 | 0 | 1 | 0 |
| quinoa | 0 | 0 | 180 | 0 | 0 |


Columns: purity = share of a bin's contents that belong to its class; recovery = share of a class that ends in its bin; jammed = particles per run stuck between bins (in a strip, slot or on a ledge); lost = out of the machine; t90 = seconds until 90% of the sample sits in its target bin (n/9 = runs that got there). Flags: FAIL = runs that went unstable or errored; PEN = particle-vs-gate overlap at or over 0.5 x the tightest gate clearance (near-size results untrustworthy); BEYOND = particles that ended past an opening their own size can't pass (soft contacts squeezed them through; should be 0, and is shown whenever it isn't).
