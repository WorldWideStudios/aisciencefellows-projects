# [P] Bambu download + visualization / 3D modeling

> **Read [docs/SYSTEM.md](../SYSTEM.md) first** (added 10:30). It's the one description of the system: the input is a clump; the rig is separate trays one above the other, each held at its +X tab and overhanging, so they **rock**. It overrides this brief where they differ.

Worktree `Documents\Github\testSieveSorter-bambu`, branch `bambu-viz`. Read [README.md](README.md) first for the shared venv and the Smart App Control blocker.

## Scope
- **Install Bambu Studio** on this laptop. `cad\slice.py` expects it at `C:\Program Files\Bambu Studio\bambu-studio.exe`, with its profiles under `resources\profiles\BBL`. It isn't installed yet. The printer on the bench is a P1S (the default).
- **Get the CAD building again.** `cad\*.py` uses cadquery, which SAC blocks on Windows (see README.md). STL and STEP files go to `cad\out\` and aren't committed. Previews (`.png`) and `_checks.json` are.
- **Visualization and 3D modeling.** Previews, the assembled-stack views, and iterating on the current design: the gated container (`gated_container.py`), the inserts, and the holder (`frame_holder.py`). Dimensions are in `cad\WORKING_DIMENSIONS.md`. The `sieve-gate-design` skill in `.claude\skills\` goes from a sample spec to gate sizes.
- Then run `slice.py <part>` for print time and grams per iteration, and `hole_gauge.py` first so the openings match this printer.

## Not this session
- MuJoCo, `sim\`, timing and benchmarks: that's the physics session. `sim\viewer.py` (three.js replay) can be shared. Coordinate before changing `sim\viewer_template.html`.

## Done when
Bambu Studio is installed, `slice.py hole_gauge` prints an estimate, the gated-container parts rebuild, and their previews are updated in a PR.

## Status, 12:50 (relaunched at 12:25 for PLAN.md's bambu section)
- **CAD fixes, done (PR #21):** `cad/seesaw_holder.py` (a centre-pivot holder with no tab, and the deep catch pan with a lip) and `sieve_insert.py` ACROSS (ribs-across 5 / 2 mm). Each has a preview, checks, a P1S slice and a print-plan entry. The sim builds them as `inserts:5mm_across,2mm_across,pitch=55,holder=seesaw`.
- **Clump finding (drops of ~100 mm hit hardest):** without the tab, the levels clear at ~54 mm pitch at ±10°, so the drop is about halved. The 45° ramps and ridges make landings glancing, and TPU inserts would be the soft option (not sliced).
- **Print queue:** `sim/opt/print_plan.md`, top of the hand-written part. What's on the printer is a question for the user.
- **Next:** the tower preview, then an A/B sim of the old vs the new parts, then the hero visuals at ~13:45 (local `media/`, never committed).

## Hero visuals, 13:00 (local in the main checkout's `media/`, never committed)
- `media/hero_forum_vs_sim.mp4`: Forum's IMG_1315 (pasta and rice on the bench tray) beside the sim at real speed. The sim is the new parts (`inserts:5mm_across,2mm_across,pitch=55,holder=seesaw`), ±10°, all 10 grain kinds, labelled "MuJoCo sim, uncalibrated", with the counts in the caption (one seed). 11 s, 4.1 MB.
- `media/hero_seesaw_tower_rig.mp4`: the same run with the BugSorter rig drawn round it (`--rig bugsorter`), so you see the pivot axles and the levels tipping opposite ways. 11 s, 3.0 MB.
- `media/hero_clump_breaker.mp4`: a close-up at 1/4 speed of a grain-surrogate clump dropping onto the breaker layer's pins and seesawing ±10° under the spray. The clump is 86 grains (rice, quinoa, pasta), a leaf, 2 twigs and 10 dirt grains, with medium bonds. Captioned "MuJoCo sim, uncalibrated". 9.6 s, 2.2 MB. `media/hero_clump_tower_1x.mp4` is the whole 4-level tower at 1×. The run is `sim/out/runs/hero_breaker_clump`: `breaker:open=8,bar=1.6,pin_d=2.5,pin_h=12,pitch=10,tip=round` over 5 / 2 mm, 85 mm pitch, seed default.
  - **Break-up:** 97% of specimens free, t50 = 0.05 s and t90 = 0.12 s from the start of the shake, largest cluster left 3. The leaf blinded 0% of the holes on any layer.
  - **Where the force is:** peak contact force p90 was 241 mN over the run, against 27 mN while still bonded in the clump. This agrees with the clump session's finding that the drops between levels (85 mm here) hit harder than the break-up. The sim's force units aren't calibrated; they only rank designs.
  - If the clump session records an insect clump, it should replace this one in the pitch.
- Re-render the first two from the seesaw session's final all-grain run once it's on `main`, if the team prefers the current 5 / 2 mm parts in the pitch.

## The breaker to print, 13:40 (PLAN.md 13:30)
- **B-164f355a**, the optimizer's verified #1: `breaker_o11p3_b1p6_d3p1_h8_p8p5_round`, 57 min, 19.6 g. It's item 1 in `sim/opt/print_plan.md`. `cad/winners.py ../sim/opt/winners_malaise.json` builds and slices all three malaise winners into `sim/opt/print_plan_malaise.md`, and its Winner 1 is this one.
- **Clip:** `media/hero_optimizer_breaker.mp4` (close-up at 1/4 speed, captioned "MuJoCo sim, uncalibrated") and `media/hero_optimizer_breaker_tower_1x.mp4`. The run is `sim/out/runs/hero_malaise_B-164f355a`: the malaise grain clump (54 grains, a leaf, 2 twigs, 6 dirt grains, medium bonds) on its own stroke, ±7°, 1.1 s, with a 0.35 mm, 40 Hz buzz.
  - **Break-up:** 100% free, t50 = 0.07 s, t90 = 0.23 s, largest cluster 1.
  - **Debris:** the leaf stays on the breaker, the twigs on 5 mm, and 5 of 6 dirt grains reach the catch.
  - **The cost:** peak-force p90 was 815 mN, against 68 mN in the clump. The fast 1.1 s cycle hits hardest, and the drops between levels dominate, as the clump session found. The units aren't calibrated.
