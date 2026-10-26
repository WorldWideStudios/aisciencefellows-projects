# Design optimizer log

One section per round. Sections marked "auto" are written by `sim/optimize.py` after each round; sections marked "notes" are the optimizer session's reading of them: what failed and why, the next hypothesis, and structural proposals that parameters can't express.

Tags: **executed** = a sim run in this log; **cited** = from another file, named; **assumed** = a placeholder until measured.

## Setup (notes, 2026-10-25 06:00)

**What is being optimized.** A design is a family plus its CAD parameters plus the stroke. Every family maps one to one onto CAD numbers that already exist, so a winner can be built without new geometry:

| Family | CAD | Searched |
|---|---|---|
| `gated` | `cad/gated_container.py` (README's final design) | floor slope 0.5-4 deg; L1 strip: width gap (with its own gap height, i.e. a "window") or tunnel; L2 tunnel; tunnel width; tooth; drop-slot length |
| `plinko` | `cad/plinko_layers.py` LAYERS | rod gap, rod top width, rod height (Z, 0.2 mm steps) for both rod layers |
| `inserts` | `cad/sieve_insert.py` INSERTS | square hole and bar for both inserts |
| all | BioKEA firmware | constant speed 15-50 mm/s (cap 50), amplitude 5-15 mm; ramp 0.01 s (assumed, sweep.py FIRMWARE) |

References, never tuned: the README design with the existing strips (w5.0 / t1.4, 2 deg), gatecalc's plan (t3.8 / t1.6), plinko and printed inserts as in the repo, and today's glued mesh inserts (`inserts:mesh5,mesh2`, not printable, so never a winner).

**Classes (demo study).** big = pasta + chickpea (L1), rice (L2), quinoa (catch), from the skill's sample spec (cited: `.claude/skills/sieve-gate-design/templates/sample-spec.toml`). Bins are the design's zones in flow order. Score = worst class of min(purity, recovery), minus jams, losses and a small t90 term; unstable runs score -1; ranked by mean - 1 sd over 3 friction sets x 3 seeds (details in the `optimize.py` docstring).

**The sim's gated tower** (new, `sim/designs_gated.py`). One holder box per level, rim on rim, container on the ledge, alternate levels flipped 180 deg, catch pan below. The sample is poured on the top container's high end. Every dimension is read from `gated_container.py` and `frame_holder.py`.

**Assumptions and settings.**
- Openings are simulated at the as-printed size, nominal - 0.15 mm (assumed undersize, from the skill; replace with `hole_gauge.py` data). Teeth and rods get 0.15 mm wider by the same token.
- Solver: dt 0.25 ms, contact timeconst 0.5 ms, not sorter.py's 0.5 / 2 ms. Cited: the physics session's instability probe (`testSieveSorter-physics/sim/out/instab/probe*.jsonl`, 1056 one-second runs, none unstable): the default let particles sink a median 0.49 mm (max 0.81) into the tray, more than the 0.15-0.3 mm clearance between rice, quinoa and the tunnel; 0.25 / 0.5 ms gave a median 0.07 mm (max 0.18) for about 1.6x the wall time. I'll switch to `sim/PERF.md`'s settings when physics commits them.
- The penetration flag uses the overlap against gate and screen geoms only (strip teeth, rods, screens), measured after the settle. Landing on a floor after a 25 mm drop between levels sinks deeper but can't push anything through an opening.
- An unstable run is detected by checking MuJoCo's BADQACC warning counter every 50 steps (MuJoCo resets and carries on otherwise, so the run would look fine). It scores -1.
- No new packages were added to `~/venvs/sieve`.

**Found while building (for the bambu session).**
- **Tab clash (executed geometry check, from the CAD numbers):** `gated_container.py` TAB_TOP = 25 mm above the container bottom. The container sits on the 3 mm ledge, so the tab top is at 28 mm in box coordinates, 3 mm above the 25 mm box rim. In a rim-on-rim stack, the tabs (y 41.7-47.7) run into the ledge of the box above (|y| 41-48). Either TAB_TOP <= 22 mm, or the boxes need 3 mm spacers. The sim cuts the tabs at 22 mm.
- **Rice parks crosswise at the w5 gate (executed: `gated:2,w5p0,t1p4`, 4 s, recorded).** The first rice reached the L1 strip after about 2 s and sat against the teeth at x 51.3 (strip face at 52) for the rest of the run: a 6.5 mm grain lying across the flow can't enter a 5 mm gap until it turns end-first.
- **Transport is slow on a 2 deg floor (same run).** At 50 mm/s and 10 mm amplitude, rice drifted toward the gate at about 7 mm/s on average and quinoa at about 4 mm/s. The poured sample starts 60-110 mm from the L1 strip, and what drops to L2 lands at its far end, 110 mm from the L2 strip. So 30 s may not finish the sort. That is why the 8 s screen ranks sorting progress, not the strict score.

**First hypotheses.**
1. The gated tower is transport-limited at today's 2 deg; the search will push slope and speed up, and a steeper floor eats into the 16 mm wall above the high end.
2. A window gate (w gap with a capped height) or a tunnel at L1 should beat the 8 mm tall w5 gap: pasta (6.5 x 6.0) can roll on edge through tall gaps once the gap is wider than 6.
3. Plinko should sort fastest (each grain only has to fall through a layer, not travel 110 mm), but rice may lie across the 1.4 mm rods and bridge them, and the drop from layer to layer is short.
4. Square-hole inserts cannot split rice from quinoa (same width, cited: `docs/gates-verdict.md`); they are in the search to show how far behind they are.

## Structural test: ratchet floor and steeper slope (notes, 2026-10-25 06:15)

**Hypothesis.** The gated tower is transport-limited. Sawtooth ribs across the floor (gentle face rising toward the gate, steep face on the gate side) should turn the symmetric stroke into one-way transport, as on a vibratory conveyor.

**Test (executed).** README design at the as-printed sizes (`gated:2,w4p85x7p85,t1p25,...`), firmware cap stroke (10 mm, 50 mm/s, ramp 0.01 s), mu 0.4, seed 0, dt 0.25 ms / timeconst 0.5 ms, 15 s shake. Runs in `sim/out/opt/ab/`, script `sim/out/opt/ab.sh`.

| variant | rice: L1 / L2 / catch / between at 15 s | quinoa: L1 / L2 / catch / between |
|---|---|---|
| A: 2 deg floor (README) | 20 / 8 / 0 / 2 | 24 / 5 / 0 / 1 |
| B: + ribs 0.8 tall, pitch 6, steep 0.15 | 30 / 0 / 0 / 0 | 30 / 0 / 0 / 0 |
| C: + ribs 0.6 tall, pitch 4, steep 0.15 | 30 / 0 / 0 / 0 | 30 / 0 / 0 / 0 |
| D: 3.5 deg floor, no ribs | 16 / 12 / 0 / 2 | 19 / 5 / 3 / 3 |

**Result: the ratchet floor stops transport completely.** The firmware stroke is constant speed with hard reversals. With the assumed 0.01 s reversal (`sweep.py` FIRMWARE ramp_s, a guess until the stroke is filmed) the tray's acceleration is a pulse of about 2 x 50 / 0.01 = 10 m/s^2 (1 g) for 10 ms at each reversal, and is zero in between. On a flat floor that slides a grain about 0.5 mm per reversal (relative speed gained (1 - mu) g x 10 ms, about 60 mm/s, then friction stops it). That's the slow drift seen in A. A rib's gentle face is several mm long, so a grain climbs a fraction of it and slides back into the valley. **Rejected; the ribs are not in the search.** The geometry stays available as `rib=<h>x<pitch>x<steep>` in `designs_gated.py`, should the measured stroke turn out to reverse much harder.

**What this says about transport.** Only gravity along the slope (tan 2 deg = 0.035 g) biases the random sliding, so a steeper floor helps (D vs A). But it costs wall height: at 4 deg the high end's floor is 8 mm up a 16 mm wall.

**Key unknown, flagged for the physics session:** the real reversal time. Transport scales with the reversal jolt, so a 2-5 ms reversal would change the gated tower's numbers a lot. The optimizer can't tune it (firmware hard-codes constant speed), but its winners should be rechecked once the stroke CSV from the video exists.

**Next structural hypothesis (mid-slot tower).** Today a grain travels the length of L1 to its gate, then drops onto the far, high end of the flipped L2 and travels the length of L2 again: about 220 mm in total at a few mm/s. Moving L1's gate and drop slot to mid-length, with L2 unflipped and its gate at the end, would land L1's passers about 25-60 mm upstream of L2's gate and roughly halve the total travel. The floor downstream of L1's slot then has to slope back into the slot. Implement as a family if round 0 confirms that the gated tower loses on transport.

## Structural test: mid-slot tower (notes, 2026-10-25 06:30)

**Hypothesis** (from the previous note). Put L1's gate and slot at mid-length and stop flipping L2. What passes L1 then lands just upstream of L2's gate, which should roughly halve the travel.

**Test (executed).** `designs_gated.py` options `gx=<x1>/<x2>` (gate position per level), `slot=<l1>/<l2>` and `flip=0`. Beyond a mid-length slot a 30 deg wedge fills the container and slopes back into the slot. The strip and rails must clear the pull tabs (|x| >= 13.15 mm). Same stroke, friction, seed and solver as the ratchet test; 15 s.

| variant | rice L1 / L2 / catch / between | quinoa L1 / L2 / catch / between |
|---|---|---|
| A: today, 2 deg | 20 / 8 / 0 / 2 | 24 / 5 / 0 / 1 |
| D: today, 3.5 deg | 16 / 12 / 0 / 2 | 19 / 5 / 3 / 3 |
| E: L1 gate at x 25, slot 8, L2 unflipped, 2 deg | 19 / 9 / 0 / 2 | 19 / 6 / 2 / 3 |
| F: as E at 3.5 deg | 20 / 8 / 0 / 2 | 16 / 9 / 1 / 4 |
| G: L1 gate at x 35, 2 deg | 22 / 8 / 0 / 0 | 22 / 4 / 0 / 4 |

**Result: no clear gain** (one seed, so weak evidence). Two thirds of the rice and quinoa are still on L1 after 15 s in every variant, so L1's own drift (a random walk of about 0.5 mm per reversal, biased only by the slope) is the bottleneck, not L2's travel. The mid-slot layouts also jam a few more quinoa (3-4 "between": on the ledges beside the shorter slot, or the wedge). **Rejected; not in the search.** The options stay in `designs_gated.py`.

**What would fix the gated tower's transport:** a harder stroke reversal (unknown until filmed; see the stress test on the leaderboard), a steeper floor (needs taller container walls, or it eats the 16 mm wall at the high end), or a different motion (an asymmetric stroke, which the firmware doesn't do). None of these is a gate-geometry change. **Plinko doesn't need transport at all:** a grain only hops across rods until it tips into a gap. That is why it leads the 8 s screen (rice 97%, quinoa 90% recovered, almost no leaks).

## demo round 0 (2026-10-25 06:34, auto)

**Tried:** gated: 30 (baseline, lhs); plinko: 13 (baseline, lhs); inserts: 7 (baseline, lhs); current: 1 (current). 603 runs, 35 min wall.

**Leader so far:** P-cbe7dbec (plinko, round 0) rods L1 gap 5.1 (rod 1.4 wide, 1.6 tall) / L2 gap 1.7 (rod 1.9, 3.2), stroke 14 mm at 41 mm/s: robust 0.891 (mean 0.929 +/- 0.038); big (pasta, chickpea) 99% pure / 100% recovered, rice 97% pure / 97% recovered, quinoa 97% pure / 96% recovered; ok.

**Screen results this round (8 s, progress score), best per family:**

- gated: best G-617e6c8a screen robust 0.368; median 0.331; failures in 0 of 30 candidates
- plinko: best P-2aaaaec0 screen robust 0.911; median 0.745; failures in 0 of 13 candidates
- inserts: best I-f660966d screen robust 0.735; median 0.608; failures in 0 of 7 candidates
- current: best C-243bf513 screen robust 0.590; median 0.590; failures in 0 of 1 candidates

**Why the losers failed** (particles per run, over this round's screened candidates in the bottom half of each family; the most common modes):

- gated: quinoa: held upstream -> L1 on the floor (28.1 in 15 cands); rice: held upstream -> L1 on the floor (25.5 in 15 cands); rice: held upstream -> L1 at the gate (within 10 mm) (3.4 in 15 cands); quinoa: held upstream -> L1 at the gate (within 10 mm) (1.2 in 12 cands); quinoa: held upstream -> L2 on the floor (0.7 in 10 cands); rice: between -> L1 in the strip (0.5 in 14 cands)
- plinko: rice: leaked downstream -> layer_3_catch (11.1 in 5 cands); quinoa: held upstream -> layer_2_rods (7.1 in 7 cands); quinoa: held upstream -> layer_1_rods (3.1 in 7 cands); rice: held upstream -> layer_1_rods (2.4 in 6 cands)
- inserts: quinoa: held upstream -> on_h1p55b1p35 (22.6 in 1 cands); rice: held upstream -> on_h2p65b0p95 (22.4 in 1 cands); quinoa: held upstream -> on_h1p55b1p25 (22.2 in 1 cands); quinoa: held upstream -> on_h1p45b1p25 (21.8 in 1 cands); rice: held upstream -> on_h3p15b1p35 (14.2 in 1 cands); rice: held upstream -> on_h3p55b1p85 (8.8 in 1 cands)
- current: rice: leaked downstream -> catch (6.6 in 1 cands); quinoa: between -> in the floor of on_mesh5 (2.0 in 1 cands); rice: between -> in the floor of on_mesh5 (1.6 in 1 cands); quinoa: held upstream -> on_mesh2 (0.6 in 1 cands); quinoa: between -> in the floor of on_mesh2 (0.2 in 1 cands)

**Leaders' remaining losses** (full runs, top 3):

- P-cbe7dbec: quinoa: held upstream -> layer_2_rods 1.1; rice: leaked downstream -> layer_3_catch 0.9; quinoa: held upstream -> layer_1_rods 0.2
- P-2aaaaec0: quinoa: held upstream -> layer_2_rods 1.7; rice: leaked downstream -> layer_3_catch 0.9; quinoa: held upstream -> layer_1_rods 0.3; rice: held upstream -> layer_1_rods 0.1
- P-e4035f89: quinoa: held upstream -> layer_2_rods 2.2; rice: leaked downstream -> layer_3_catch 0.9; quinoa: held upstream -> layer_1_rods 0.3; rice: held upstream -> layer_1_rods 0.2

**Parameters at a bound among each family's elite** (the range may be too narrow):

- gated: k1 w 0.17/t 0.83
- plinko: none
- inserts: none

**Next hypothesis (auto):** 0.9 particles per run leak through a gate they should not pass: tighten that gate or cap the gap height (window gate)


## demo round 0: reading (notes, 2026-10-25 06:45)

**What won and why.** Plinko, clearly. The best candidate, P-cbe7dbec, has rods 5.1 / 1.7 nominal and a 14 mm stroke at 41 mm/s. It sorts 97% of rice and 96% of quinoa into their bins at 97% purity, with no jams and no flags, and reaches t90 in about 4 s. Plinko needs no transport: a grain hops across the rods until it tips into a gap, a few mm away. The gated tower must walk every grain 100+ mm per level, and at the firmware's ~1 g reversal pulses no gated candidate got its quinoa through in 30 s (best quinoa recovery 11%, gatecalc's t3.8 / t1.6).

**Why the losers failed** (auto section above, read):
- **gated:** 25-28 of 30 rice and quinoa still on L1's floor after 8 s, 10+ mm from the gate. That is transport, not gate size. Its elite still learned something real: 83% chose a tunnel at L1 rather than a width gap. A tunnel cuts by thickness, so pasta can't roll through on edge (gatecalc's L1 pick too).
- **plinko:** the bottom half leaks rice to the catch (about 11 per run; the L2 gap is wider than rice is thick) or holds quinoa on layer 2 (about 7 per run; the gap is too tight for quinoa to tip into). Every top-3 plinko candidate chose an L2 gap of 1.7 nominal (1.55 as printed) between those two.
- **inserts:** square holes can't split rice from quinoa (same width). The repo's 5 / 2 mm inserts score 0.714, but only because rice's corner-to-corner diagonal (1.86 mm) is 0.01 mm wider than the as-printed 1.85 mm hole. All 9 runs are flagged; 0.1 mm of print tolerance leaks rice. Every other insert size either holds all quinoa or leaks rice.
- **today's glued mesh** (reference): 0.523. Rice 100% pure but only 67% recovered: 3.2 particles per run stick in the 5 mm mesh, and some rice leaks to the catch.

**Leaders' remaining losses.** About 1 quinoa per run stays on layer 2 and about 1 rice per run reaches the catch. The rice that leaks is the thin tail of the sim's rice (thickness 1.7 mm +/- 7%, so about 10% of rice is under the 1.55 mm gap). That overlap is in the material, not the machine. Real rice needs measuring (`sim/bench/grain_dims.csv`) before this matters.

**Winners rule (changed after seeing results; recorded here).** Before the first full results I set the rule: top 3 among candidates with no failed and no flagged run, filled with marked flagged ones only if fewer than 3 qualify. Applied to round 0, it put two gated designs into places 2 and 3, and both score below 0 (they sort almost nothing in 30 s). It skipped plinko designs scoring 0.85, whose only issue was 1-2 of 9 runs with a gate overlap of 0.094-0.098 mm against a 0.07 mm threshold. A winner has to be a working sorter, so I added a floor: robust score >= 0.5. The floor removes non-working designs; it doesn't favour a particular one. The flagged winners stay marked, with their overlap numbers, in `winners.json`.

**For the bambu session (print risk):** winner #1's layer-1 rods are 1.4 mm wide on top and 1.6 mm tall, tapering 8 deg to 0.95 mm at the bottom, over 43 mm spans between the rib and the wall. They're printable, but may be floppy. If they are, tell me the minimum rod size and I'll make it a constraint.

**Next hypothesis.**
1. Plinko's L2 gap is the critical number, and it sits 0.14 mm under the sim's rice thickness. The stress test reruns the top 3 with the printer making openings 0.1 mm tighter or looser, and with sharper or softer stroke reversals (0.005 / 0.02 s).
2. Rounds 1-2 (cross-entropy) refine plinko's rods and stroke. Expect the stroke amplitude to matter: the top 3 use 7.5-14 mm.
3. The gated tower stays in the search for completeness, but no gate geometry will fix its transport (see the two structural tests above).

## demo round 1 (2026-10-25 06:49, auto)

**Tried:** gated: 16 (ce); plinko: 8 (ce); inserts: 3 (ce). 306 runs, 14 min wall.

**Leader so far:** P-63092ca9 (plinko, round 1) rods L1 gap 5.6 (rod 2.1 wide, 2.6 tall) / L2 gap 1.6 (rod 1.6, 3.4), stroke 10 mm at 50 mm/s: robust 0.915 (mean 0.953 +/- 0.038); big (pasta, chickpea) 99% pure / 100% recovered, rice 96% pure / 100% recovered, quinoa 100% pure / 96% recovered; ok.

**Screen results this round (8 s, progress score), best per family:**

- gated: best G-331e7311 screen robust 0.429; median 0.335; failures in 0 of 16 candidates
- plinko: best P-63092ca9 screen robust 0.943; median 0.882; failures in 0 of 8 candidates
- inserts: best I-08d1890b screen robust 0.756; median 0.662; failures in 0 of 3 candidates

**Why the losers failed** (particles per run, over this round's screened candidates in the bottom half of each family; the most common modes):

- gated: quinoa: held upstream -> L1 on the floor (28.8 in 8 cands); rice: held upstream -> L1 on the floor (26.6 in 8 cands); rice: held upstream -> L1 at the gate (within 10 mm) (2.8 in 8 cands); quinoa: held upstream -> L1 at the gate (within 10 mm) (0.8 in 6 cands); quinoa: held upstream -> L2 on the floor (0.4 in 6 cands); rice: between -> L1 in the strip (0.5 in 3 cands)
- plinko: rice: leaked downstream -> layer_3_catch (4.4 in 4 cands); quinoa: held upstream -> layer_2_rods (3.0 in 4 cands); quinoa: held upstream -> layer_1_rods (1.8 in 4 cands); rice: held upstream -> layer_1_rods (0.5 in 4 cands)
- inserts: quinoa: held upstream -> on_h1p45b1p05 (26.3 in 1 cands); quinoa: held upstream -> on_h1p65b1p25 (15.4 in 1 cands); quinoa: held upstream -> on_h4p85b1p55 (6.3 in 1 cands); rice: held upstream -> on_h4p85b1p55 (4.6 in 1 cands); quinoa: held upstream -> on_h5p15b1p25 (2.8 in 1 cands); rice: held upstream -> on_h5p15b1p25 (0.3 in 1 cands)

**Leaders' remaining losses** (full runs, top 3):

- P-63092ca9: quinoa: held upstream -> layer_2_rods 1.2; quinoa: held upstream -> layer_1_rods 0.1
- P-cbe7dbec: quinoa: held upstream -> layer_2_rods 1.1; rice: leaked downstream -> layer_3_catch 0.9; quinoa: held upstream -> layer_1_rods 0.2
- P-7e49fbec: quinoa: held upstream -> layer_2_rods 2.3; quinoa: held upstream -> layer_1_rods 0.3

**Parameters at a bound among each family's elite** (the range may be too narrow):

- gated: k1 w 0.15/t 0.85
- plinko: none
- inserts: none

**Next hypothesis (auto):** the leader sorts cleanly; refine for robustness and throughput.


## demo round 1: reading, and the stroke-angle update (notes, 2026-10-25 06:55)

**What changed in the leader.** Cross-entropy moved plinko's layer-2 gap from 1.7 to 1.6 nominal (1.45 as printed). The new leader, P-63092ca9 (rods 5.6 / 1.6, robust 0.915), leaks no rice to the catch (round 0's leaders leaked 0.9 per run). It pays with about 1.2 quinoa per run left on layer 2. That is the right trade: rice now has 0.25 mm of margin over the gap and quinoa 0.35 mm under it, both above the 0.14 mm of the round 0 leaders. A wider margin also survives print tolerance better (the stress test will tell). It runs on **the firmware's own cap stroke**, 10 mm at 50 mm/s, so BioKEA's machine needs no new motion for it.

**Gated:** the best is now 0.071 (3.2 deg floor, tunnels 5.4 / 1.7, quinoa 34% recovered at 30 s). Still the same failure: 27-29 grains per run on L1's floor.

**Brief update (main, 05:50 and 06:05): stroke angle and the demo rig.** I merged `origin/main` (physics' `angle_deg`, `unstable_resets`, PERF.md: production solver dt 0.25 ms / timeconst 0.5 ms, the same as this optimizer already uses). Changes from round 2 on:
- **Two drives in the search.**
  - *firmware*: BioKEA's stage, constant speed 15-50 mm/s, 5-15 mm amplitude.
  - *tool*: a vibrating tool like the demo rig's, a sine at 10-50 Hz with 1-5 g peak acceleration.
  - Both take a stroke angle of 0-90 deg (0 = along the tray, 90 = straight up). Old candidates count as firmware at 0 deg, so their results stand.
  - Families that gained these parameters get an extra Latin hypercube batch to explore them, besides the cross-entropy proposals.
- **Demo-rig reference row:** `inserts:5mm`, shaken up and down as in the video (sine 20 Hz, 2 g, 90 deg, the motion physics assumed in `sim/VERTICAL.md`). It has two bins, so rice and quinoa share its catch, and the 3-class score shows exactly that.
- `sorter.py`'s own reset detection now also fails a run, besides the BADQACC counter.

**Structural hypothesis, revived by the angle: the unflipped mid-slot tower (`gated_mid`).** An angled throw is how a vibratory conveyor moves material in one direction, and it could cure the gated tower's transport problem. But the throw conveys toward the same end of every level, while today's tower flips every other level, so L2's grains would be conveyed away from L2's gate. The mid-slot layout tested at 06:30 keeps every gate at +X (L1's gate at mid-length with its drop slot, L2 unflipped at the end). It was useless under the firmware stroke, but it is the layout a directional throw needs. Round 2 adds it as the family `gated_mid` (Latin hypercube, 16 candidates): L1 gate x 14-38 mm (the strip has to clear the pull tabs) with a 6-14 mm slot ending at least 7 mm upstream of L2's strip, plus the whole stroke space.

## Constraint from the bambu session: rods and teeth at least two print lines (notes, 2026-10-25 07:00)

Bambu's `cad/build_winners.py` (branch `bambu-viz`, PR #4) flags rods, teeth and bars narrower than 0.8 mm (two 0.4 mm extrusion lines) as fragile, and openings under 0.8 mm as likely to close up on the first layer. Plinko rods taper 8 deg, so a tall, thin rod gets narrow at the bed. I adopted this as a hard constraint (`MIN_LINES`): a rod's width at the bed, top width - 2 x height x tan 8 deg, must be at least 0.8 mm. Winner selection re-checks every candidate against today's constraints.

Effect: two of round 1's top 3 drop out of `winners.json`, but stay on the leaderboard. P-63092ca9 (0.915) has layer-2 rods 1.6 wide and 3.4 tall, 0.64 mm at the bed. P-7e49fbec (0.860) has layer-1 rods 1.5 wide and 3.2 tall, 0.60 mm at the bed. Both have feasible neighbours (shorter rods), which round 3's proposals will find. The insect study's smallest openings go up from 0.6 to 0.8 mm for the same reason.

The `gated_mid` CAD block now keeps `GATE_X` scalar (L2, what today's script builds) and puts L1's position in `mid_slot_PROPOSAL`, so `build_winners.py` doesn't break on it. A mid-slot winner needs new L1 geometry first (`buildable_with_todays_cad: false`).

## demo round 2 (2026-10-25 07:12, auto)

**Tried:** demo_rig: 1 (current); gated: 20 (ce, lhs); gated_mid: 16 (lhs); plinko: 16 (ce, lhs); inserts: 5 (ce, lhs). 648 runs, 22 min wall.

**Leader so far:** P-ae394887 (plinko, round 2) rods L1 gap 3.7 (rod 2.6 wide, 1.6 tall) / L2 gap 1.5 (rod 1.8, 2.4), stroke tool sine 48 Hz, 2.2 g (0.24 mm), 20 deg up: robust 0.999 (mean 0.999 +/- 0.000); big (pasta, chickpea) 100% pure / 100% recovered, rice 100% pure / 100% recovered, quinoa 100% pure / 100% recovered; PEN 1/9 (clr 0.26, pen 0.153).

**Screen results this round (8 s, progress score), best per family:**

- demo_rig: best D-e018f15d screen robust 0.995; median 0.995; failures in 0 of 1 candidates
- gated: best G-0c6843ad screen robust 0.659; median 0.341; failures in 0 of 20 candidates
- gated_mid: best G-060cecb0 screen robust 0.876; median 0.333; failures in 0 of 16 candidates
- plinko: best P-668db784 screen robust 1.000; median 0.882; failures in 0 of 16 candidates
- inserts: best I-90aad5db screen robust 0.854; median 0.688; failures in 0 of 5 candidates

**Why the losers failed** (particles per run, over this round's screened candidates in the bottom half of each family; the most common modes):

- demo_rig: rice: held upstream -> on_5mm (0.1 in 1 cands)
- gated: quinoa: held upstream -> L1 on the floor (28.0 in 10 cands); rice: held upstream -> L1 on the floor (25.7 in 10 cands); rice: held upstream -> L1 at the gate (within 10 mm) (2.6 in 10 cands); quinoa: held upstream -> L1 at the gate (within 10 mm) (1.0 in 10 cands); quinoa: held upstream -> L2 on the floor (0.7 in 8 cands); quinoa: held upstream -> L2 at the gate (within 10 mm) (0.5 in 7 cands)
- gated_mid: quinoa: held upstream -> L1 on the floor (27.6 in 8 cands); rice: held upstream -> L1 on the floor (25.9 in 8 cands); rice: held upstream -> L1 at the gate (within 10 mm) (3.7 in 8 cands); quinoa: held upstream -> L1 at the gate (within 10 mm) (2.7 in 4 cands); quinoa: held upstream -> L2 in the drop slot (0.9 in 5 cands); quinoa: between -> L1 in the strip (0.3 in 4 cands)
- plinko: quinoa: held upstream -> layer_2_rods (8.1 in 7 cands); quinoa: held upstream -> layer_1_rods (4.8 in 7 cands); rice: held upstream -> layer_1_rods (6.6 in 5 cands); rice: leaked downstream -> layer_3_catch (7.6 in 3 cands); rice: between -> in the floor of layer_1_rods (0.8 in 2 cands); quinoa: between -> in the floor of layer_1_rods (0.7 in 1 cands)
- inserts: rice: held upstream -> on_h2p45b1p45 (28.6 in 1 cands); rice: held upstream -> on_h4p15b1p75 (18.9 in 1 cands); quinoa: held upstream -> on_h4p15b1p75 (17.7 in 1 cands); quinoa: held upstream -> on_h1p85b1p65 (10.8 in 1 cands); quinoa: held upstream -> on_h1p75b1p15 (10.3 in 1 cands); quinoa: held upstream -> on_h2p45b1p45 (8.4 in 1 cands)

**Leaders' remaining losses** (full runs, top 3):

- P-ae394887: none
- P-668db784: none
- G-060cecb0: rice: leaked downstream -> catch 0.4

**Parameters at a bound among each family's elite** (the range may be too narrow):

- gated: k1 w 0.22/t 0.78, drive firmware 0.78/tool 0.22, angle low (5.15)
- gated_mid: k1 w 0.50/t 0.50, drive firmware 0.14/tool 0.86
- plinko: drive firmware 0.74/tool 0.26, angle low (4.20)
- inserts: drive firmware 0.86/tool 0.14, angle low (0.87)

**Next hypothesis (auto):** the leader's near-size results are flagged (overlap vs clearance): check it at a smaller dt or stiffer contacts before trusting it


## demo round 2: reading (notes, 2026-10-25 07:20)

**The stroke matters more than the geometry.** Round 2 was the first with the vibrating-tool drive (sine) and the stroke angle. All three top designs use it:
- P-ae394887, plinko, rods 3.7 / 1.5, sine 48 Hz at 2.2 g (0.24 mm amplitude), 20 deg up: **0.999**. Every class 100% pure and recovered in all 9 runs, t90 0.4 s.
- P-668db784, plinko, rods 3.5 / 1.6, sine 14 Hz at 2.0 g, along the tray: 0.998.
- G-060cecb0, **gated_mid**, L1 window w3.1 x 3.1 at x 31.8, L2 t1.8, sine 28 Hz at 4.3 g, 10 deg up: **0.955**.

The best on BioKEA's firmware stroke is P-ba5dd6b3, plinko 5.6 / 1.6 at 9.5 mm and 47 mm/s, 5 deg up: 0.929. A small, fast vibration keeps every grain hopping over the rods or slots, so each gets many chances at a gap per second. The firmware stroke gives at most a ~1 g jolt 2.5 times a second.

**The structural hypothesis held.** Under the firmware stroke the gated tower couldn't move grain (best 0.07). The unflipped mid-slot layout with an angled throw sorts at 0.955, with 99-100% recovery per class and t90 7.8 s. The throw conveys every level toward +X, and only the unflipped layout has every gate at +X. Today's flipped tower with a tool-drive throw scored -0.05 at best: all 4 such candidates were run at full length, at angles of 10-55 deg, and sorted almost nothing (checked against the run cache). L2's grains are conveyed away from its gate.

**Why the losers failed (auto section above).**
- **gated and gated_mid** bottom halves: 26-28 grains still on L1's floor. They are mostly firmware-drive candidates, so transport again.
- **plinko** bottom half: quinoa held on layer 2 (8 per run) or rice leaking to the catch (8 per run), the same gap-size trade as before. Some rice is also held on layer 1 at the slower strokes.
- **inserts:** still can't split rice from quinoa.
- **The demo rig** (reference, 0.499): pasta and chickpea 100% on the screen, rice and quinoa all in the catch together. That is perfect at what it was built for (pasta vs rice). It has no second bin, so the 3-class score caps it near 0.5.

**Flags on the leaders.** P-ae394887 has 1 of 9 runs flagged (gate overlap 0.153 mm against a 0.13 threshold), P-668db784 has 3 of 9, and G-060cecb0 has 9 of 9. Its window gate is within 0.04 mm of a grain size, so its clearance is tiny. By the winners rule, none of them can be a winner yet. `winners.json` is P-ba5dd6b3 and P-cbe7dbec (firmware plinko, clean) and G-a48f4670 (gated_mid, sine 37 Hz at 2.5 g, 45 deg up, clean, 0.835).

**Next hypothesis and actions.**
1. **Verify the flagged leaders with stiffer contacts.** A new `verify` step reruns them at dt 0.125 ms and timeconst 0.25 ms (half the overlap, about 2x the time). A design that comes back unflagged and still scores well counts as clean in the winners rule. This resolves the untrustworthiness with a better solver; it doesn't loosen the rule. Queued after the insect round.
2. **Recommend per drive.** BioKEA's stage can only do the firmware stroke, while the demo rig is a vibrating tool, so `winners.json` gets a best-per-drive entry as well as the overall top 3.
3. **gated_mid** gets the next cross-entropy round (its elite is 86% tool drive).

## insects round 0 (2026-10-25 07:59, auto)

**Tried:** gated: 11 (baseline, lhs); plinko: 9 (baseline, lhs); inserts: 4 (baseline, lhs); current: 1 (current); gated_mid: 8 (lhs). 396 runs, 47 min wall.

**Leader so far:** P-8d6849ce (plinko, round 0) rods L1 gap 3.1 (rod 2.4 wide, 2.4 tall) / L2 gap 1.3 (rod 2.6, 3.4), stroke tool sine 32 Hz, 4.0 g (0.97 mm), 75 deg up: robust 0.351 (mean 0.470 +/- 0.119); > 6 mm 74% pure / 57% recovered, 2-6 mm 89% pure / 78% recovered, < 2 mm 78% pure / 92% recovered; PEN 9/9 (clr 0.05, pen 0.706).

**Screen results this round (8 s, progress score), best per family:**

- gated: best G-127ae062 screen robust 0.468; median 0.333; failures in 0 of 11 candidates
- plinko: best P-2a281144 screen robust 0.612; median 0.394; failures in 0 of 9 candidates
- inserts: best I-88c112b1 screen robust 0.509; median 0.430; failures in 0 of 4 candidates
- current: best C-243bf513 screen robust 0.133; median 0.133; failures in 0 of 1 candidates
- gated_mid: best G-c46df8f7 screen robust 0.649; median 0.333; failures in 0 of 8 candidates

**Why the losers failed** (particles per run, over this round's screened candidates in the bottom half of each family; the most common modes):

- gated: 2-6 mm: held upstream -> L1 on the floor (26.4 in 6 cands); < 2 mm: held upstream -> L1 on the floor (13.4 in 6 cands); 2-6 mm: held upstream -> L1 at the gate (within 10 mm) (29.1 in 2 cands); < 2 mm: held upstream -> L2 on the floor (12.2 in 2 cands); < 2 mm: held upstream -> L1 at the gate (within 10 mm) (6.6 in 2 cands); 2-6 mm: between -> L1 in the strip (1.9 in 2 cands)
- plinko: 2-6 mm: held upstream -> layer_1_rods (8.7 in 5 cands); < 2 mm: held upstream -> layer_2_rods (5.8 in 5 cands); 2-6 mm: between -> in the floor of layer_2_rods (3.4 in 5 cands); 2-6 mm: leaked downstream -> layer_3_catch (5.7 in 3 cands); < 2 mm: held upstream -> layer_1_rods (3.9 in 3 cands); 2-6 mm: between -> in the floor of layer_1_rods (2.2 in 5 cands)
- inserts: 2-6 mm: held upstream -> on_h2p35b1p35 (30.7 in 1 cands); 2-6 mm: held upstream -> on_h1p95b1p35 (28.3 in 1 cands); < 2 mm: held upstream -> on_h2p35b1p35 (12.2 in 1 cands); < 2 mm: held upstream -> on_h1p15b0p95 (5.3 in 1 cands); 2-6 mm: between -> in the floor of on_h1p95b1p35 (4.4 in 1 cands); < 2 mm: held upstream -> on_h1p25b1p15 (3.7 in 1 cands)
- current: 2-6 mm: leaked downstream -> catch (8.0 in 1 cands); 2-6 mm: between -> in the floor of on_mesh5 (7.4 in 1 cands); 2-6 mm: between -> in the floor of on_mesh2 (6.7 in 1 cands); 2-6 mm: held upstream -> on_mesh5 (2.1 in 1 cands); > 6 mm: between -> in the floor of on_mesh5 (1.6 in 1 cands); < 2 mm: between -> in the floor of on_mesh5 (1.3 in 1 cands)
- gated_mid: 2-6 mm: held upstream -> L1 on the floor (35.8 in 4 cands); < 2 mm: held upstream -> L1 on the floor (18.8 in 4 cands); 2-6 mm: held upstream -> L1 at the gate (within 10 mm) (7.2 in 1 cands); < 2 mm: held upstream -> L2 in the drop slot (1.9 in 1 cands); < 2 mm: held upstream -> L1 at the gate (within 10 mm) (1.6 in 1 cands); < 2 mm: held upstream -> L2 on the floor (0.8 in 1 cands)

**Leaders' remaining losses** (full runs, top 3):

- P-8d6849ce: 2-6 mm: leaked downstream -> layer_3_catch 5.0; > 6 mm: leaked downstream -> layer_2_rods 2.6; 2-6 mm: held upstream -> layer_1_rods 2.2; < 2 mm: held upstream -> layer_2_rods 1.2; 2-6 mm: between -> in the floor of layer_2_rods 1.0
- P-2ee377b0: 2-6 mm: held upstream -> layer_1_rods 4.1; < 2 mm: held upstream -> layer_2_rods 4.1; 2-6 mm: between -> in the floor of layer_2_rods 3.9; 2-6 mm: leaked downstream -> layer_3_catch 3.0; < 2 mm: between -> in the floor of layer_2_rods 1.7
- P-2a281144: 2-6 mm: held upstream -> layer_1_rods 12.3; < 2 mm: held upstream -> layer_2_rods 8.2; 2-6 mm: between -> in the floor of layer_1_rods 1.8; > 6 mm: between -> in the floor of layer_1_rods 0.7; < 2 mm: between -> in the floor of layer_2_rods 0.3

**Parameters at a bound among each family's elite** (the range may be too narrow):

- gated: k1 w 0.15/t 0.85, drive firmware 0.38/tool 0.62, k2 w 0.85/t 0.15
- plinko: drive firmware 0.38/tool 0.62
- inserts: drive firmware 0.38/tool 0.62
- gated_mid: k1 w 0.62/t 0.38, drive firmware 0.15/tool 0.85, k2 w 0.38/t 0.62

**Next hypothesis (auto):** 7.6 particles per run leak through a gate they should not pass: tighten that gate or cap the gap height (window gate); 2.1 particles per run jam between bins: see where in the losses list; the leader's near-size results are flagged (overlap vs clearance): check it at a smaller dt or stiffer contacts before trusting it


## insects round 0: reading (notes, 2026-10-25 08:05) -- EXPLORATORY

The insects are the generated specimens of `sim/insects.py`, with textbook sizes and none measured. The classes are BugPicker's body lengths: > 6 mm (L1), 2-6 mm (L2), < 2 mm (catch).

**Result: no design sorts these classes well, and the reason is structural.**
- The best is P-8d6849ce, plinko 3.1 / 1.3 on a sine at 32 Hz and 4 g, 75 deg up: robust 0.351. Recovery is 57% for > 6 mm, 78% for 2-6 mm and 92% for < 2 mm. gatecalc predicted about the same (10 / 45 / 98% recovery with its gates t2.9 / w1.2, from `gatecalc.py plan` on the malaise template with these length classes, run at 06:00). Gates cut width and thickness, and body length overlaps between the classes in both.
- No candidate reaches the 0.5 working-sorter floor, so `winners_insects.json` lists none.
- **Today's glued mesh jams 17 specimens per run** (legs caught in the mesh; it scores 0.168). That matches the warning in `docs/gates-verdict.md` about woven mesh as a fence.

**Every insect result is flagged.** Legs (capsules down to 0.06 mm radius) sink 0.4-1.25 mm into the rods and gates, while the clearances are about 0.05 mm, because some specimen is always near-size. One more reason these numbers rank but don't predict.

**Hypothesis (a question for the team, not for the optimizer):** BugPicker's real constraint is whether a specimen fits a 96-well, which is width-driven (`.claude/skills/sieve-gate-design/references/well-fit.md`). Gates can cut width; nothing in the stack cuts length. Classes defined by width, or "fits a well / doesn't", would be sortable. That's the team's call. Until then the insect study gets the leftover compute: one cross-entropy round after demo round 4.

## Verification of the flagged demo leaders (notes, 2026-10-25 08:10)

`verify` reran the four best flagged designs at dt 0.125 ms and timeconst 0.25 ms (half the contact softness), 3 friction sets x 3 seeds, 30 s:

| id | standard: robust, flags | stiff: robust, flags | verdict |
|---|---|---|---|
| P-ae394887 plinko 3.7 / 1.5, sine 48 Hz 2.2 g 20 deg | 0.999, 1/9 flagged | **1.000**, none (max gate overlap 0.077 mm, threshold 0.13) | **clean** |
| P-668db784 plinko 3.5 / 1.6, sine 14 Hz 2.0 g | 0.998, 3/9 | 1.000, 1/9 | still flagged |
| G-060cecb0 gated_mid, window 3.1 x 3.1 | 0.955, 9/9 | 0.940, 9/9 | still flagged |
| P-547508e5 plinko 3.1 / 1.7, sine 46 Hz 1.3 g 35 deg | 0.937, 1/9 | 0.927, none | **clean** |

The scores barely move with stiffer contacts, so the ranking wasn't an artefact of soft contacts. P-ae394887 and P-547508e5 become eligible. G-060cecb0 stays flagged for a real reason: its 2.95 mm window is within 0.04 mm of a grain dimension, so any print error flips that grain's routing. That's a sim-trust flag and a printability warning in one.

**winners.json now:**
1. P-ae394887, plinko, vibrating tool;
2. P-ba5dd6b3, plinko, firmware stroke;
3. P-547508e5, plinko, vibrating tool.

Best per drive: firmware P-ba5dd6b3 (0.929), vibrating tool P-ae394887 (1.000 verified).

**Next:** demo round 3 (running); then the stress test of these winners (reversal time 0.005 / 0.02 s for the firmware one, printer undersize 0.05 / 0.25 mm for all); then round 4.

## demo round 3 (2026-10-25 08:18, auto)

**Tried:** gated: 12 (ce); gated_mid: 10 (ce); plinko: 8 (ce); inserts: 2 (ce). 360 runs, 14 min wall.

**Leader so far:** P-ae394887 (plinko, round 2) rods L1 gap 3.7 (rod 2.6 wide, 1.6 tall) / L2 gap 1.5 (rod 1.8, 2.4), stroke tool sine 48 Hz, 2.2 g (0.24 mm), 20 deg up: robust 0.999 (mean 0.999 +/- 0.000); big (pasta, chickpea) 100% pure / 100% recovered, rice 100% pure / 100% recovered, quinoa 100% pure / 100% recovered; PEN 1/9 (clr 0.26, pen 0.153).

**Screen results this round (8 s, progress score), best per family:**

- gated: best G-cb487448 screen robust 0.667; median 0.351; failures in 0 of 12 candidates
- gated_mid: best G-a1ecf9bb screen robust 0.900; median 0.472; failures in 0 of 10 candidates
- plinko: best P-fdf86953 screen robust 0.930; median 0.900; failures in 0 of 8 candidates
- inserts: best I-062c2244 screen robust 0.778; median 0.712; failures in 0 of 2 candidates

**Why the losers failed** (particles per run, over this round's screened candidates in the bottom half of each family; the most common modes):

- gated: quinoa: held upstream -> L1 on the floor (26.7 in 6 cands); rice: held upstream -> L1 on the floor (23.2 in 6 cands); rice: held upstream -> L1 at the gate (within 10 mm) (3.8 in 6 cands); quinoa: held upstream -> L1 at the gate (within 10 mm) (1.3 in 6 cands); quinoa: held upstream -> L2 on the floor (1.1 in 6 cands); quinoa: held upstream -> L2 at the gate (within 10 mm) (0.6 in 6 cands)
- gated_mid: rice: held upstream -> L1 on the floor (12.2 in 5 cands); quinoa: held upstream -> L2 in the drop slot (9.8 in 5 cands); rice: held upstream -> L1 at the gate (within 10 mm) (6.4 in 5 cands); quinoa: held upstream -> L1 on the floor (5.9 in 4 cands); quinoa: held upstream -> L2 on the ledge beside the slot (2.8 in 5 cands); rice: leaked downstream -> catch (4.4 in 3 cands)
- plinko: quinoa: held upstream -> layer_2_rods (2.1 in 4 cands); rice: leaked downstream -> layer_3_catch (2.6 in 3 cands); quinoa: held upstream -> layer_1_rods (1.3 in 4 cands); rice: held upstream -> layer_1_rods (0.3 in 1 cands)
- inserts: quinoa: held upstream -> on_h1p75b1p15 (13.9 in 1 cands); quinoa: held upstream -> on_h5p05b1p55 (8.1 in 1 cands); rice: held upstream -> on_h5p05b1p55 (5.2 in 1 cands); rice: leaked downstream -> catch (0.3 in 1 cands); quinoa: between -> in the floor of on_h1p75b1p15 (0.1 in 1 cands)

**Leaders' remaining losses** (full runs, top 3):

- P-ae394887: none
- P-668db784: none
- G-a1ecf9bb: none

**Parameters at a bound among each family's elite** (the range may be too narrow):

- gated: k1 w 0.22/t 0.78, drive firmware 0.71/tool 0.29, angle low (6.56)
- gated_mid: k1 w 0.46/t 0.54, drive firmware 0.14/tool 0.86
- plinko: drive firmware 0.61/tool 0.39, angle low (6.89)
- inserts: drive firmware 0.86/tool 0.14, accel low (1.05), angle low (1.04)

**Next hypothesis (auto):** the leader's near-size results are flagged (overlap vs clearance): check it at a smaller dt or stiffer contacts before trusting it


## demo round 3: reading (notes, 2026-10-25 08:25)

**The gated container is a winner again: the unflipped mid-slot tower with an angled vibration.** G-a1ecf9bb scores **0.985**, every class 100% pure and recovered in all 9 runs, no jams, no flags (gate overlap 0.090 mm against a 0.24 mm clearance), t90 7.1 s. It is winner #2.
- **Strips:** L1 tunnel t3.5, L2 tunnel t1.6, both tunnels 5.0 wide, tooth 0.8. That is exactly bambu's two-line minimum; the elite pushes the tooth thin to fit more openings.
- **Floor:** 2.7 deg.
- **L1 gate:** at x 22.2 with an 8.1 mm drop slot, then the wedge. L2 is the standard container, and the levels are **not** flipped.
- **Stroke:** sine 48 Hz, 3.7 g (0.40 mm), 30 deg up.

Two structural steps got here: the README's gated container (-0.07), then the unflipped mid-slot layout (useless on the firmware stroke), then the angled throw that layout was built for. Both L1 and L2 cut by thickness (tunnels). That matches gatecalc's L1 pick and the elite's 78-85% tunnel share since round 0: a width gap lets pasta roll through on edge.

**For the bambu session: this winner needs new CAD before it can be built** (`cad.buildable_with_todays_cad: false`). `gated_container.py` needs three things:
- a per-container `GATE_X`, here L1 22.2 and L2 53 as today;
- a drop slot `slot` mm long from the strip's downstream face (8.1 for L1), instead of always ending at OPEN_X;
- beyond L1's slot, a solid wedge to the +X wall, rising 30 deg from a 0.4 mm lip and capped 2 mm under the wall top.

The tower is built without the 180 deg flip. The sim geometry is `designs_gated.py` with `gx=22.2/53,slot=8.1/7,flip=0`. The strip and its rails must stay clear of the pull tabs (|x| >= 13.15). Until then, winners #1 and #3 (plinko) and the firmware-stroke plinko (best per drive) build with today's scripts.

**Losers (auto section, read; the location labels were fixed this round).**
- **gated (flipped):** 23-27 grains still on L1's floor. Its elite stays firmware-heavy and never gets a working throw.
- **gated_mid** bottom half: rice held at or before L1 (12 + 6 per run), quinoa held on L2's floor (10 per run, previously mislabelled "in the drop slot": `locate()` used L1's gate position for every level), and some rice leaking to the catch. That's wrong strokes and gap sizes, the cross-entropy spread.
- **plinko:** the same small rice-leak / quinoa-hold trade (about 2 per run).

**Next hypothesis.** The top 3 are all vibrating-tool designs, and two are verified clean. What's left to learn is robustness: does the ranking hold if the printer makes openings 0.1 mm tighter or looser, or if the stage reverses faster or slower? The stress test is running now on the winners, the best per drive and the references. After it: round 4, with the stacked demo rig on its up-and-down stroke as a reference.

## Stress test, a scoring bug, and the winners rule (notes, 2026-10-25 09:00)

**Bug (mine, fixed).** `summarize()` used the strict score only when the fidelity was literally `full`. The stress variants (`us*`, `ramp*`) and `verify`'s stiff reruns fell through to the screen's *progress* score. It showed up as the README gated reference scoring -0.07 on its standard runs but about 0.43 under every stress variant, although the raw counts were the same in both: about 10-15 rice on L2 and most quinoa still on L1 at 30 s. All stress and verification numbers were recomputed from the cached runs with the strict score; no reruns were needed. The verification verdicts don't change: P-ae394887 is 0.999 at stiff contacts (reported as 1.000 before), clean.

**Stress results (strict score, 3 friction sets x 3 seeds, 30 s each).** Undersize: openings printed 0.05 mm small (looser than assumed) or 0.25 mm (tighter). Ramp: stage reversal 0.005 s or 0.02 s, firmware stroke only.

| design | as ranked | undersize 0.05 / 0.25 | ramp 0.005 / 0.02 | worst |
|---|---|---|---|---|
| P-ae394887 plinko 3.7 / 1.5, sine 48 Hz | 0.999 | 0.978 / 0.997 | - | **0.978** |
| G-a1ecf9bb gated_mid, sine 48 Hz 30 deg | 0.985 | 0.925 / 0.965 | - | **0.925** |
| P-668db784 plinko 3.5 / 1.6, sine 14 Hz | 0.998 | 0.937 / 0.997 | - | 0.937 (still flagged) |
| P-fdf86953 plinko 5.1 / 1.7, sine 50 Hz | 0.937 | **0.650** / 0.977 | - | **0.650** |
| P-ba5dd6b3 plinko 5.6 / 1.6, firmware | 0.929 | 0.930 / 0.870 | 0.971 / 0.892 | 0.870 |
| repo plinko 5.0 / 1.4, firmware | 0.670 | 0.799 / 0.485 | 0.934 / 0.530 | 0.485 |
| repo inserts 5 / 2, firmware | 0.714 | 0.599 / 0.710 | 0.729 / 0.655 | 0.599 |
| today's mesh | 0.523 | 0.523 / 0.523 | 0.518 / 0.522 | 0.518 |

What it says:
1. The top plinko and the gated_mid tower hold up within 0.1 mm of print error.
2. P-fdf86953 doesn't: with its 1.7 mm L2 gap printed 0.1 mm wider than assumed, rice leaks to the catch (0.65). It would have been a bad print.
3. The firmware winner is moderately sensitive to both unknowns (0.87-0.97).
4. The repo's own plinko is very sensitive (0.49-0.93): its 1.4 mm gap holds quinoa if the printer runs tight.

**Winners rule refinement (after seeing results; recorded here).** Winners now rank by the **worst** robust score over every check run on the design: friction x seeds, the stiff rerun, and the stress variants. The brief offers the worst case as a ranking key, and the point of the stress test was to avoid printing a design that only works if the printer hits its assumed size. It demotes P-fdf86953; it doesn't promote any particular design. A design that hasn't been stress-tested can rank above one that has, simply because it hasn't been tested yet. `winners.json` says which are `stress_tested`, and the next step stresses the top 6 (all current winners and the best per drive) so the final winners are compared fairly.

## demo round 4 (2026-10-25 08:59, auto)

**Tried:** inserts: 3 (baseline, ce); gated: 12 (ce); gated_mid: 10 (ce); plinko: 8 (ce). 378 runs, 14 min wall.

**Leader so far:** P-ae394887 (plinko, round 2) rods L1 gap 3.7 (rod 2.6 wide, 1.6 tall) / L2 gap 1.5 (rod 1.8, 2.4), stroke tool sine 48 Hz, 2.2 g (0.24 mm), 20 deg up: robust 0.999 (mean 0.999 +/- 0.000); big (pasta, chickpea) 100% pure / 100% recovered, rice 100% pure / 100% recovered, quinoa 100% pure / 100% recovered; PEN 1/9 (clr 0.26, pen 0.153).

**Screen results this round (8 s, progress score), best per family:**

- inserts: best I-34e64bea screen robust 0.775; median 0.649; failures in 0 of 3 candidates
- gated: best G-7461ca86 screen robust 0.667; median 0.347; failures in 0 of 12 candidates
- gated_mid: best G-fc7ba1b5 screen robust 0.876; median 0.677; failures in 0 of 10 candidates
- plinko: best P-7dd9222c screen robust 1.000; median 0.880; failures in 0 of 8 candidates

**Why the losers failed** (particles per run, over this round's screened candidates in the bottom half of each family; the most common modes):

- inserts: quinoa: held upstream -> on_h1p65b1p15 (12.9 in 1 cands); rice: leaked downstream -> catch (10.2 in 1 cands); quinoa: held upstream -> on_h4p65b1p35 (9.3 in 1 cands); rice: held upstream -> on_h4p65b1p35 (6.7 in 1 cands); quinoa: held upstream -> on_h1p85b1p15 (0.7 in 1 cands); quinoa: held upstream -> on_h4p85b1p35 (0.1 in 1 cands)
- gated: quinoa: held upstream -> L1 on the floor (26.8 in 6 cands); rice: held upstream -> L1 on the floor (22.2 in 6 cands); rice: held upstream -> L1 at the gate (within 10 mm) (4.0 in 6 cands); quinoa: held upstream -> L1 at the gate (within 10 mm) (1.1 in 6 cands); quinoa: held upstream -> L2 on the floor (1.2 in 5 cands); quinoa: held upstream -> L2 at the gate (within 10 mm) (1.0 in 5 cands)
- gated_mid: rice: held upstream -> L1 on the floor (8.1 in 5 cands); quinoa: held upstream -> L2 on the floor (12.6 in 3 cands); quinoa: held upstream -> L2 at the gate (within 10 mm) (9.0 in 4 cands); quinoa: held upstream -> L1 on the floor (6.5 in 5 cands); rice: leaked downstream -> catch (6.2 in 4 cands); rice: held upstream -> L1 at the gate (within 10 mm) (2.6 in 5 cands)
- plinko: quinoa: held upstream -> layer_2_rods (5.6 in 3 cands); rice: held upstream -> layer_1_rods (4.0 in 3 cands); rice: leaked downstream -> layer_3_catch (7.6 in 1 cands); quinoa: held upstream -> layer_1_rods (1.9 in 4 cands); rice: between -> in the floor of layer_1_rods (0.1 in 1 cands)

**Leaders' remaining losses** (full runs, top 3):

- P-ae394887: none
- P-7dd9222c: none
- P-668db784: none

**Parameters at a bound among each family's elite** (the range may be too narrow):

- inserts: drive firmware 0.86/tool 0.14, accel low (1.08), angle low (1.70)
- gated: k1 w 0.23/t 0.77, drive firmware 0.63/tool 0.37, angle low (7.74)
- gated_mid: k1 w 0.38/t 0.62, drive firmware 0.14/tool 0.86
- plinko: drive firmware 0.57/tool 0.43, angle low (7.94)

**Next hypothesis (auto):** the leader's near-size results are flagged (overlap vs clearance): check it at a smaller dt or stiffer contacts before trusting it


## demo round 4: reading (notes, 2026-10-25 09:10)

**New:**
- **P-7dd9222c**, plinko 3.6 / 1.6, sine 20 Hz at 2.1 g along the tray (0 deg): every one of 684 particles in its bin, t90 0.4 s. It is flagged in 5 of 9 runs (gate overlap 0.218 mm against a 0.12 threshold), so it is queued for `verify`. Its stroke is almost the demo rig's assumed tool motion (20 Hz, 2 g), only horizontal.
- **P-6e03ce14**, plinko 4.1 / 1.6 on the **firmware** stroke (9 mm at 50 mm/s), with the stage tilted 25 deg up: **0.958**, clean (gate overlap 0.084 / 0.24 clearance), quinoa 266/270 in the catch, t90 1.6 s. This is the new best for BioKEA's stage. The 25 deg tilt is a mounting change, not a firmware change. A firmware-only candidate at 0 deg (P-ba5dd6b3, 0.929; 5 deg) stays on the board.

**The actual demo rig** (main's 06:20 correction): stacked printed 5 mm / 2 mm trays (`inserts:5mm,2mm`, as printed), shaken up and down (sine 20 Hz, 2 g, 90 deg; assumed tool motion). Robust **0.460**, flagged 9/9, with 2 particles beyond geometry:
- pasta and chickpea are 100% on the 5 mm tray;
- **rice: 164 of 270 on the 2 mm tray, 106 (39%) fell into the catch**;
- quinoa: 100% in the catch, but that bin is 28% rice.

Rice's corner-to-corner diagonal (1.86 mm) is 0.01 mm over the as-printed 1.85 mm hole, and vertical shaking keeps tipping it into the holes. So the rig sorts pasta from the rest perfectly, but can't separate rice from quinoa reliably. On the firmware stroke along the tray, the same trays score 0.714, also flagged. **For the demo:** keep the rig's job to pasta vs rice (the 5 mm tray), or replace the 2 mm tray with plinko rods at 1.5-1.6 mm (the winners' L2).

**Losers.**
- **gated (flipped):** unchanged, grain stays on L1's floor.
- **gated_mid** bottom half: quinoa held on L2's floor or at L2's gate (13 + 9 per run), rice held on L1 (8), rice leaking (6). It's tuning noise around the leader.
- **plinko:** the usual gap trade.

**Next.** Verify P-7dd9222c and anything else flagged in the top 4; one more demo round; stress the top 6 again; replays of the final winners; then insect round 1 with whatever time is left.

## Verification of P-7dd9222c (notes, 2026-10-25 09:15)

P-7dd9222c (plinko 3.6 / 1.6, sine 20 Hz at 2.1 g along the tray) **stays flagged** at stiffer contacts: 5 of 9 runs, and the peak gate overlap went *up*, from 0.218 to 0.306 mm (threshold 0.12). The 1.3 mm amplitude throws grains hard into the rods, and the peak sink at impact comes from impact speed, not contact softness. The score didn't move (0.999 at both settings, every particle in its bin), so the deep contacts aren't changing routing. By the rule it isn't a winner. It's still the design to try if the demo rig's tool really runs near 20 Hz and 2 g, but only after the bench confirms it.

A design-pipeline fix went in at the same time. Every step now recomputes all summaries from the run cache when it starts, so none decides what to stress, verify or replay from stale saved numbers. That staleness is why winner #2 (P-547508e5) and the firmware pick (P-cbe7dbec) hadn't been stress-tested; they are running now.

## Every winner stress-tested; a rule for the L2 rod gap (notes, 2026-10-25 09:20)

The two designs that hadn't been stress-tested failed it:
- P-547508e5, plinko 3.1 / **1.7**: worst 0.630;
- P-cbe7dbec, plinko 5.1 / **1.7**, firmware: worst 0.654.

In both, the loose-printer variant (openings 0.05 mm under nominal instead of 0.15) lets rice through layer 2. The firmware one also loses ground at a 0.02 s stroke reversal (0.681).

**Rule for printing: plinko layer-2 gap 1.5-1.6 mm nominal.** Every stress-tested plinko with a 1.7 mm gap drops to about 0.63-0.65 when the printer runs 0.1 mm loose. With 1.5-1.6 mm the worst cases are 0.87-0.98. Sim rice is 1.7 mm thick (+/- 7%). The gap has to stay under rice's thin tail even when it prints loose, while staying 0.3+ mm over quinoa (1.1 mm). Measuring real rice and the printer's undersize (`hole_gauge.py`) would pin this down.

**winners.json, all stress-tested, ranked by worst case:**
1. P-ae394887, plinko 3.7 / 1.5, vibrating tool 48 Hz 2.2 g 20 deg: 0.999 (worst 0.978);
2. G-a1ecf9bb, gated_mid, tunnels 3.5 / 1.6, vibrating tool 48 Hz 3.7 g 30 deg: 0.985 (worst 0.925);
3. P-ba5dd6b3, plinko 5.6 / 1.6, **firmware** 9.5 mm at 47 mm/s, 5 deg up: 0.929 (worst 0.870). Also the best per drive for BioKEA's stage.

P-6e03ce14 (plinko 4.1 / 1.6, firmware at 25 deg) scores 0.958 but falls to 0.826 at a 0.02 s reversal, so it ranks just below.

## Design invariant from the user: a stack of baskets (notes, 2026-10-25 09:30)

The user restated what the sorter *is*: a stack of baskets. Specimens fall through the levels, and everything of one size class ends up on **one level's removable tray**. That tray is then lifted out by its side extensions (the pull tabs) and placed straight into the next step.

This is a hard constraint on every family, current and future:
1. **One class per level, on a removable tray.** Each bin is a tray that lifts out whole. In the sim, a class's bin is exactly one level's zone. The catch at the bottom is a tray as well (plinko's `layer_3_catch`, the holder-tower's catch pan).
2. **Pull tabs stay, and stay reachable.** No family may drop or bury them.
   - The insert and gated-container tabs sit in the holder's finger notches; bambu cut the gated container's TAB_TOP to 21 mm so the tabs clear the box above.
   - Plinko's tabs rise above the rim through slots in the layers above.
   - `gated_mid` keeps its strip and rails out of the tab zone (|x| >= 13.15 mm).
3. **A specimen has to sit loose on its tray, not wedged in its floor.** A grain stuck in rods, holes or mesh won't tip out when the tray is moved to the next step. The sim already counts any particle whose centre is inside a tray's floor, a strip, a slot or a ledge as **jammed** ("between"). That costs it its class's recovery plus a jam penalty, so the score favours trays you can pick up and empty cleanly.

All three current winners meet this: **0 jammed and 0 lost in all 9 runs each**.
- P-ae394887, plinko: pasta and chickpea 144/144 on layer 1, rice 270/270 on layer 2, quinoa 270/270 on the catch tray.
- G-a1ecf9bb, gated_mid: the same counts in L1 / L2 / catch.
- P-ba5dd6b3, plinko on the firmware stroke: 144 / 270 / 261 with 9 quinoa held a level up, none jammed.

Today's glued mesh, by contrast, jams 3.2 grains and 17 insects per run in its mesh. Those are exactly the specimens that don't come out when the tray is lifted.

## demo round 5 (2026-10-25 09:28, auto)

**Tried:** gated: 12 (ce); gated_mid: 10 (ce); plinko: 8 (ce); inserts: 2 (ce). 360 runs, 13 min wall.

**Leader so far:** P-b192da7c (plinko, round 5) rods L1 gap 4.7 (rod 2.6 wide, 2.2 tall) / L2 gap 1.6 (rod 2.3, 3.2), stroke tool sine 37 Hz, 2.1 g (0.38 mm), 25 deg up: robust 1.000 (mean 1.000 +/- 0.000); big (pasta, chickpea) 100% pure / 100% recovered, rice 100% pure / 100% recovered, quinoa 100% pure / 100% recovered; ok.

**Screen results this round (8 s, progress score), best per family:**

- gated: best G-d726c2e8 screen robust 0.792; median 0.341; failures in 0 of 12 candidates
- gated_mid: best G-ebdca794 screen robust 0.802; median 0.416; failures in 0 of 10 candidates
- plinko: best P-b192da7c screen robust 1.000; median 0.898; failures in 0 of 8 candidates
- inserts: best I-111ae925 screen robust 0.808; median 0.751; failures in 0 of 2 candidates

**Why the losers failed** (particles per run, over this round's screened candidates in the bottom half of each family; the most common modes):

- gated: quinoa: held upstream -> L1 on the floor (27.4 in 6 cands); rice: held upstream -> L1 on the floor (23.1 in 6 cands); rice: held upstream -> L1 at the gate (within 10 mm) (4.4 in 6 cands); quinoa: held upstream -> L1 at the gate (within 10 mm) (1.2 in 6 cands); quinoa: held upstream -> L2 on the floor (0.8 in 5 cands); rice: between -> L1 in the strip (0.6 in 6 cands)
- gated_mid: rice: held upstream -> L1 on the floor (13.4 in 5 cands); quinoa: held upstream -> L1 on the floor (12.8 in 5 cands); rice: held upstream -> L1 at the gate (within 10 mm) (9.7 in 4 cands); quinoa: held upstream -> L2 on the floor (7.1 in 4 cands); rice: leaked downstream -> catch (7.9 in 3 cands); quinoa: held upstream -> L2 at the gate (within 10 mm) (4.0 in 5 cands)
- plinko: quinoa: held upstream -> layer_2_rods (4.3 in 4 cands); quinoa: held upstream -> layer_1_rods (2.1 in 4 cands); rice: leaked downstream -> layer_3_catch (0.6 in 3 cands); rice: held upstream -> layer_1_rods (0.4 in 3 cands)
- inserts: quinoa: held upstream -> on_h1p75b1p15 (9.7 in 1 cands); quinoa: held upstream -> on_h4p75b1p45 (8.2 in 1 cands); rice: held upstream -> on_h4p75b1p45 (4.9 in 1 cands); quinoa: between -> in the floor of on_h4p75b1p45 (0.1 in 1 cands); rice: between -> in the floor of on_h4p75b1p45 (0.1 in 1 cands)

**Leaders' remaining losses** (full runs, top 3):

- P-b192da7c: none
- P-ae394887: none
- P-7dd9222c: none

**Parameters at a bound among each family's elite** (the range may be too narrow):

- gated: k1 w 0.26/t 0.74, drive firmware 0.53/tool 0.47, angle low (8.35)
- gated_mid: k1 w 0.30/t 0.70, drive firmware 0.14/tool 0.86
- plinko: drive firmware 0.56/tool 0.44, angle low (8.78)
- inserts: drive firmware 0.86/tool 0.14, accel low (1.08), angle low (1.74)

**Next hypothesis (auto):** the leader sorts cleanly; refine for robustness and throughput.


## demo round 5: reading (notes, 2026-10-25 09:40)

**New leader: P-b192da7c, plinko 4.7 / 1.6**, sine 37 Hz at 2.1 g, 25 deg up: **1.000**, no flags (gate overlap 0.084 / 0.24 clearance), 684 / 684 particles on their own trays, t90 0.2 s. It is in the stress test running now.

**Today's gated tower works too, on a strong horizontal vibration.** G-d726c2e8 is the standard, **flipped** gated tower that `gated_container.py` builds today:
- tunnels t4.4 / t1.8, tunnel width 8 (as today), tooth 1.1, slot 6, 2.4 deg floor;
- sine 26 Hz at 3.8 g (1.4 mm), **along the tray** (0 deg);
- score 0.946: rice 268/270 and quinoa 269/270 in their bins, t90 11 s.

A symmetric shake along the tray has no preferred direction, so flipping the levels costs nothing. At 3.8 g grains skate freely and the 2.4 deg slope walks them to the gates. The firmware's ~1 g jolts can't do that, and an angled throw conveys a flipped L2 the wrong way. So the flipped/unflipped question is really a stroke question: an **angled throw needs the unflipped mid-slot tower; a strong flat shake works with today's tower.**

Caveat: it is flagged in 9 of 9 runs. Its L2 tunnel is 1.65 mm as printed, 0.04 mm under the rice's thickness, the same near-size fragility as the 1.7 mm plinko gaps. It's queued for `verify` and the stress test. Expect it to fail the loose-printer variant unless the L2 tunnel comes down to t1.6-1.7 nominal.

**Losers:**
- **gated:** the usual firmware-stroke transport failure (23-27 grains on L1's floor).
- **gated_mid:** rice held at L1 and quinoa on L2 at the wrong strokes.
- **plinko:** quinoa held on layer 2 when the gap runs tight.

**Next:** verify and stress the new ones (queued), replays of the winners, then insect round 1 if time remains.

## Verification of today's flipped tower on a flat shake (notes, 2026-10-25 09:50)

G-d726c2e8, the standard flipped gated tower on a 26 Hz, 3.8 g shake along the tray, **stays flagged** at stiffer contacts: 7 of 9 runs, overlap 0.059 mm, but its clearance is only 0.04 mm. Its score holds (0.946, 0.937 stiff), so the result isn't a soft-contact artefact. The flag is a real near-size warning: the L2 tunnel prints at 1.65 mm against 1.7 mm rice. **Next hypothesis:** the same tower and shake with a safer L2 tunnel (t1.6-1.7 nominal) should keep the score and lose the flag. The gated family's cross-entropy now centres on this design, so round 6 samples that neighbourhood. Insect round 1 is dropped from the queue: it doesn't fit before 10:50, and the insect classes are capped by structure, not tuning (insect round 0 notes).

## demo round 6 (2026-10-25 09:55, auto)

**Tried:** gated: 12 (ce); gated_mid: 10 (ce); plinko: 8 (ce); inserts: 2 (ce). 360 runs, 13 min wall.

**Leader so far:** P-b192da7c (plinko, round 5) rods L1 gap 4.7 (rod 2.6 wide, 2.2 tall) / L2 gap 1.6 (rod 2.3, 3.2), stroke tool sine 37 Hz, 2.1 g (0.38 mm), 25 deg up: robust 1.000 (mean 1.000 +/- 0.000); big (pasta, chickpea) 100% pure / 100% recovered, rice 100% pure / 100% recovered, quinoa 100% pure / 100% recovered; ok.

**Screen results this round (8 s, progress score), best per family:**

- gated: best G-e5083752 screen robust 0.829; median 0.345; failures in 0 of 12 candidates
- gated_mid: best G-6525d37f screen robust 0.814; median 0.551; failures in 0 of 10 candidates
- plinko: best P-e6f1f8db screen robust 1.000; median 0.886; failures in 0 of 8 candidates
- inserts: best I-02a7cd44 screen robust 0.793; median 0.785; failures in 0 of 2 candidates

**Why the losers failed** (particles per run, over this round's screened candidates in the bottom half of each family; the most common modes):

- gated: quinoa: held upstream -> L1 on the floor (27.8 in 6 cands); rice: held upstream -> L1 on the floor (26.0 in 6 cands); rice: held upstream -> L1 at the gate (within 10 mm) (1.8 in 6 cands); quinoa: held upstream -> L1 at the gate (within 10 mm) (1.2 in 5 cands); quinoa: held upstream -> L2 on the floor (0.9 in 6 cands); rice: between -> L1 in the strip (0.3 in 5 cands)
- gated_mid: quinoa: held upstream -> L1 on the floor (17.3 in 3 cands); rice: held upstream -> L1 on the floor (9.4 in 4 cands); rice: held upstream -> L1 at the gate (within 10 mm) (6.7 in 5 cands); rice: leaked downstream -> catch (10.5 in 2 cands); quinoa: held upstream -> L2 at the gate (within 10 mm) (2.7 in 5 cands); quinoa: held upstream -> L2 on the floor (3.3 in 3 cands)
- plinko: quinoa: held upstream -> layer_2_rods (4.8 in 4 cands); quinoa: held upstream -> layer_1_rods (4.1 in 4 cands); rice: held upstream -> layer_1_rods (0.9 in 3 cands); rice: leaked downstream -> layer_3_catch (1.0 in 2 cands)
- inserts: quinoa: held upstream -> on_h1p75b1p15 (9.1 in 1 cands); quinoa: held upstream -> on_h5p15b1p35 (4.9 in 1 cands); rice: held upstream -> on_h5p15b1p35 (2.0 in 1 cands); rice: leaked downstream -> catch (0.2 in 1 cands)

**Leaders' remaining losses** (full runs, top 3):

- P-b192da7c: none
- P-e6f1f8db: none
- P-ae394887: none

**Parameters at a bound among each family's elite** (the range may be too narrow):

- gated: k1 w 0.26/t 0.74, drive firmware 0.47/tool 0.53, angle low (8.68)
- gated_mid: k1 w 0.25/t 0.75, drive firmware 0.13/tool 0.87
- plinko: drive firmware 0.52/tool 0.48
- inserts: drive firmware 0.86/tool 0.14, accel low (1.08), angle low (1.67)

**Next hypothesis (auto):** the leader sorts cleanly; refine for robustness and throughput.


## demo round 6: the hypothesis holds; today's gated tower is a clean winner (notes, 2026-10-25 10:00)

**Hypothesis (09:50):** today's flipped tower on a strong flat shake, with a safer L2 tunnel, keeps its score and loses the flag. **Confirmed.**

**G-e5083752**, the standard flipped gated tower, **buildable with today's `gated_container.py`**:
- **CAD:** constants FLOOR_SLOPE_DEG 3.1, TUNNEL_W 8.3, TOOTH 1.7, GATE_X 52.8 (7.2 mm slot), plus two new strips, `gate_t5p3` (L1) and `gate_t1p6` (L2). No new geometry.
- **Stroke:** sine 38 Hz at 4.8 g (0.83 mm), along the tray.
- **Result:** robust **0.950, no flags** (gate overlap 0.091 mm against a 0.24 clearance). Pasta and chickpea 144/144 on L1, rice 270/270 on L2, quinoa 268/270 on the catch, 0 jammed, t90 10 s.

L2's t1.6 prints at 1.45 mm: 0.25 mm under rice, 0.35 mm over quinoa. That's the same safe window as the plinko layer-2 rule.

**Why the losers failed this round.** gated_mid candidates at steep throws (60-65 deg) bounce grains instead of conveying them (0.61-0.85). A flipped tower with a w5.2 gap at L1 leaks pasta on edge (0.62). Inserts are still flagged everywhere.

It's provisionally winner #2 (stress test queued next: printer undersize +/- 0.1 mm). If it holds, **all three styles the optimizer explored have a working, stress-tested sorter**:
- plinko rods;
- today's gated tower on a flat shake;
- the mid-slot gated tower on an angled throw.

All three are stacks of removable trays, one class per tray.

## The rig rocks: a seesaw drive (notes, 2026-10-25 10:10)

**From the user (10:05-10:15), with a photo of the rig.** The trays are separate levels hung one above another in an aluminium frame. Each section drops into the next tray. Each tray is attached at its mid-points to the motor, which rocks it **side to side like a seesaw** (the holder's mounting tab at the middle of its +X end, `frame_holder.py`). That is the motion of the machine as it stands, so it's the quickest thing to improve. The shaking results above stay valid, for a rig that shakes.

**What the optimizer did until now.** Every stroke was a translation: the firmware stage, or a vibrating tool, at any angle. `sorter.py` only translates the tray (a uniform pseudo-force).

**New drive, `rock`** (in `optimize.py`'s run wrapper, without touching `sorter.py`):
1. **Tilt.** Gravity is rotated into the tilted tray frame every step.
2. **Rotating-frame forces.** Every particle also gets m(-alpha x r - w x (w x r) - 2 w x v), with r measured in plan from the tray centre, where the pivot axis runs. This includes the jolt from the angular acceleration at each hard reversal, so the tray ends jerk while the middle doesn't.
3. **Profile.** The tilt follows the firmware's constant-speed profile with hard reversals, starting level, between +/- `rock_deg`, `rock_period` s per cycle.
4. **Search space.** The pivot axis is a categorical: x = the tray's long axis (the width tips side to side; this matches "attached at the mid points") or y = its short axis (the ends tip). The amplitude is 2-20 deg and the period 0.4-6 s. All three are unmeasured.

**Checked (executed, plinko 3.7 / 1.5, 2 s, mu 0.4):** rocking about the long axis put 27/30 rice on its tray against 19/30 with no motion; about the short axis, 23/30. The tilt traces as expected: gravity's x component reaches 1703 mm/s^2 = g sin 10 deg. A first smoke test showed identical counts for every motion. That was my test, not the physics: three runs in one process each wrapped the previous run's step. `run_job` now always starts from MuJoCo's own `mj_step`, and `replay` applies the rocking as well.

**Not modelled yet.** The levels hang apart in the frame rather than rim on rim, so the drop between trays is longer than in the sim's tower. The pivot height relative to each tray floor isn't known either. Both are assumptions to check against the rig.

**Next.** A demo round with every new candidate and reference on the seesaw drive (`run --drive rock`). `winners.json` gets a "seesaw" entry in its best-per-drive list: the design for the rig's current motor.

## demo round 7 (2026-10-25 10:54, auto)

**Tried:** gated: 22 (baseline, ce, lhs); plinko: 17 (baseline, ce, lhs); inserts: 7 (baseline, ce, lhs); current: 1 (current); demo_rig: 1 (current); gated_mid: 16 (ce, lhs). 756 runs, 43 min wall.

**Leader so far:** P-b192da7c (plinko, round 5) rods L1 gap 4.7 (rod 2.6 wide, 2.2 tall) / L2 gap 1.6 (rod 2.3, 3.2), stroke tool sine 37 Hz, 2.1 g (0.38 mm), 25 deg up: robust 1.000 (mean 1.000 +/- 0.000); big (pasta, chickpea) 100% pure / 100% recovered, rice 100% pure / 100% recovered, quinoa 100% pure / 100% recovered; ok.

**Screen results this round (8 s, progress score), best per family:**

- gated: best G-2b33c311 screen robust 0.411; median 0.338; failures in 0 of 22 candidates
- plinko: best P-59cc0bf9 screen robust 0.919; median 0.694; failures in 0 of 17 candidates
- inserts: best I-907f0f4c screen robust 0.657; median 0.592; failures in 0 of 7 candidates
- current: best C-1f16dae6 screen robust 0.554; median 0.554; failures in 0 of 1 candidates
- demo_rig: best D-ef26c8c7 screen robust 0.804; median 0.804; failures in 0 of 1 candidates
- gated_mid: best G-4947dd42 screen robust 0.465; median 0.333; failures in 0 of 16 candidates

**Why the losers failed** (particles per run, over this round's screened candidates in the bottom half of each family; the most common modes):

- gated: quinoa: held upstream -> L1 on the floor (27.9 in 11 cands); rice: held upstream -> L1 on the floor (26.0 in 11 cands); rice: held upstream -> L1 at the gate (within 10 mm) (2.7 in 11 cands); quinoa: held upstream -> L1 at the gate (within 10 mm) (1.2 in 9 cands); quinoa: held upstream -> L2 on the floor (1.0 in 10 cands); rice: between -> L1 in the strip (0.2 in 5 cands)
- plinko: quinoa: held upstream -> layer_2_rods (12.0 in 9 cands); quinoa: held upstream -> layer_1_rods (8.8 in 9 cands); rice: held upstream -> layer_1_rods (6.8 in 9 cands); rice: leaked downstream -> layer_3_catch (6.1 in 3 cands)
- inserts: quinoa: held upstream -> on_h4p85b1p35 (10.1 in 2 cands); rice: held upstream -> on_h3p05b1p55 (17.9 in 1 cands); quinoa: held upstream -> on_h1p85b1p15 (7.2 in 2 cands); rice: held upstream -> on_h4p85b1p35 (6.8 in 2 cands); quinoa: held upstream -> on_h3p95b2p05 (9.9 in 1 cands); quinoa: held upstream -> on_h3p05b1p55 (9.0 in 1 cands)
- current: rice: leaked downstream -> catch (5.8 in 1 cands); rice: between -> in the floor of on_mesh5 (3.6 in 1 cands); quinoa: between -> in the floor of on_mesh5 (3.1 in 1 cands); quinoa: held upstream -> on_mesh2 (1.0 in 1 cands); quinoa: between -> in the floor of on_mesh2 (0.6 in 1 cands); rice: held upstream -> on_mesh5 (0.3 in 1 cands)
- demo_rig: quinoa: held upstream -> on_5mm (9.1 in 1 cands); rice: held upstream -> on_5mm (6.3 in 1 cands)
- gated_mid: quinoa: held upstream -> L1 on the floor (27.6 in 8 cands); rice: held upstream -> L1 on the floor (24.7 in 8 cands); rice: held upstream -> L1 at the gate (within 10 mm) (3.9 in 8 cands); quinoa: held upstream -> L1 at the gate (within 10 mm) (1.3 in 7 cands); quinoa: held upstream -> L2 at the gate (within 10 mm) (0.8 in 7 cands); rice: between -> L1 in the strip (0.5 in 7 cands)

**Leaders' remaining losses** (full runs, top 3):

- P-b192da7c: none
- P-e6f1f8db: none
- P-ae394887: none

**Parameters at a bound among each family's elite** (the range may be too narrow):

- gated: k1 w 0.25/t 0.75, drive firmware 0.38/tool 0.45/rock 0.17, angle low (8.29), rock_axis x 0.36/y 0.64
- plinko: drive firmware 0.41/tool 0.41/rock 0.17, rock_axis x 0.36/y 0.64
- inserts: drive firmware 0.73/tool 0.14/rock 0.13, accel low (1.20), rock_axis x 0.50/y 0.50
- gated_mid: k1 w 0.20/t 0.80, drive firmware 0.13/tool 0.69/rock 0.18, rock_axis x 0.25/y 0.75

**Next hypothesis (auto):** the leader sorts cleanly; refine for robustness and throughput.



## demo round 7: the seesaw (notes, 2026-10-25 10:58)

**Best design for the rig's rocking motor: P-59cc0bf9, plinko rods 3.1 / 1.6 mm (nominal), rocked +/-19 deg about the tray's long axis at 0.4 s per cycle.** Robust 0.835 (mean 0.898 +/- 0.063), no flags, 90% sorted after 3.2 s in 9 of 9 runs. Every big grain and every rice grain ends on its own layer. 90% of the quinoa reaches the catch, and the rest sits on the rice layer (rice purity 92%). It is `winners.json` `best_by_drive` "seesaw". Executed, 3 friction sets x 3 seeds, 30 s. Not stress-tested or verified at stiff contacts: the round ended at the stop time.

**What rocking needs (executed, this round's full runs):**
- **Fast and steep wins.** Ranked: +/-19 deg at 0.4 s about the long axis (0.835); +/-14.5 deg at 0.9 s about the short axis (0.705); +/-11 deg at 0.8 s (0.503); +/-17 deg at 3.4 s (0.471). Slow rocking leaves quinoa on the upper layers.
- **The winner sits at two bounds** (amplitude 19 of 20 deg, period 0.4 of 0.4 s), so the optimum may lie beyond the searched range.
- **The reversal jolts probably carry it.** At 0.4 s per cycle the tray turns at about 190 deg/s and reverses in 0.01 s (assumed, as for the firmware stage). That gives roughly 4 g at the tray ends. So this behaves more like a jolting shaker than a gentle tilt, and the unmeasured reversal time matters again.
- **Today's setups on the default seesaw (+/-10 deg, 1.6 s, long axis):**
  - glued mesh 0.480: 65% of the rice stays on its tray; the rest leaks or wedges in the 5 mm mesh;
  - plinko as in the repo (5.0 / 1.4) 0.408;
  - the demo rig's 5 mm tray alone 0.387;
  - the printed inserts 0.359.
- **Gated designs don't work on a seesaw** (best 0.293). Rice and quinoa stay on L1's floor: 26 and 28 per run in the bottom half. A symmetric tilt has no net push toward the gate, and a gate needs a drive with a direction.

**Caveats (assumed):**
- The pivot axis is taken through each tray's centre at the grain's own height. The real pivot height is unknown.
- The rig's trays hang apart in the frame, so the drops between them are longer than in the sim's stacked box.
- Whether the motor can rock +/-19 deg at 2.5 Hz is unknown. The amplitude and period it can actually do are the next thing to measure.

**Next hypothesis:**
1. Measure the rig's real tilt amplitude, period and pivot axis.
2. Rerun the seesaw search with the range opened past 20 deg and below 0.4 s, if the motor allows it, or pinned to what it does.
3. Stress the winner on reversal time (0.005 / 0.02 s) and printer undersize (+/- 0.1 mm), and verify it at stiff contacts.
4. If the motor is slow, try a plinko with a steeper-sided rod or an asymmetric (sawtooth) floor, so a slow tilt still carries grain over the rods.

**Code note:** commit 4b8f76d's message says ce_update "pads or resets" a categorical whose size changed. It only resets it: a categorical that gained a choice restarts at uniform weights.

**Stop.** The driver stopped at 10:54 (`out/opt/STOP`) after round 7, per the brief. The leaderboard, winners and this log are final for this session.

## Correction: the rig's seesaw axis is y (notes, 2026-10-25 11:05)

**Main's SYSTEM.md section 3 (the user confirmed it at 10:50, commit 9785b73 on main):**
- Each tray tips at its ends, about its own pivot across its middle (axis y), about 20-30 deg either side.
- Neighbouring levels rock in opposite phase.

This overrides my 10:10 reading ("x matches attached at the mid points"). So round 7's winner, P-59cc0bf9 (+/-19 deg about x), rocks the wrong axis. It is not the design for the rig's motor.

**Under the confirmed axis (executed, round 7 full runs):**
- The best is **P-fccdb05e, plinko rods 3.3 / 1.7, +/-14.5 deg at 0.9 s, robust 0.705.** Rice is 93% kept and quinoa 83% through. Gate overlap is flagged in 2 of 9 runs.
- Its layer-2 gap of 1.7 mm breaks the printing rule from the stress test (1.5-1.6 mm).
- So `winners.json` has **no clean seesaw entry** now. The leaderboard's best-per-drive table lists P-fccdb05e, flagged.

**Code (this commit):**
- `RIG_ROCK_AXIS = "y"`: only y-axis runs count as the rig's motor in best-per-drive.
- `ROCK_DEFAULT` is now y, 20 deg.
- `rock_deg` is searched up to 30 deg.

**Not modelled by `rocking()`:**
- **Alternating levels.** It turns every particle in phase, which is right for one box (the plinko layers rock together) but not for a tower of separate trays.
- **Each level hinged in the lab frame.** SYSTEM.md gives this to the new seesaw session (`sim/rocking.py`); its results supersede this round's for multi-tray designs.

**Next:** a y-axis round at 10-30 deg on the seesaw session's model. The x-axis results stay in the log as a record of the search.

## Restart on the alternating seesaw (notes, 2026-10-25 12:40)

**PLAN.md (11:45):** rerun the search on `rocking.py`'s `seesaw:` stroke, where each tray rocks on its own hinge across its middle (axis y) and neighbours run in opposite phase. My `rocking()` wrapper turns every particle in phase, which is wrong for a stack. It stays only for the old `rock` drive.

**New study `seesaw`** (`optimize.py run --study seesaw --families plinko,inserts`):
- Same grains and classes as `demo`.
- The stroke parameters are the seesaw's: `ss_deg` 5-15 deg (the user's default is 10), `ss_period` 0.4-6 s, `ss_shape` constant_speed or sine. The inserts family also searches `pitch` 80-110 mm.
- At +/-15 deg, neighbouring boxes touch at 72 mm pitch with the +X tab (`rocking.py`), and 85 mm leaves 13 mm. A run whose trays touch counts as a failure.
- References, on the default seesaw (+/-10 deg, 2 s, constant speed, 85 mm apart): the demo rig (printed 5 / 2 mm), today's glued mesh, plinko as in the repo, and the demo study's leader P-b192da7c.
- **Plinko is one holder box,** so it rocks as one level on one hinge, all three layers in phase (`one_box_seesaw`, patched in the child process so `rocking.py` stays the seesaw session's). Gated is left out: round 7 showed it can't sort on a symmetric seesaw.
- Screen 10 s, full 30 s, 12 workers.

**Speed fix in `sorter.py` (executed):** a seesaw run was about 30x slower per step than a translation run: plinko took 99 s for 1 s of sim against 3.6 s. The cause:
- Every contact touches a level's hinge DOF.
- The level bodies came after the particles, so MuJoCo's factorization (which eliminates from the last DOF) filled the Newton Hessian in densely.
- The fix puts the level bodies first. That took 5.1 s for the same run, with the same counts to within one grain, and Newton iterations unchanged (about 9 per step).
- CG instead doesn't converge with the levels' 1e10 armature (grains fell through the floor in the test), and PGS took 61 s.
- The recording is unchanged: `pbodies` and `write_recording` skip the level bodies at the front now.

## Breaker layer and the malaise study (notes, 2026-10-25 13:00)

**`sim/designs_breaker.py`:**
- Spec: `breaker:open,bar,pin_d,pin_h,pitch,tip`. The keys, defaults and rounding are `cad/breaker_layer.py`'s, so a winner prints as is.
- Two sim-only keys: `under=5mm+2mm` (the demo rig's trays below) and `tower=85` (box pitch).
- The breaker is a holder box on top, so `rocking.py` rocks it as the top level, alternating with the 5 mm tray.
- The default's grid matches the CAD's: 12 x 8 openings of 8 mm, 77 round pins 2.5 x 12 mm at 9.6 mm.

**`sim/opt_malaise.py` (EXPLORATORY):**
- Search: the six breaker keys, the seesaw (5-15 deg, 0.4-6 s) and its buzz (0-0.4 mm at 40 Hz).
- Score per run: 0.5 break-up (free share and speed) + 0.3 gentleness + 0.2 sort. Robust = mean - sd over the weak / medium / strong bond sets.
- Gentleness is half "never over 5 mN while still in the clump" and half the peak-force p90 on a log scale (1 at 5 mN, 0 at 500 mN). Over the whole run, 98% of the grains pass 5 mN on the CAD default (85 mm drops between levels), so that share can't rank designs.
- 4 s per run (2 cycles at 2 s), dt 0.25 ms: about 3.5 min each on one core. The clump's bonds make Newton's factorization fill in, as the clumps.py docstring says.

**Blocker: insect clumps don't pack (executed, 12:55).** `python clumps.py insect_malaise=40` gives a "diameter" of 75 m with 12 bonds. The same happens with `insect_malaise_lt2` (6.9 m), `insect_malaise_2to6 + _gt6` (43 m, 0 bonds), and `insect_compact + insect_elongate` with debris on the tower (QACC NaN, reset). `insect_compact=20` alone packs (8.9 mm). So the study's clump is the bench-demo **grain surrogate** (rice 30, quinoa 20, pasta 4, leaf 1, twig 2, dirt 6). The real Malaise clump waits for the clump session's fix to `clumps.pack`.

**Seesaw round 0, screen (10 s, seed 0 x 3 friction sets):** nothing sorts well on the seesaw alone. The best is today's glued mesh at 0.48, then plinko at +/-5.5 deg, 3.6 s, sine (0.38), and the demo rig at 0.34. This agrees with the physics session's VERIFY_SEESAW.md: below the ~22 deg at which grains slide, quinoa rides the 5 mm tray's ribs. **Round 1 adds `vib_mm`** (0-0.5 mm at 40 Hz, straight up), after the seesaw session saw 0.3 mm clear the 5 mm tray. It also adds references: the demo rig + 0.3 mm, and bambu's ribs-across inserts in the seesaw holder, with and without the buzz.

**Memory:** at 12:53 Windows ran low (main's note). For about 5 minutes my two drivers overlapped at about 20 workers. Since 12:58 it's 12 in all: seesaw 4, malaise 8.

## malaise round 0 (EXPLORATORY, 2026-10-25 13:03, auto)

**Tried:** 15 candidates (baseline, lhs), 45 runs, 9 min wall.

**Leader:** B-32a7c82c: grid 11.4 mm (bars 2.3), pins 1.4 x 6.8 mm round every ~8 mm; seesaw +/-12 deg, 2.5 s + 0.35 mm buzz at 40 Hz. Robust 0.638 (mean 0.726); free 97%, gentle 29%, sort 85%, largest cluster 1.7.

- reference NO BREAKER: robust 0.217; free 31%, gentle 76%, sort 17%
- reference cad/breaker_layer.py default (open 8, pins 2.5 x 12 every 10, round) on the default seesaw: robust 0.287; free 65%, gentle 46%, sort 22%
- reference the CAD default breaker, default seesaw + 0.3 mm buzz at 40 Hz (1.9 g, the tool's): robust 0.479; free 85%, gentle 35%, sort 75%

**Why the losers lost:**

- free at the end: top half 0.86, bottom half 0.68
- gentleness: top half 0.33, bottom half 0.42
- in the ideal zone: top half 0.73, bottom half 0.30
- largest cluster left: top half 7.94, bottom half 16.89
- peak force p90, mN: top half 181.80, bottom half 106.13
- rank correlation with the robust score (+ helps): vib_mm +0.84, ss_period +0.56, bar +0.43, ss_deg +0.31, tip=round +0.20, tip=flat -0.20


## malaise round 1 (EXPLORATORY, 2026-10-25 13:07, auto)

**Tried:** 8 candidates (ce), 24 runs, 4 min wall.

**Leader:** B-87f42099: grid 8.9 mm (bars 1.2), pins 2 x 7.6 mm flat every ~11.8 mm; seesaw +/-8 deg, 3.5 s + 0.35 mm buzz at 40 Hz. Robust 0.683 (mean 0.756); free 100%, gentle 31%, sort 90%, largest cluster 1.0.

- reference NO BREAKER: robust 0.217; free 31%, gentle 76%, sort 17%
- reference cad/breaker_layer.py default (open 8, pins 2.5 x 12 every 10, round) on the default seesaw: robust 0.287; free 65%, gentle 46%, sort 22%
- reference the CAD default breaker, default seesaw + 0.3 mm buzz at 40 Hz (1.9 g, the tool's): robust 0.479; free 85%, gentle 35%, sort 75%

**Why the losers lost:**

- free at the end: top half 0.90, bottom half 0.74
- gentleness: top half 0.32, bottom half 0.38
- in the ideal zone: top half 0.78, bottom half 0.46
- largest cluster left: top half 5.83, bottom half 14.13
- peak force p90, mN: top half 204.95, bottom half 136.25
- rank correlation with the robust score (+ helps): vib_mm +0.68, bar +0.48, pin_h -0.34, ss_period +0.31, open +0.23, pin_d +0.13


## malaise round 2 (EXPLORATORY, 2026-10-25 13:11, auto)

**Tried:** 8 candidates (ce), 24 runs, 4 min wall.

**Leader:** B-31c4ea6d: grid 12 mm (bars 1.9), pins 2.8 x 6 mm round every ~9 mm; seesaw +/-10.5 deg, 3.6 s + 0.3 mm buzz at 40 Hz. Robust 0.700 (mean 0.759); free 100%, gentle 30%, sort 90%, largest cluster 1.0.

- reference NO BREAKER: robust 0.217; free 31%, gentle 76%, sort 17%
- reference cad/breaker_layer.py default (open 8, pins 2.5 x 12 every 10, round) on the default seesaw: robust 0.287; free 65%, gentle 46%, sort 22%
- reference the CAD default breaker, default seesaw + 0.3 mm buzz at 40 Hz (1.9 g, the tool's): robust 0.479; free 85%, gentle 35%, sort 75%

**Why the losers lost:**

- free at the end: top half 0.93, bottom half 0.76
- gentleness: top half 0.32, bottom half 0.36
- in the ideal zone: top half 0.83, bottom half 0.52
- largest cluster left: top half 4.02, bottom half 12.81
- peak force p90, mN: top half 228.96, bottom half 150.38
- rank correlation with the robust score (+ helps): vib_mm +0.50, open +0.43, bar +0.37, pin_h -0.33, pin_d +0.27, tip=round +0.25

## seesaw round 0 (2026-10-25 13:21, auto)

**Tried:** plinko: 14 (baseline, lhs); inserts: 9 (baseline, lhs); current: 1 (current). 126 runs, 27 min wall.

**Leader so far:** I-c7efd18f (inserts, round 0) square holes 5 (bar 1.2) / 2 (bar 1), stroke seesaw +/-10 deg (ends tip, neighbours alternate), 2 s per cycle, constant speed: robust 0.364 (mean 0.382 +/- 0.018); big (pasta, chickpea) 49% pure / 100% recovered, rice 79% pure / 74% recovered, quinoa 89% pure / 44% recovered; PEN 6/6 (clr 0.01, pen 0.283).

**Screen results this round (10 s, progress score), best per family:**

- plinko: best P-fd614143 screen robust 0.779; median 0.641; failures in 0 of 14 candidates
- inserts: best I-c7efd18f screen robust 0.636; median 0.528; failures in 0 of 9 candidates
- current: best C-4a07a203 screen robust 0.561; median 0.561; failures in 0 of 1 candidates

**Why the losers failed** (particles per run, over this round's screened candidates in the bottom half of each family; the most common modes):

- plinko: quinoa: held upstream -> layer_1_rods (10.2 in 7 cands); quinoa: held upstream -> layer_2_rods (8.0 in 7 cands); rice: held upstream -> layer_1_rods (7.2 in 7 cands); rice: leaked downstream -> layer_3_catch (9.4 in 5 cands); rice: between -> in the floor of layer_1_rods (0.3 in 1 cands)
- inserts: rice: held upstream -> on_h2p55b0p95 (26.7 in 1 cands); rice: held upstream -> on_h2p75b1p05 (26.0 in 1 cands); rice: held upstream -> on_h3p75b1p85 (18.7 in 1 cands); quinoa: held upstream -> on_h1p25b1p45 (18.7 in 1 cands); quinoa: held upstream -> on_h3p75b1p85 (17.7 in 1 cands); rice: held upstream -> on_h3p35b2p15 (16.0 in 1 cands)
- current: rice: leaked downstream -> catch (4.7 in 1 cands); quinoa: between -> in the floor of on_mesh5 (4.0 in 1 cands); rice: between -> in the floor of on_mesh5 (3.7 in 1 cands); rice: held upstream -> on_mesh5 (1.3 in 1 cands); rice: lost -> z -181439 mm (0.3 in 1 cands); quinoa: held upstream -> on_mesh2 (0.3 in 1 cands)

**Leaders' remaining losses** (full runs, top 3):

- I-c7efd18f: quinoa: held upstream -> on_h4p85b1p35 10.7; quinoa: held upstream -> on_h1p85b1p15 6.2; rice: held upstream -> on_h4p85b1p35 6.0; rice: leaked downstream -> catch 1.7
- P-8e00372e: quinoa: held upstream -> layer_1_rods 9.5; quinoa: held upstream -> layer_2_rods 7.0; rice: held upstream -> layer_1_rods 2.8
- P-19e01862: quinoa: held upstream -> layer_1_rods 11.8; quinoa: held upstream -> layer_2_rods 5.0; rice: held upstream -> layer_1_rods 3.0

**Parameters at a bound among each family's elite** (the range may be too narrow):

- plinko: ss_shape constant_speed 0.50/sine 0.50
- inserts: ss_shape constant_speed 0.38/sine 0.62

**Next hypothesis (auto):** 1.7 particles per run leak through a gate they should not pass: tighten that gate or cap the gap height (window gate); the leader's near-size results are flagged (overlap vs clearance): check it at a smaller dt or stiffer contacts before trusting it



## Seesaw round 0 and the malaise verification (notes, 2026-10-25 13:25)

**Seesaw round 0 (full runs at 16 s, 2 seeds x 3 friction sets):** no design reaches the 0.5 winner bar on a +/-5-15 deg seesaw alone, so `winners_seesaw.json` has no winners yet.
- Best: today's glued mesh 0.406 (it jams 6 grains per run), the demo rig 0.364, plinko 4.7 / 1.6 at the default seesaw 0.345.
- Every design keeps the big grains and most of the rice. Quinoa recovery stays at 33-45%: it rides the solid parts of the upper tray.
- That matches VERIFY_SEESAW.md (the physics session) and the 11:20 renders. Round 1, running now, adds the 40 Hz buzz (`vib_mm`), the demo rig + 0.3 mm, and bambu's ribs-across inserts.

**Malaise, verified on fresh clumps (seeds 1, 2 x the 3 bond sets; each seed packs a different clump):**

| id | design | robust, seed 0 | robust, seeds 1-2 | robust, all seeds | freed, seeds 1-2 |
|---|---|---|---|---|---|
| B-164f355a | grid 11.3 (bars 1.6), round pins 3.1 x 8 every 12.9; +/-7 deg, 1.1 s + 0.35 mm buzz | 0.672 | 0.612 | **0.630** | 94% |
| B-87f42099 | grid 8.9 (bars 1.2), flat pins 2 x 7.6 every 10.1; +/-8 deg, 3.5 s + 0.35 mm buzz | 0.683 | 0.575 | 0.605 | 94% |
| B-31c4ea6d | grid 12 (bars 1.9), round pins 2.8 x 6 every 13.9; +/-10.5 deg, 3.6 s + 0.3 mm buzz | 0.700 | 0.336 | 0.422 | 76% |
| CAD default + 0.3 mm buzz | grid 8, round pins 2.5 x 12 every 9.6; +/-10 deg, 2 s | 0.479 | 0.440 | 0.452 | 84% |
| CAD default | (same, no buzz) | 0.287 | 0.188 | 0.216 | 34% |
| no breaker | the demo rig's trays alone, +/-10 deg, 2 s | 0.217 | 0.235 | 0.229 | 48% |

- Round 2's leader was lucky on seed 0. Its clumps on seeds 1-2 kept a large cluster.
- **From now on the malaise winners are verified designs, ranked by the lower of the seed-0 robust and the all-seed robust** (a design can only lose by being checked). The verify run covers the top 6.
- **What holds:** a breaker with short pins (6-8 mm, not the CAD's 12) plus a 0.3-0.35 mm buzz frees 94% of the clump on fresh seeds, against 48% with no breaker. The CAD default alone (34%) is no better than no breaker. With the buzz it reaches 84%.
- **The cost:** grains are hit harder. The peak-force p90 is about 250 mN against 34 mN with no breaker, where the clump just sits whole.

**Correction (13:27):** the malaise round entries above give the pin spacing as "every ~X mm", which is the `pitch` key (a target). The CAD stands pins on grid nodes, every k-th with k = round(pitch / (open + bar)), so the real spacing is k x (open + bar). For every leader so far k = 1, so it's the grid step: 12.9 mm for B-164f355a, 10.1 for B-87f42099 and 13.9 for B-31c4ea6d. The leaderboard now shows the real spacing.
## seesaw round 1 (2026-10-25 13:41, auto)

**Tried:** inserts: 9 (baseline, ce, lhs); across: 2 (current); plinko: 16 (ce, lhs). 135 runs, 19 min wall.

**Leader so far:** P-3bbfc231 (plinko, round 1) rods L1 gap 4.7 (rod 3.5 wide, 3.2 tall) / L2 gap 1.5 (rod 2.9, 2.2), stroke seesaw +/-14 deg (ends tip, neighbours alternate), 1.9 s per cycle, constant speed + 0.35 mm buzz at 40 Hz: robust 0.998 (mean 0.998 +/- 0.000); big (pasta, chickpea) 100% pure / 100% recovered, rice 100% pure / 100% recovered, quinoa 100% pure / 100% recovered; ok.

**Screen results this round (10 s, progress score), best per family:**

- inserts: best I-beceacfc screen robust 0.849; median 0.644; failures in 0 of 9 candidates
- across: best A-860ce30b screen robust 0.779; median 0.361; failures in 0 of 2 candidates
- plinko: best P-690b1645 screen robust 1.000; median 0.894; failures in 0 of 16 candidates

**Why the losers failed** (particles per run, over this round's screened candidates in the bottom half of each family; the most common modes):

- inserts: quinoa: held upstream -> on_h1p55b1p25 (21.0 in 1 cands); rice: held upstream -> on_h2p95b1p65 (20.7 in 1 cands); quinoa: held upstream -> on_h1p55b1p35 (19.7 in 1 cands); quinoa: held upstream -> on_h4p45b1p45 (15.3 in 1 cands); quinoa: held upstream -> on_h4p55b1p25 (13.7 in 1 cands); rice: held upstream -> on_h4p45b1p45 (13.3 in 1 cands)
- across: rice: leaked downstream -> catch (27.7 in 1 cands)
- plinko: rice: leaked downstream -> layer_3_catch (11.9 in 3 cands); quinoa: held upstream -> layer_2_rods (5.9 in 6 cands); rice: held upstream -> layer_1_rods (4.1 in 6 cands); quinoa: held upstream -> layer_1_rods (3.9 in 6 cands)

**Leaders' remaining losses** (full runs, top 3):

- P-3bbfc231: none
- P-3b817251: none
- P-690b1645: rice: between -> in the floor of layer_1_rods 0.2

**Parameters at a bound among each family's elite** (the range may be too narrow):

- inserts: ss_shape constant_speed 0.40/sine 0.60
- plinko: ss_shape constant_speed 0.66/sine 0.34

**Next hypothesis (auto):** the leader sorts cleanly; refine for robustness and throughput.



## Seesaw round 1: the buzz makes the seesaw sort (notes, 2026-10-25 13:45)

**Winners (`winners_seesaw.json`, full runs at 16 s, 2 seeds x 3 friction sets, no flags):**
1. **P-3bbfc231:** plinko rods L1 gap 4.7 (rod 3.5 wide, 3.2 tall) / L2 gap 1.5 (rod 2.9, 2.2), on a seesaw of **+/-14 deg at 1.9 s, constant speed, + a 0.35 mm buzz at 40 Hz** (1.8 g). Robust **0.998**: every class 100% pure and 100% recovered, t90 0.6 s.
2. **P-3b817251:** plinko 4.5 / 1.4 (rods 2.3 x 2.8 / 2.2 x 2.6), **+/-10.5 deg at 1.5 s + 0.2 mm** (1.3 g). Robust **0.997**. This one sits at the user's +/-10 deg default with a gentler buzz.
3. P-690b1645: plinko 4.9 / 1.4, +/-13 deg, 2.1 s + 0.4 mm. Robust 0.974, gate overlap flagged (stiff-contact rerun running).

**The buzz is what does it.** In round 0, with no buzz, the best plinko scored 0.345. Every round-1 elite has a buzz of 0.2-0.45 mm, and below 0.15 mm scores fall to 0.5-0.7 (screen). This is the seesaw session's finding (SEESAW.md 12:30) turned into a design: the seesaw carries grains end to end, and the buzz shakes them off solid parts and into the openings.

**Separate trays (inserts), which is what the rig hangs:**
- The best searched design is I-beceacfc: holes 5.2 / 1.8, +/-11.5 deg, 1.9 s sine + 0.35 mm. Robust 0.630, with gate overlap flagged and 3 grains per run past an opening they can't fit.
- The demo rig + 0.3 mm buzz scores 0.389, against 0.364 without. The buzz clears the 5 mm tray (quinoa 100% recovered), but it pushes the long rice through the 2 mm square holes corner to corner (rice recovery 57%).
- **Ribs across (bambu's `5mm_across` / `2mm_across` in the seesaw holder):** 0.528 on the plain seesaw, the best separate-tray result without a buzz (quinoa 73% through, against 44% for the demo rig). With the 0.3 mm buzz it fails at -0.03: rice falls through the 2 mm across insert (5% kept). **Ribs across want no buzz, or a finer second tray.**

**Caveats (assumed):**
- **Plinko is one holder box** with its three rod layers inside, rocking as one level. The user's rig hangs separate trays, so plinko goes in as a single tray holding all three layers. The tray-per-class designs sort less well (0.63 at best).
- Angle, period, buzz and pivot height are all unmeasured. Whether the rig's motor can add a 40 Hz buzz of 0.2-0.35 mm (1.3-1.8 g) is the question for the bench. The handheld tool does buzz.
- Full runs are 16 s on 2 seeds, not 30 s on 3 (seesaw runs cost about 25x a translation run per sim second even after the 20x fix). Not stress-tested on printer undersize.
- The sim ranks designs; it isn't calibrated against bench counts.

**Where this leaves the story (for main / PITCH.md):**
- Seesaw alone sorts the big grains only.
- Seesaw + buzz with plinko rods sorts all three classes in the sim.
- Breaker (short pins) + buzz frees 94% of a fresh grain clump, against 48% with no breaker (malaise, EXPLORATORY).
- The buzz is the common lever.

**Stiff-contact rerun (13:46, dt 0.125 ms, timeconst 0.25 ms, 3 seeds x 3 friction sets, 16 s):**
- P-690b1645 holds at 0.996, with 1 of 9 runs still flagged.
- P-a822b277 (plinko 3.5 / 1.4, +/-6 deg, 4.3 s + 0.3 mm) comes back clean at 0.947 and is now winner #3: a low-angle option.
- Winners 1 and 2 were never flagged.

**Replays (local, gitignored), for bambu's hero clips:**
- `sim/out/opt/seesaw/replay/P-3bbfc231/view.html` and `.../P-3b817251/view.html`: every kind 100% in its class.
- `sim/out/opt/malaise/replay/B-164f355a/view.html`: the winning breaker frees the clump (medium bonds, 100%).
- `.../B-5405ea9b/view.html`: no breaker, and the clump sits whole on the 5 mm tray (2% freed).

**Stop for the freeze.** Final: `winners_seesaw.json`, `winners_malaise.json` and their leaderboards. Next, after the hack:
- the insect clump, once `clumps.pack` handles insects;
- printer-undersize stress on the seesaw winners;
- a bench check of whether the rig can add the 40 Hz buzz.
