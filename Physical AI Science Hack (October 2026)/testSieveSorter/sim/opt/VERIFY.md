# Verification of the optimizer's winners (demo)

Physics session, 2026-10-25 09:59, `sim/verify.py`. The second opinion the brief's honesty rules ask for: the optimizer's runs are the screening, this reruns its top designs independently.

- **Winners checked:** `opt/winners.json` generated 2026-10-25 07:14, top 3, plus the demo rig (`inserts:5mm,2mm`, the stacked trays the team built) with the firmware stroke and shaken up and down.
- **Runs:** fresh seeds 100-105 (the optimizer used 0-2) x 3 friction sets (default friction 0.3 / 0.4 / 0.5 (no calibration.json yet)) = 18 runs per design and variant, 30 s of shaking each, scored with `optimize.run_score` (robust = mean - 1 sd, as on the leaderboard).
- **Variants:** the study's mix (rice 30, quinoa 30, chickpea 8, pasta 8); a heavy load, 2x every kind, in the same 30 s; and the study's mix with contacts one setting stiffer, to see whether soft contacts are doing some of the sorting.
- **Contacts:** measured per design: 3 runs of 2 s at each setting, on the design's own stroke; the cheapest setting whose median every-step gate and screen overlap stays under half the design's tightest clearance. `contact_rule.py`'s pick is listed beside it (VERTICAL.md, Contact rule). The optimizer ran everything at dt 0.25 ms / timeconst 0.5 ms.
- **Flags** (a run whose overlap with gates and screens reaches 0.5 x the tightest clearance): *10th* reads the overlap every 10th step, as optimize.py does; *every* reads it every step, which catches an impact's peak.
- The sim is uncalibrated: these scores rank designs, they don't predict bench percentages.
- **Incomplete:** the run stopped before these finished, so their rows cover fewer runs: demo rig: inserts:5mm,2mm, firmware cap stroke, heavy: 14 of 18; demo rig: inserts:5mm,2mm, up and down (2 g sine at 20 Hz, VERTICAL.md), normal: 7 of 18; demo rig: inserts:5mm,2mm, up and down (2 g sine at 20 Hz, VERTICAL.md), heavy: 0 of 18; demo rig: inserts:5mm,2mm, up and down (2 g sine at 20 Hz, VERTICAL.md), stiff: 7 of 18.

<!-- summary -->
## Reading (physics session, 10:10)

**What was checked.** The 07:14 winners:
- P-ba5dd6b3 and P-cbe7dbec: plinko, firmware stroke;
- G-a48f4670: gated_mid, 37 Hz sine at 45°;
- the stacked demo rig.

Since then the optimizer's 09:39 `winners.json` has a new top 3, all on the vibrating tool: P-ae394887, P-b192da7c and G-a1ecf9bb. **Those are not verified here.** P-ba5dd6b3 is still the optimizer's best design for BioKEA's firmware stroke, so its rows are current. P-cbe7dbec has dropped out: its 1.7 mm L2 gap leaks rice if printed loose.

**The run is incomplete.** Claude Code stopped it at 200 of 234 runs because the laptop ran low on memory (2.3 of 31 GB free). The three winners finished every variant. The demo rig is missing 34 runs:
- firmware stroke, heavy load: 4 of 18;
- up-and-down shake, study load: 11 of 18;
- up-and-down shake, heavy load: all 18.

The tables mark the partial rows.

1. **At the study load the ranking doesn't hold, but the gaps are small.**
   - On fresh seeds and measured contacts, the gated tower (#3) comes first on the robust score: 0.851, against 0.808 for #1 and 0.782 for #2.
   - On the mean, #3 vs #1 is within noise (0.918 vs 0.888, 2 se 0.049). #3 leads because it varies less from run to run.
   - #3 beats #2 clearly, and #1 vs #2 is within noise.
   - With contacts one setting stiffer, #3 leads #1 clearly: mean 0.928 vs 0.857.
2. **The plinkos' optimizer scores lean on soft contacts.**
   - The probe measured their L2 rod overlap at production contacts at 0.093 and 0.073 mm, against flag limits of 0.080 and 0.065 mm. So at the optimizer's dt 0.25 ms they sit at or over the flag line when the overlap is read every step. Reading every 10th step passed them.
   - With stiffer contacts they hold back more quinoa on layer 2. For P-ba5dd6b3 that is 9 % of quinoa at dt 0.125 ms and 12 % at 0.0625 ms; the optimizer saw 3 % at 0.25 ms (fresh seeds may account for part of the gap). Its mean falls 0.960 → 0.888 → 0.857, and its robust score 0.929 → 0.808 → 0.746.
   - The optimizer's stress test already puts this design's worst case at 0.870, with openings printed 0.25 mm undersize. Soft contacts are a second, independent reason to expect less than 0.93 on the bench.
   - The gated tower doesn't need soft contacts: stiffer contacts raise its robust score from 0.851 to 0.877.
3. **Under the heavy load (2x, same 30 s) the optimizer's order holds, clearly.**
   - Plinko #1 does better (0.906): it holds back less quinoa (4 %) and reaches t90 in 2 s.
   - The gated tower drops to 0.641 because its first level overloads. After 30 s, 102 of 1080 rice and 70 of 1080 quinoa are still on L1, and 4 of 18 runs never reach 90 %.
   - It needs a smaller batch or a longer shake than this load.
4. **The demo rig:** the stacked trays at the nominal 5 / 2 mm holes.
   - **Firmware stroke:** 0.685 robust (0.743 mean). Pasta stays on the 5 mm tray, but 19 % of the rice drops through 2 mm to the catch, and 5 % of the quinoa stays on the 5 mm tray. The heavy load gives the same (0.678 over 14 of 18 runs).
   - **Shaken up and down (2 g, 20 Hz):** it fails over 30 s, at 0.02 (7 runs). 89 % of the rice ends in the catch, as VERTICAL.md found over 10 s.
   - All three winners beat it.
5. **Contacts: the probe vs `contact_rule.py`.**
   - **Both plinkos:** the probe and the rule agree on 0.125 ms.
   - **Gated tower:** the rule picked the stiffest setting and called it untrustworthy, because its nearest measured stroke is 4 g at 20 Hz. The probe found production contacts enough (0.080 ≤ 0.115 mm). The rule was safe here, at 3.8x the wall time.
   - **Stacked rig, firmware stroke:** the rule **picks too soft a setting**. It says 0.125 ms, but the probe on the stack needed 0.0625 ms (0.076 > 0.065 mm). The rule's table came from single-tray designs, and the stack's 2 mm screen takes about twice their overlap: 0.179 against 0.092 mm at production.
   - Until the table includes the stack, run the stack at 0.0625 / 0.125 ms or probe it with this script.
6. **Next, when memory allows:**
   - **Verify the 09:39 winners:** `python verify.py --study demo --top 3 --seeds 6 --heavy 2 --workers 8`, about 2 h at 8 workers. With `--variants normal` it is about 40 min. The demo-rig runs are cached and get reused.
   - **Rerun the contact-rule grid with `inserts:5mm,2mm` added.**

The command below reads the current `opt/winners.json`. The 07:14 file checked here is in commit 7e6a416.
<!-- /summary -->

## Study load

**Ranking changes:** verified order #3 > #1 > #2. #1 - #2: mean +0.030 (2 se 0.052, within noise); #2 - #3: mean -0.060 (2 se 0.048, clear).

| Design | Optimizer robust | Robust (mean - sd) | Mean | Worst friction set | big (pasta, chickpea) purity / recovery | rice purity / recovery | quinoa purity / recovery | Jams / lost per run | t90 s (reached) | Flagged runs, 10th / every step | Fails |
|---|---|---|---|---|---|---|---|---|---|---|---|
| #1 P-ba5dd6b3 (plinko) | 0.929 | **0.808** | 0.888 | 0.812 | 1.00 / 1.00 | 0.92 / 0.98 | 0.98 / 0.91 | 0.00 / 0.00 | 5.0 (17/18) | 1 / 1 of 18 | 0 |
| #2 P-cbe7dbec (plinko) | 0.891 | **0.782** | 0.858 | 0.848 | 1.00 / 1.00 | 0.92 / 0.89 | 0.89 / 0.92 | 0.00 / 0.00 | 4.9 (12/18) | 0 / 0 of 18 | 0 |
| #3 G-a48f4670 (gated_mid) | 0.835 | **0.851** | 0.918 | 0.908 | 0.95 / 1.00 | 1.00 / 0.97 | 0.98 / 0.98 | 0.06 / 0.00 | 9.5 (18/18) | 1 / 1 of 18 | 0 |
| demo rig: inserts:5mm,2mm, firmware cap stroke | – | **0.685** | 0.743 | 0.699 | 0.88 / 1.00 | 0.99 / 0.79 | 0.83 / 0.94 | 0.00 / 0.00 | 13.8 (8/18) | 0 / 0 of 18 | 0 |
| demo rig: inserts:5mm,2mm, up and down (2 g sine at 20 Hz, VERTICAL.md) (7 of 18 runs) | – | **0.022** | 0.060 | 0.050 | 1.00 / 1.00 | 0.96 / 0.11 | 0.53 / 1.00 | 0.00 / 0.00 | – (0/7) | 0 / 3 of 7 | 0 |

## Heavy load (2x)

**Ranking holds:** verified order #1 > #2 > #3. #1 - #2: mean +0.058 (2 se 0.022, clear); #2 - #3: mean +0.159 (2 se 0.041, clear).

| Design | Optimizer robust | Robust (mean - sd) | Mean | Worst friction set | big (pasta, chickpea) purity / recovery | rice purity / recovery | quinoa purity / recovery | Jams / lost per run | t90 s (reached) | Flagged runs, 10th / every step | Fails |
|---|---|---|---|---|---|---|---|---|---|---|---|
| #1 P-ba5dd6b3 (plinko) | 0.929 | **0.906** | 0.941 | 0.904 | 0.98 / 1.00 | 0.96 / 0.99 | 0.99 / 0.95 | 0.00 / 0.00 | 2.0 (18/18) | 0 / 0 of 18 | 0 |
| #2 P-cbe7dbec (plinko) | 0.891 | **0.851** | 0.882 | 0.880 | 0.99 / 1.00 | 0.94 / 0.90 | 0.90 / 0.93 | 0.00 / 0.00 | 6.2 (18/18) | 0 / 0 of 18 | 0 |
| #3 G-a48f4670 (gated_mid) | 0.835 | **0.641** | 0.723 | 0.675 | 0.78 / 1.00 | 0.95 / 0.89 | 0.99 / 0.88 | 0.00 / 0.00 | 24.1 (14/18) | 1 / 5 of 18 | 0 |
| demo rig: inserts:5mm,2mm, firmware cap stroke (14 of 18 runs) | – | **0.678** | 0.747 | 0.698 | 0.83 / 1.00 | 0.99 / 0.80 | 0.83 / 0.89 | 0.00 / 0.00 | 14.6 (6/14) | 0 / 0 of 14 | 0 |
| demo rig: inserts:5mm,2mm, up and down (2 g sine at 20 Hz, VERTICAL.md) | – | not run yet | | | | | | | | | |

## Study load, contacts one setting stiffer

**Ranking changes:** verified order #3 > #2 > #1. #1 - #2: mean +0.023 (2 se 0.065, within noise); #2 - #3: mean -0.094 (2 se 0.045, clear).

| Design | Optimizer robust | Robust (mean - sd) | Mean | Worst friction set | big (pasta, chickpea) purity / recovery | rice purity / recovery | quinoa purity / recovery | Jams / lost per run | t90 s (reached) | Flagged runs, 10th / every step | Fails |
|---|---|---|---|---|---|---|---|---|---|---|---|
| #1 P-ba5dd6b3 (plinko) | 0.929 | **0.746** | 0.857 | 0.770 | 1.00 / 1.00 | 0.90 / 0.98 | 0.98 / 0.88 | 0.00 / 0.00 | 7.9 (16/18) | 0 / 0 of 18 | 0 |
| #2 P-cbe7dbec (plinko) | 0.891 | **0.755** | 0.835 | 0.826 | 0.99 / 1.00 | 0.90 / 0.89 | 0.89 / 0.89 | 0.00 / 0.00 | 7.0 (11/18) | 0 / 0 of 18 | 0 |
| #3 G-a48f4670 (gated_mid) | 0.835 | **0.877** | 0.928 | 0.908 | 0.95 / 1.00 | 1.00 / 0.96 | 0.98 / 0.99 | 0.00 / 0.00 | 10.9 (18/18) | 0 / 0 of 18 | 0 |
| demo rig: inserts:5mm,2mm, firmware cap stroke | – | **0.685** | 0.743 | 0.699 | 0.88 / 1.00 | 0.99 / 0.79 | 0.83 / 0.94 | 0.00 / 0.00 | 13.8 (8/18) | 0 / 0 of 18 | 0 |
| demo rig: inserts:5mm,2mm, up and down (2 g sine at 20 Hz, VERTICAL.md) (7 of 18 runs) | – | **0.022** | 0.060 | 0.050 | 1.00 / 1.00 | 0.96 / 0.11 | 0.53 / 1.00 | 0.00 / 0.00 | – (0/7) | 0 / 3 of 7 | 0 |

## Contacts and overlap per design

Max overlap over all runs of a variant, mm. Gate = gates and screens, read every 10th step / every step.

| Design | Tightest clearance mm | Probe: median gate overlap mm at 0.25 / 0.125 / 0.0625 ms | Used: dt / timeconst ms (pick; stiffer) | Why | contact_rule.py would pick | normal: gate 10th / every, floor | heavy: gate 10th / every, floor | stiff: gate 10th / every, floor | Wall s per run (normal, heavy, stiff) |
|---|---|---|---|---|---|---|---|---|---|
| #1 P-ba5dd6b3 (plinko) | 0.160 | 0.093 / 0.042 / 0.023 | 0.125 / 0.25; 0.0625 / 0.125 | median gate overlap 0.042 mm <= 0.080 mm | 0.125 / 0.25 | 0.089 / 0.089, 0.047 | 0.050 / 0.063, 0.062 | 0.025 / 0.025, 0.026 | 202, 381, 375 |
| #2 P-cbe7dbec (plinko) | 0.130 | 0.073 / 0.032 / 0.018 | 0.125 / 0.25; 0.0625 / 0.125 | median gate overlap 0.032 mm <= 0.065 mm | 0.125 / 0.25 | 0.038 / 0.045, 0.058 | 0.047 / 0.049, 0.061 | 0.021 / 0.022, 0.026 | 189, 400, 381 |
| #3 G-a48f4670 (gated_mid) | 0.230 | 0.080 / 0.045 / 0.025 | 0.25 / 0.5; 0.125 / 0.25 | median gate overlap 0.080 mm <= 0.115 mm | 0.0625 / 0.125 | 0.135 / 0.135, 0.222 | 0.120 / 0.164, 0.234 | 0.055 / 0.066, 0.112 | 56, 128, 104 |
| demo rig: inserts:5mm,2mm, firmware cap stroke | 0.130 | 0.179 / 0.076 / 0.045 | 0.0625 / 0.125; 0.0625 / 0.125 | median gate overlap 0.045 mm <= 0.065 mm | 0.125 / 0.25 | 0.050 / 0.064, 0.048 | 0.045 / 0.061, 0.053 | 0.050 / 0.064, 0.048 | 428, 828, 428 |
| demo rig: inserts:5mm,2mm, up and down (2 g sine at 20 Hz, VERTICAL.md) | 0.130 | 0.178 / 0.092 / 0.050 | 0.0625 / 0.125; 0.0625 / 0.125 | median gate overlap 0.050 mm <= 0.065 mm | 0.0625 / 0.125 | 0.070 / 0.190, 0.059 | – | 0.070 / 0.190, 0.059 | 207, –, 207 |

## Count matrices (summed over all runs; rows = class, columns = final bin)

**#1 P-ba5dd6b3 (plinko); study load** (18 runs)

| Class | layer_1_rods | layer_2_rods | layer_3_catch | between | lost |
|---|---|---|---|---|---|
| big (pasta, chickpea) | 288 | 0 | 0 | 0 | 0 |
| rice | 0 | 528 | 12 | 0 | 0 |
| quinoa | 1 | 49 | 490 | 0 | 0 |

**#1 P-ba5dd6b3 (plinko); heavy load (2x)** (18 runs)

| Class | layer_1_rods | layer_2_rods | layer_3_catch | between | lost |
|---|---|---|---|---|---|
| big (pasta, chickpea) | 576 | 0 | 0 | 0 | 0 |
| rice | 1 | 1066 | 13 | 0 | 0 |
| quinoa | 8 | 48 | 1024 | 0 | 0 |

**#1 P-ba5dd6b3 (plinko); study load, contacts one setting stiffer** (18 runs)

| Class | layer_1_rods | layer_2_rods | layer_3_catch | between | lost |
|---|---|---|---|---|---|
| big (pasta, chickpea) | 288 | 0 | 0 | 0 | 0 |
| rice | 0 | 531 | 9 | 0 | 0 |
| quinoa | 1 | 63 | 476 | 0 | 0 |

**#2 P-cbe7dbec (plinko); study load** (18 runs)

| Class | layer_1_rods | layer_2_rods | layer_3_catch | between | lost |
|---|---|---|---|---|---|
| big (pasta, chickpea) | 288 | 0 | 0 | 0 | 0 |
| rice | 0 | 478 | 62 | 0 | 0 |
| quinoa | 1 | 44 | 495 | 0 | 0 |

**#2 P-cbe7dbec (plinko); heavy load (2x)** (18 runs)

| Class | layer_1_rods | layer_2_rods | layer_3_catch | between | lost |
|---|---|---|---|---|---|
| big (pasta, chickpea) | 576 | 0 | 0 | 0 | 0 |
| rice | 0 | 967 | 113 | 0 | 0 |
| quinoa | 8 | 68 | 1004 | 0 | 0 |

**#2 P-cbe7dbec (plinko); study load, contacts one setting stiffer** (18 runs)

| Class | layer_1_rods | layer_2_rods | layer_3_catch | between | lost |
|---|---|---|---|---|---|
| big (pasta, chickpea) | 288 | 0 | 0 | 0 | 0 |
| rice | 0 | 478 | 62 | 0 | 0 |
| quinoa | 3 | 54 | 483 | 0 | 0 |

**#3 G-a48f4670 (gated_mid); study load** (18 runs)

| Class | L1 | L2 | catch | between | lost |
|---|---|---|---|---|---|
| big (pasta, chickpea) | 288 | 0 | 0 | 0 | 0 |
| rice | 6 | 522 | 11 | 1 | 0 |
| quinoa | 11 | 1 | 528 | 0 | 0 |

**#3 G-a48f4670 (gated_mid); heavy load (2x)** (18 runs)

| Class | L1 | L2 | catch | between | lost |
|---|---|---|---|---|---|
| big (pasta, chickpea) | 576 | 0 | 0 | 0 | 0 |
| rice | 102 | 964 | 14 | 0 | 0 |
| quinoa | 70 | 60 | 950 | 0 | 0 |

**#3 G-a48f4670 (gated_mid); study load, contacts one setting stiffer** (18 runs)

| Class | L1 | L2 | catch | between | lost |
|---|---|---|---|---|---|
| big (pasta, chickpea) | 288 | 0 | 0 | 0 | 0 |
| rice | 10 | 521 | 9 | 0 | 0 |
| quinoa | 5 | 1 | 534 | 0 | 0 |

**demo rig: inserts:5mm,2mm, firmware cap stroke; study load** (18 runs)

| Class | on_5mm | on_2mm | catch | between | lost |
|---|---|---|---|---|---|
| big (pasta, chickpea) | 288 | 0 | 0 | 0 | 0 |
| rice | 15 | 424 | 101 | 0 | 0 |
| quinoa | 27 | 3 | 510 | 0 | 0 |

**demo rig: inserts:5mm,2mm, firmware cap stroke; heavy load (2x)** (14 runs)

| Class | on_5mm | on_2mm | catch | between | lost |
|---|---|---|---|---|---|
| big (pasta, chickpea) | 448 | 0 | 0 | 0 | 0 |
| rice | 14 | 674 | 152 | 0 | 0 |
| quinoa | 82 | 9 | 749 | 0 | 0 |

**demo rig: inserts:5mm,2mm, firmware cap stroke; study load, contacts one setting stiffer** (18 runs)

| Class | on_5mm | on_2mm | catch | between | lost |
|---|---|---|---|---|---|
| big (pasta, chickpea) | 288 | 0 | 0 | 0 | 0 |
| rice | 15 | 424 | 101 | 0 | 0 |
| quinoa | 27 | 3 | 510 | 0 | 0 |

**demo rig: inserts:5mm,2mm, up and down (2 g sine at 20 Hz, VERTICAL.md); study load** (7 runs)

| Class | on_5mm | on_2mm | catch | between | lost |
|---|---|---|---|---|---|
| big (pasta, chickpea) | 112 | 0 | 0 | 0 | 0 |
| rice | 0 | 23 | 187 | 0 | 0 |
| quinoa | 0 | 1 | 209 | 0 | 0 |

**demo rig: inserts:5mm,2mm, up and down (2 g sine at 20 Hz, VERTICAL.md); study load, contacts one setting stiffer** (7 runs)

| Class | on_5mm | on_2mm | catch | between | lost |
|---|---|---|---|---|---|
| big (pasta, chickpea) | 112 | 0 | 0 | 0 | 0 |
| rice | 0 | 23 | 187 | 0 | 0 |
| quinoa | 0 | 1 | 209 | 0 | 0 |

## Reproduce

```
python verify.py --study demo --top 3 --seeds 6 --heavy 2 --workers 8
```
