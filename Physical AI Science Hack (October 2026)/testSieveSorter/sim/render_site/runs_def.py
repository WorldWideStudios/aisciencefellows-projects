"""The runs the Sieve Render Lab shows, grouped by topic, each credited to the session that made it."""
from pathlib import Path

G = Path(r"C:\Users\ajfil\Documents\Github")
REPO_SIM = G / "testSieveSorter" / "sim"
CL = G / "testSieveSorter-clump/sim/out/runs"
BA = G / "testSieveSorter-bambu/sim/out/runs"
SE = G / "testSieveSorter-seesaw/sim/out/runs"
OP = G / "testSieveSorter-opt/sim/out/opt"
LY = G / "testSieveSorter-layers/sim/out/runs"
ML = "More levels (multi-layer)"

RUNS = [
    # gated ramp towers with gaps between levels, each level rocking on its own (main session, designs_gated pitch=)
    ("gatedgap", "Gated ramps, levels spaced apart (main)", "Ramp tower, 70 mm gaps, levels rock alternately",
     REPO_SIM / "out/runs/gated_mid_gap",
     "The optimizer's mid-slot ramp tower with 70 mm between levels, so each container lifts out on its own. Each level seesaws ±10° about its own "
     "middle, neighbours opposite, with the 0.4 mm 48 Hz shake thrown 30° up. Pasta and chickpea 15/15 on L1, every rice kind 57/58 on L2, "
     "fines 26/45 in the catch (12 still on L2). 6 fines bounced out through the gaps: a short skirt or lip per level would keep them. Trays never closer than 13.4 mm."),
    ("gatedgapflip", "Gated ramps, levels spaced apart (main)", "Same, alternate levels flipped",
     REPO_SIM / "out/runs/gated_mid_gap_flip",
     "The same spaced tower with every other level flipped (the standard gated layout). Rice still 56/58 on L2, but the fines stall on L2: none reach the catch."),
    ("gated3gap", "Gated ramps, levels spaced apart (main)", "3-level ramp tower, 70 mm gaps",
     REPO_SIM / "out/runs/gated3_gap",
     "The multi-layer session's 3-level ramp tower (tunnels 3.35 / 1.45 / 0.95 mm) with 70 mm gaps, alternating per-level seesaw + fast shake. "
     "Big 15/15 on L1, rice 44/58 on L2 and 11 on L3, quinoa 11/15 on L3, chia 9/15 in the catch, 4 fines lost through the gaps."),
    # more levels: one tray per size class (multi-layer session, sim/LAYERS.md)
    ("layers4best", ML, "4 trays + catch: 5 size classes (best, 2.25 mm tray 2)", LY / "layers_4tray_l2wide",
     "The best multi-level tower. Four ribs-across trays on centre pivots, 55 mm apart, over the catch pan. Square holes "
     "4.85 / 2.25 / 1.75 / 1.25 mm as modelled (print 5.0 / 2.4 / 1.9 / 1.4 mm; prints come out about 0.15 mm small). ±10° seesaw, "
     "neighbours opposite, 0.3 mm 40 Hz buzz, all 10 grains. Tray 1: pasta 10/10, chickpea 5/5. Tray 2: black rice 12/12 (and 7 of 10 "
     "wild rice, whose 10 mm needles lie flat). Tray 3: rice 11/12, white rice 11/12, brown rice 12/12. Tray 4: quinoa 15/15, couscous 12/15. "
     "Catch: chia 15/15 and 2 couscous. One seed, uncalibrated: the sim ranks designs, it doesn't predict percentages."),
    ("layers4", ML, "4 trays + catch, first try (2.15 mm tray 2)", LY / "layers_4tray_grains",
     "Four ribs-across trays on centre pivots, 55 mm apart, over the catch pan. Square holes 4.85 / 2.15 / 1.75 / 1.25 mm as modelled "
     "(print 5.0 / 2.3 / 1.9 / 1.4 mm; prints come out about 0.15 mm small). ±10° seesaw, neighbours opposite, 0.3 mm 40 Hz buzz. "
     "Tray 1 (4.85): pasta 10/10, chickpea 5/5. Tray 2 (2.15): black rice 12/12, but also 8 of 10 wild rice (the 10 mm needles lie flat "
     "and never stand up in a hole). Tray 3 (1.75): rice 11/12, white rice 11/12, brown rice 10/12. Tray 4 (1.25): quinoa 15/15, "
     "couscous 12/15. Catch: chia 15/15 and 2 couscous. Settled by 7 s."),
    ("layers5", ML, "5 trays + catch: adds a 1.95 mm brown-rice tray", LY / "layers_5tray_grains",
     "The same tower with a fifth tray, 1.95 mm (print 2.1), between 2.15 and 1.75, to give brown rice its own class. It only half works: "
     "it holds 8 of 12 brown rice, but also 4 of 12 white rice, and 3 brown rice still pass. Brown and white rice differ by about 0.1 mm "
     "in their smallest hole, so a sixth class needs measured grains first. Every other level is as in the 4-tray run."),
    ("layers4precise", ML, "4 trays with the gated tower's angled shake", LY / "layers_4tray_precise",
     "The 4-tray tower with the gated tower's shake (0.4 mm at 48 Hz, thrown 30° up) instead of the vertical 0.3 mm buzz. Worse for "
     "separate trays: 13 plain, white and brown rice stay on 2.15, 6 quinoa and couscous on 1.75, 4 chia on 1.25, and 5 fines bounce out. "
     "Keep the vertical buzz for trays."),
    ("layersgated3", ML, "Mid-slot ramp gated tower, 3 levels", LY / "layers_gated3_grains",
     "The optimizer's mid-slot ramp tower with a third level: tunnels 3.35 / 1.45 / 0.95 mm (gates at x 22.2 / 38 / 53, slots 8.1 / 7 / 7 mm, "
     "levels not flipped), rocking as one piece ±10° with 0.4 mm at 48 Hz thrown 30° up. Tunnels sort by thickness, so it makes 4 classes: "
     "L1 pasta 10/10, chickpea 5/5; L2 all five rices 56/58; L3 quinoa 12/15, couscous 7/15; catch chia 9/15. The fines were still "
     "moving at 12 s (8 couscous on L2)."),
    ("layersgated4", ML, "Mid-slot ramp gated tower, 4 levels (2.15 mm window gate)", LY / "layers_gated4_grains",
     "A 4-level try: a 2.15 × 2.15 mm window gate added as L2 to hold black rice, then tunnels 1.45 / 0.95 mm (gates at x 15 / 28 / 41 / 53). "
     "The window holds black rice 11/12 but also about half of every other rice (rice 5, white 5, brown 6, wild 8): grains reach a "
     "window lying flat, and a hole in a wall doesn't tip them the way a hole in a floor does. Square-hole trays do this split better."),
    ("layersinsect3", ML, "Malaise insects on an insect-cut 3-tray tower", LY / "layers_insect3_malaise",
     "60 specimens of the real Malaise mix on three trays cut for insects: 2.85 / 1.45 / 0.95 mm holes (print 3.0 / 1.6 / 1.1), same seesaw "
     "and buzz. By body length: > 6 mm 3/3 on tray 1; 2–4 mm 7 on tray 1, 9 on tray 2; 1–2 mm 8 on tray 2, 9 on tray 3; < 1 mm 13 of 19 "
     "in the catch, 5 bounce out. Legs and wings hold insects on holes 2–3× their body width, and 11 specimens end snagged in holes."),
    ("layersmalaise4", ML, "Malaise insects on the 4-tray grain tower", LY / "layers_4tray_malaise",
     "The same 60 specimens on the first 4-tray grain tower (4.85 / 2.15 / 1.75 / 1.25 mm). > 6 mm 3/3 stay on tray 1, 2–4 mm mostly on "
     "tray 2 (12 of 16), 1–2 mm split between tray 4 (8) and the catch (8), < 1 mm in the catch (10) or bounced out (9). Grain-sized "
     "holes are too coarse for the BugPicker classes; use the insect-cut tower."),
    # gated ramp designs on the seesaw with the precise fast shake (main session, the optimizer's designs)
    ("gatedmidseesaw", "Gated ramps on the seesaw + fast shake (main)", "Mid-slot ramp tower, all 10 grains",
     REPO_SIM / "out/runs/gated_mid_seesaw",
     "The optimizer's mid-slot gated tower with the 30° ramp (G-a1ecf9bb), rocking as one piece ±10° about its middle, with the optimizer's "
     "precise shake on top: 0.4 mm at 48 Hz, thrown 30° up. Pasta and chickpea 100% on L1; plain rice 12/12, white 10/12, brown 11/12 on L2 "
     "(it keeps the rice the sieves let through); chia 14/15, quinoa 12/15, couscous 11/15 in the catch. Black and wild rice partly stay on L1."),
    ("gatedmidseesawdemo", "Gated ramps on the seesaw + fast shake (main)", "Mid-slot ramp tower, its own 4-grain mix",
     REPO_SIM / "out/runs/gated_mid_seesaw_demo",
     "The same tower and motion with the optimizer's demo mix: pasta 8/8 and chickpea 8/8 on L1, rice 27/30 on L2, quinoa 29/30 in the catch."),
    ("gatedflipseesaw", "Gated ramps on the seesaw + fast shake (main)", "Standard gated tower, flipped levels, all 10 grains",
     REPO_SIM / "out/runs/gated_flip_seesaw",
     "The standard gated container (G-d726c2e8) on the same seesaw and shake. The rice kinds reach L2, but the fines stall there: 0 of 15 quinoa "
     "and chia reach the catch. Flipped levels don't suit a symmetric seesaw; the mid-slot ramp layout does."),
    # the demo stack
    ("after", "Demo stack: before and after (main)", "After: new parts + buzz", REPO_SIM / "out/runs/demo_after",
     "All 10 grain kinds. Ribs-across inserts on the centre-pivot holder (55 mm apart), ±10° seesaw with neighbours opposite, "
     "plus a 0.3 mm 40 Hz buzz. Quinoa, couscous and chia: 44 of 45 reach the catch. The buzz also shakes plain and white rice through 2 mm."),
    ("after30", "Demo stack: before and after (main)", "After, 30 s (sifted to the end)", REPO_SIM / "out/runs/demo_after_30s",
     "The same run as After, left going for 30 s so the sifting finishes."),
    ("before", "Demo stack: before and after (main)", "Before: old parts, seesaw only", REPO_SIM / "out/runs/demo_before",
     "The original 5 mm / 2 mm inserts 85 mm apart on the same ±10° seesaw, no buzz. 12 of 45 small grains sit on the 5 mm ribs."),
    # clumps: insects
    ("prmalaise", "Clumps: insects (clump session, main)", "Real Malaise mix on the printed breaker, spray on", CL / "pr_malaise_default",
     "Clump session (CLUMPS.md). 40 insects at the real Malaise size shares on breaker B-164f355a (the one being printed), "
     "±7° at 1.1 s + 0.35 mm buzz, spray on, medium bonds. Holds for 3 s, then collapses as it wets: 90% freed by 4 s, largest piece 2."),
    ("prmalaisedry", "Clumps: insects (clump session, main)", "Real Malaise mix on the printed breaker, spray off", CL / "pr_malaise_none",
     "Clump session. The same clump and breaker with the spray off: it stops at 25% freed, largest piece 30. The spray finishes the job."),
    ("insectbreaker", "Clumps: insects (clump session, main)", "Insect clump (2–6 mm, >6 mm) on the printed breaker",
     REPO_SIM / "out/runs/insect_clump_breaker",
     "Main session. 35 Malaise-size insects with a leaf, twig and dirt, 155 medium bonds, spray on, on breaker B-164f355a with its own motion. "
     "100% freed: half by 3.5 s, 90% by 5.0 s."),
    ("insectnobreaker", "Clumps: insects (clump session, main)", "Same insect clump, no breaker", REPO_SIM / "out/runs/insect_clump_nobreaker",
     "Main session. The same clump on the plain stack, ±10° seesaw, no buzz, no spray. It holds together: 9% freed, largest piece 32 of 35."),
    ("brkmalaise", "Clumps: insects (clump session, main)", "Real Malaise mix on the hand-designed breaker", CL / "brk_malaise_default",
     "Clump session. The CAD default breaker (8 mm grid, 2.5 × 12 mm pins), ±10° + 0.3 mm buzz, spray on: 60% freed at 4 s (35% with the spray off)."),
    # clumps: grains
    ("prgrain", "Clumps: grain surrogate (clump, bambu, main)", "Grain clump on the printed breaker", CL / "pr_grain_default",
     "Clump session. 106 grains on breaker B-164f355a, ±7° + buzz, spray on: 100% freed, 90% by 0.6 s."),
    ("grainbreaker", "Clumps: grain surrogate (clump, bambu, main)", "Optimizer's grain clump on the printed breaker",
     BA / "hero_malaise_B-164f355a",
     "Bambu session (hero clip). The optimizer's malaise clump on B-164f355a with its own motion: 100% freed; the leaf stays on top and the dirt reaches the catch."),
    ("herobreaker", "Clumps: grain surrogate (clump, bambu, main)", "Grain clump on the hand-designed breaker", BA / "hero_breaker_clump",
     "Bambu session (hero clip). The CAD default breaker over the 5 / 2 mm stack, ±10° seesaw, spray on: 97% freed, largest piece 3."),
    ("plainclump", "Clumps: grain surrogate (clump, bambu, main)", "Grain clump on the plain seesaw (holds)", CL / "c10_calib_seesaw",
     "Clump session. A plain ±10° seesaw with no breaker and no buzz: the medium clump sheds nothing and the ball sits over the pivot."),
    ("grainclump", "Clumps: grain surrogate (clump, bambu, main)", "First grain clump (±25°, weak bonds)", REPO_SIM / "out/runs/clump_seesaw_first",
     "The first clump, weak bonds on a ±25° seesaw. It came apart within 0.4 s. Superseded by the stickier clumps above."),
    # seesaw sorting
    ("plinkoseesaw", "Optimizer: seesaw winners", "Plinko rods 4.7 / 1.5 mm, ±14° + buzz", OP / "seesaw/replay/P-3bbfc231",
     "Optimizer. One box with three rod layers, ±14° at 1.9 s plus a 0.35 mm 40 Hz buzz. Robust 0.998: every class 100%, 90% sorted in 0.6 s."),
    ("plinkoseesaw10", "Optimizer: seesaw winners", "Plinko rods 4.5 / 1.4 mm, ±10.5° + buzz", OP / "seesaw/replay/P-3b817251",
     "Optimizer. The same idea at ±10.5°, 1.5 s per rock plus a 0.2 mm buzz. Robust 0.997."),
    ("vib015", "Seesaw + buzz amplitude (seesaw session)", "Buzz 0.15 mm", SE / "vib_a0.15",
     "Seesaw session. Old 5 / 2 mm stack, ±10° seesaw plus a 0.15 mm 40 Hz buzz: 2 chia still on 5 mm."),
    ("vib03", "Seesaw + buzz amplitude (seesaw session)", "Buzz 0.3 mm", SE / "vib_a0.3",
     "Seesaw session. The same with a 0.3 mm buzz: no quinoa, couscous or chia left on 5 mm."),
    ("vib05", "Seesaw + buzz amplitude (seesaw session)", "Buzz 0.5 mm", SE / "vib_a0.5",
     "Seesaw session. A 0.5 mm buzz: the fines all clear, and more plain rice goes through 2 mm."),
    ("abold", "Old vs new parts, seesaw only (bambu session)", "Old inserts, 85 mm apart", BA / "ab_old",
     "Bambu session A/B. Original inserts on the old holder, ±10° seesaw, no buzz: 7 of 12 quinoa left on 5 mm."),
    ("abnew", "Old vs new parts, seesaw only (bambu session)", "Ribs-across inserts, centre pivot 55 mm", BA / "ab_new",
     "Bambu session A/B. Ribs-across inserts on the centre-pivot holder: 1 of 12 quinoa left on 5 mm, and a 55 mm drop between levels instead of 85 mm."),
    ("seesaw5", "Seesaw angle sweep (main)", "±5° seesaw", REPO_SIM / "out/runs/seesaw_5deg",
     "150 grains of 9 kinds, old parts 85 mm apart, 2 s per rock, 8 s."),
    ("seesaw10", "Seesaw angle sweep (main)", "±10° seesaw", REPO_SIM / "out/runs/seesaw_10deg", "Same, at ±10°."),
    ("seesaw15", "Seesaw angle sweep (main)", "±15° seesaw", REPO_SIM / "out/runs/seesaw_15deg", "Same, at ±15°. Sorts best of the three."),
    ("seesaw25", "Seesaw angle sweep (main)", "±25° seesaw (too wide)", SE / "seesaw_tower",
     "Seesaw session's first tower run: pasta, rice and quinoa, 110 mm spacing. The user judged ±25° too wide."),
    # gated and earlier optimizer results (vibrating-tool shake, not the seesaw)
    ("gatedmid", "Gated containers with ramps (optimizer, vibrating-tool shake)", "Mid-slot gated tower with a 30° ramp",
     OP / "demo/replay/G-a1ecf9bb",
     "Optimizer's invented family G-a1ecf9bb: level-1 gate at mid-length with a drop slot and a solid 30° wedge ramp, levels not flipped, "
     "tunnels 3.5 / 1.6 mm, floor 2.7°. 48 Hz, 0.4 mm vibration thrown 30° up: every class 100%. "
     "On a symmetric seesaw gated designs can't sort, because nothing pushes grain to the gate."),
    ("gatedflip", "Gated containers with ramps (optimizer, vibrating-tool shake)", "Standard gated tower, flipped levels",
     OP / "demo/replay/G-d726c2e8",
     "Optimizer G-d726c2e8: the README's gated container with tunnels 4.4 / 1.8 mm and a 2.4° floor, every other level flipped, "
     "26 Hz 3.8 g flat shake. Every class 100%; L2 flagged near-size."),
    ("plinkotool", "Earlier optimizer results (vibrating-tool shake)", "Plinko 3.7 / 1.5 mm (printed plate #1)", OP / "demo/replay/P-ae394887",
     "Optimizer P-ae394887, the first winner plate sliced for the P1S: rod layers 3.7 / 1.5 mm on a 48 Hz vibration thrown 20° up. Robust 0.999."),
    ("mesh", "Earlier optimizer results (vibrating-tool shake)", "Today's glued mesh on the bench", OP / "demo/replay/C-243bf513",
     "Reference: BioKEA's glued mesh inserts on the firmware's 10 mm, 50 mm/s stroke. Robust 0.52; it jams."),
]
