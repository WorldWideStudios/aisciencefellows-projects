# Orchestration plan: 11:45 to submission

Written by the main session at 11:45 PT, Oct 25. **Submission is at 14:30**; live demos are 15:30–17:30. [docs/SYSTEM.md](../SYSTEM.md) is the source of truth for what the system is. This file says **who does what next**. Merge `origin/main`, read both, and do your section. Commit and open a PR at every checkpoint; the main session merges within minutes.

## The story we're submitting (everything below serves it)
1. **The problem:** a Malaise sample arrives as a **clump** of tangled insects with leaves, twigs and dirt. Sieves only sort loose specimens.
2. **Break-up:** a printed **breaker layer** (blunt pins on a grid), plus the rig's motion and spray, frees specimens gently.
3. **Sort:** the freed specimens fall through **separate stacked trays** that **seesaw** about their middles, with **neighbours alternating**. Coarse is on top, fine below, and a catch pan at the bottom.
4. **Self-improving design:** an optimizer runs the MuJoCo sim, ranks printable designs, writes down why the losers lost, and proposes new shapes. The winners are built and sliced for the P1S.
5. **Honesty:** the sim ranks designs; it isn't calibrated against bench counts yet. Every number says so.

## What the user has told us (don't contradict these)
- The input is a clump; breaking it up is the true point ([clump-breakup.md](clump-breakup.md)).
- The rig is separate trays, one above the other. Model the trays, particles, motion and spray, never the tool or motor.
- **Motion:** each tray seesaws about its own pivot across the middle (the ends tip), and neighbouring levels alternate so material doesn't fly off.
- **±25° is too wide.** Renders at ±5 / 10 / 15° are with the user. **Default to ±10° and search 5–15° until they pick.**
- Forum's photos are the demo example. Media stays local (`media/`, gitignored). Never commit clips or photos.
- Renders should use **all the grains we've modelled**: pasta, chickpea, rice, white_rice, brown_rice, black_rice, wild_rice, quinoa, couscous, chia (see `sim/GRAINS.md`).

## What the 11:20 angle renders showed (all 9 grains, 85 mm pitch, 2 s per cycle, 8 s)
- Pasta and chickpea always stay on 5 mm. The rice kinds mostly reach 2 mm.
- **Half the quinoa and most of the chia sit on the 5 mm tray at every angle.** All the angles are below the ~22° at which grains slide on plastic, so a gentle seesaw barely moves them. They sit on solid ribs instead of finding a hole. ±15° sorts best of the three.
- Fix options to test: a small fast vibration on top of the slow seesaw (the tool's buzz), longer runs, ribs running across the tilt instead of along it (the seesaw session saw grains ride X-ribs like rails), and taller catch-pan end walls (grains bounced out at 25°).

## 13:00 update: the demo configuration
Every final render and number for the pitch uses **the new seesaw parts plus the buzz**:
- design `inserts:5mm_across,2mm_across,pitch=55,holder=seesaw` (PR #21);
- stroke `seesaw:deg=10,period_s=2,vib_mm=0.3,vib_hz=40` (PRs #18 and #22).

Why:
- The ribs-across inserts cut the quinoa stuck on 5 mm from 7/12 to 1/12 (PR #24).
- The buzz clears quinoa, couscous and chia off 5 mm (PR #22).
- The 55 mm pitch cuts the drop impact by about 35%.
- Known cost: the buzz pushes plain `rice` / `white_rice` through 2 mm. Say so.
- Compare against the old parts with no buzz (`inserts:5mm,2mm,pitch=85`, `seesaw:deg=10,period_s=2`) as the before.

**Memory:** the laptop hit 214 MB free at 12:53, and several batches were killed. Run **one seed at a time, ≤ 3 workers each**, and cache everything so a rerun resumes. The optimizer keeps its workers but should drop to 8 if memory goes under 2 GB.


## 13:05 update: the optimizer's breaker is the hero part
Malaise round 0 (PR #27, grain clump): optimizer leader B-32a7c82c, an 11.4 mm grid with 1.4 × 6.8 mm round pins every 8 mm, on a ±12° seesaw at 2.5 s with a 0.35 mm, 40 Hz buzz. Robust score **0.638, 97% freed, 85% sorted**. Compare: the CAD default + buzz 0.479, the default without buzz 0.287, no breaker 0.217. Final rounds end ~13:40.
- **bambu:** once `sim/opt/winners_malaise.json` is final (~13:40), build and slice its #1 breaker with `cad/breaker_layer.py` (same keys). **Send it to the printer by ~13:50.** At about 90 min it's ready for the 15:30 live demo. Add it to the print plan, plus a clip of it breaking a clump (from its replay).
- **optimizer:** after the final round, write the winner's replay (`view.html`) and say in `leaderboard_malaise.md` which stroke settings the bench should use.

## 13:30 update: PRINT THIS breaker (verified on fresh clumps)
**B-164f355a**: `breaker:open=11.3,bar=1.6,pin_d=3.1,pin_h=8,pitch=8.5,tip=round`, on a ±7° seesaw at 1.1 s + 0.35 mm, 40 Hz buzz.
- Robust **0.630 pooled over all seeds**, 94% of fresh clumps freed (LOG.md, PR #34).
- Round 2's 0.700 leader (B-31c4ea6d) was lucky on one seed: 0.42 on fresh clumps. Don't print it, even though `winners_malaise.json` still lists it first.
- **Built and sliced by the main session:** `cad/out/slice/breaker_o11p3_b1p6_d3p1_h8_p8p5_round.gcode.3mf` in the main checkout. P1S, **57 min, 19.6 g**; 40 pins, 68.9% open; no flags.
- **bambu:** at 13:40, build from the verified ranking (LOG.md's verify table), not from the file order. If B-164f355a is still the verified #1, just add the slice above to the print plan.

## Next steps per session

### clump (`clump-sim`): critical path
1. **~12:15, PR:** `sim/clumps.py` plus the hook, and one clump that builds and visibly **breaks apart** on the seesaw tower, with a `view.html`. It's running now. Get it to `main`.
2. **Also an insect clump,** not only grains. Malaise clumps are insects (`insects.py` kinds, at the real size shares in `sim/INSECT_AUDIT.md`). Keep the grain clump as the bench-demo surrogate.
3. **~12:45:** write `sim/CLUMPS.md`.
   - Compare: bond weak / medium / strong × spray on / off × seesaw ±10° vs seesaw + vibration, with and without the breaker layer once `designs_breaker.py` exists.
   - Report t50 / t90 to free, the largest cluster left, the damage proxy and leaf blinding.
4. Workers ≤ 4.

### seesaw (`seesaw-tower`)
0. **Now:** the final renders in the demo configuration above, with all 10 grain kinds. Do one before / after pair, PR it, and record the counts in SEESAW.md.
1. **Done (PRs #18, #22):** add a **seesaw + vibration** stroke: a slow alternating seesaw plus a small fast oscillation on top, both parametrised.
   - Show whether it moves the stuck quinoa and chia off the 5 mm ribs.
   - Try ribs-across (when bambu has the spec) in the sim.
2. **~12:30, the final demo renders:**
   - all 10 grain kinds, at the user's chosen angle (±10° until told otherwise), 12–16 s;
   - seesaw alone vs seesaw + vibration;
   - pitch 85–110 mm;
   - `view.html` with `--rig bugsorter`;
   - put the counts table in `sim/SEESAW.md`, and PR.
3. Workers ≤ 4.

### optimizer (`design-opt`)
1. **Restart now, on the right motion:** use `rocking.py`'s **`seesaw:` stroke** (per level, alternating). Your old in-phase `rocking()` wrapper is wrong for the stack.
   - Angle 5–15°, period swept, plus the seesaw + vibration stroke when it lands.
   - Families: plinko and inserts first. Gated can't sort on a symmetric seesaw (your round 7).
   - 12 workers: the CPU is mostly idle.
2. **~12:30:** add `sim/designs_breaker.py` (the `breaker:` spec, matching `cad/breaker_layer.py`) and **study `malaise`**. Start its rounds as soon as the clump PR is on `main`.
   - Score: break-up first, then gentleness, then sort.
   - Label it EXPLORATORY.
3. Commit and PR **after every round**. Final `leaderboard_malaise.md` / `winners_malaise.json` by **~13:45**.

### physics (`physics-bench`)
1. **Real Malaise insect mix:** from `INSECT_AUDIT.md`, give the optimizer and the clump session a mix definition with the real size shares (56–58% under 1.5 mm). Put it in `insects.py` or a preset, without changing existing mixes. PR by ~12:30.
2. **Verify under the seesaw:**
   - Rerun the current winners and the optimizer's best seesaw designs with the alternating `seesaw:` stroke: 6 seeds × 3 friction sets.
   - Write `sim/opt/VERIFY_SEESAW.md` and open a PR by ~13:30.
3. Workers ≤ 4.

### bambu (`bambu-viz`)
1. **CAD fixes from the sim,** each with a preview, checks, a slice and a print-plan entry:
   1. a catch pan with taller end walls or an inward lip;
   2. a 5 mm insert with ribs **across** the tilt (or no solid strips along X), and give the seesaw session its sim spec;
   3. a seesaw holder with a **centre pivot axle and no +X tab** (about 85 mm pitch at ±15°).
2. **Print queue:** say in the print plan what's printing, what's printed, and what's next. The breaker layer takes 89 min.
3. **~13:45, hero visuals for the pitch,** local in `media/` and never committed. Use the Record button or `record_view.py`.
   - the seesaw tower with all grains (the seesaw session's run);
   - the clump breaking on the breaker layer (the clump session's run);
   - Forum's photo beside the sim, captioned "MuJoCo sim, uncalibrated".

### main
- Merge PRs as they land.
- Keep SYSTEM.md, the README and this plan true.
- By ~14:00:
  - the README tells the story above, with links to the results;
  - `docs/PITCH.md` has the 5-minute demo script, numbers and caveats;
  - the mascot is in the README header, once picked.
- **14:15 freeze:** no new features, fixes only. **14:30 submit.**

## Decisions only the user can make
1. **Seesaw angle:** ±5, ±10 or ±15° (or another)? And is a small fast vibration on top of the seesaw OK? It's what the handheld tool adds.
2. **Printer:** what's printed or printing now? Should the breaker layer print next?
3. **Bench demo:** will the team break up a real surrogate clump on the rig at the demo?
4. **Mascot:** A2 (sample jar into a 3-tier sieve) for the banner and B3 for the icon, or others?
5. **License,** and whether to purge the 7.8 MB clip from the git history (it's off `main` already).
