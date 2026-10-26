# Verification under the rig's seesaw

Physics session, 2026-10-25 12:53, `sim/verify_seesaw.py`. The designs rerun on the motion the rig really makes (docs/SYSTEM.md section 3): each tray rocks about its own pivot across its middle (the ends tip), and neighbouring levels alternate. `rocking.py`'s lab-frame hinges, one per level.

- **Designs:** the demo rig the team built (printed 5 mm / 2 mm trays, `inserts:5mm,2mm`, pitch 85 mm); the demo study's top 2 from `opt/winners.json`, whose vibration strokes are replaced by the seesaw (a one-box design rocks as one level about the holder's middle, as the optimizer's seesaw study does it); and the optimizer's seesaw winners from `opt/winners_seesaw.json` when that file lands (it hadn't when this ran).
- **Runs:** fresh seeds 100-105 x 3 friction sets (default friction 0.3 / 0.4 / 0.5 (no calibration.json yet)) = 18 runs per design and stroke, 8 s of seesaw after a 1 s settle, the demo mix (rice 30, quinoa 30, chickpea 8, pasta 8), scored by `optimize.run_score` with the demo study's classes (robust = mean - 1 sd, as on the leaderboard). The optimizer's full runs are 30 s, so its scores aren't directly comparable: they are listed for the ranking only.
- **Contacts:** dt 0.25 ms / timeconst 0.5 ms for every run (the optimizer runs at 0.25 / 0.5).
- **Seesaw:** constant angular speed with smoothed reversals (as the firmware drives its stage), the catch pan rocking as the next level. The user hasn't picked the angle from the 5 / 10 / 15 deg renders; +/-10 deg is the default.
- The sim is uncalibrated: these scores rank designs, they don't predict bench percentages.

- **Incomplete:** demo rig: inserts:5mm,2mm,pitch=85, +/-10 deg, 2 s, constant speed: 8 of 18 runs.

<!-- summary -->
## Reading (physics session, 12:55)

**The batch was cut short.** Claude Code stopped it at 12:53 because Windows was critically low on memory (214 MB free of 32 GB). That says nothing about the runs themselves. 8 of the demo rig's 18 runs had finished, all three friction sets were covered, and none failed. The plinko winners hadn't started, and the optimizer had no seesaw winners to check yet. The rest needs memory first; see Reproduce.

**The demo rig on the ±10° seesaw sorts the big pieces, but only half sorts the rest in 8 s.** Robust 0.36 (mean 0.40, worst friction set 0.39), summed over the 8 runs:
- **Pasta and chickpea:** all 128 stay on the 5 mm tray. Their purity there is 0.48 only because small grains stay with them.
- **Rice:** 62% reaches the 2 mm tray. 20% is still on 5 mm at the end, and 17% passed the 2 mm holes into the catch pan. A 2 mm square hole is 2.8 mm across its diagonal, and rice is about 1.7 mm thick.
- **Quinoa:** 47% reaches the catch pan. **40% is still on the 5 mm tray**, and 13% sits on 2 mm.
- No run reached t90, so sorting was still going on at 8 s. Jams and losses are rare (0.1 per run).
- The closest neighbouring boxes come at 85 mm pitch is 28 mm, so they never touch.

**What it means:**
- It confirms the 11:20 angle renders (PLAN.md): ±10° is under the ~22° at which grains slide on plastic, so quinoa rides the 5 mm tray's solid ribs and never finds a hole.
- The rig needs one of the fixes being tested before the seesaw can be quoted as sorting the fine classes: the buzz on top (`vib_mm`, PR #18), ribs across the tilt, a steeper angle or longer runs.
- The vibration-tuned winners (robust 0.98–1.00 on their own 37–48 Hz strokes) weren't checked on the seesaw. A one-box plinko seesaw run costs about 4x a tower's.

The sim is uncalibrated: these numbers rank motions and designs; they aren't bench percentages.
<!-- /summary -->

## Seesaw +/-10 deg, 2 s, constant speed

**Order on robust:** demo-rig.

| Design | Optimizer robust (its own stroke) | Robust (mean - sd) | Mean | Worst friction set | big (pasta, chickpea) purity / recovery | rice purity / recovery | quinoa purity / recovery | Jams / lost per run | t90 s (reached) | Closest boxes mm | Fails |
|---|---|---|---|---|---|---|---|---|---|---|---|
| demo rig: inserts:5mm,2mm,pitch=85 | – | **0.355** | 0.398 | 0.385 | 0.48 / 1.00 | 0.83 / 0.62 | 0.74 / 0.47 | 0.12 / 0.12 | – (0/8) | 28.4 | 0 |
| demo #1 P-ae394887 (plinko, one box) | 0.999 | not run yet | | | | | | | | | |
| demo #2 P-b192da7c (plinko, one box) | 1.000 | not run yet | | | | | | | | | |

## Count matrices (summed over all runs; rows = class, columns = final bin)

**demo rig: inserts:5mm,2mm,pitch=85; seesaw +/-10 deg, 2 s, constant speed** (8 runs)

| Class | on_5mm | on_2mm | catch | between | lost |
|---|---|---|---|---|---|
| big (pasta, chickpea) | 128 | 0 | 0 | 0 | 0 |
| rice | 47 | 150 | 41 | 1 | 1 |
| quinoa | 95 | 31 | 114 | 0 | 0 |

## Reproduce

```
python verify_seesaw.py --deg 10 --period 2 --seeds 6 --duration 8 --top 2 --pitch 85 --workers 4 --dt 0.00025 --tc 0.0005 --onebox-seeds 2
```
