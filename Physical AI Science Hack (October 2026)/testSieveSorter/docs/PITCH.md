# Pitch: 5-minute demo script

Physical AI for Science Hack, BioKEA track. Live demos 15:30–16:30, then demos and pitching 16:30–17:30. **Numbers are from the MuJoCo sim and uncalibrated. Say so once, clearly.** *Numbers refreshed at 13:45 from the merged results (README "Results").*

## 0:00 The problem (30 s)
- BioKEA images and DNA-barcodes insects from Malaise traps: thousands of mostly tiny flies in ethanol.
- The sample often arrives as a **clump**: tangled insects with leaves, twigs and dirt. Sieves only sort loose specimens, and pulling a clump apart by hand is slow and breaks legs.
- BioKEA's BugSorter (EntoSieve, upgraded) shakes a stack of glued-mesh trays. We kept its idea, a stack of sieves, and redesigned the parts it shakes.

## 0:30 What we built (60 s)
Show the CAD previews (`cad/out/*.png`) and the printed parts on the table.
1. **The breaker layer** goes on top: blunt 8 mm pins on an 11.3 mm grid (the optimizer's design). The motion throws the clump onto the pins and the spray loosens it. Leaves stay on top, and freed specimens fall through.
2. **The seesaw stack:** separate trays one above the other (5 mm, 2 mm, catch). Each one seesaws about its own centre pivot, and neighbours rock in opposite directions, so whatever drops lands on a tray tilted the other way.
3. **Fixes the sim found before we printed:**
   - inserts with **ribs across the tilt**, because small grains rode ribs that ran along it;
   - a **centre-pivot holder**, which halves the drop between levels, the biggest impact force on specimens;
   - a **lipped catch pan**, because grains bounced out.

## 1:30 The simulation (90 s)
Open the **Sieve Render Lab** (the viewer with a Run menu) and switch runs live:
1. **"Insect clump, no breaker":** 35 Malaise-size insects plus a leaf, twig and dirt. On the plain seesaw it holds together: 9% freed, the largest piece 32 of 35.
2. **"Insect clump on the optimizer's breaker":** the same clump, plus the breaker, the buzz and the spray. It holds for a few seconds, then comes fully apart: 100% freed, 90% by 5 s.
3. **"Before" → "After":** all 10 grain kinds on the seesawing stack.
   - Before, 12 of 45 small grains sit on the 5 mm ribs.
   - After (ribs-across inserts, centre pivot, buzz), 44 of 45 reach the catch.
   - Be upfront about the cost: the buzz shakes plain rice through 2 mm.
- Inside the viewer: toggle grain kinds, zones and the tower frame, and scrub time. The tower frame is display only; the physics is the trays, the particles, the motion and the spray.

## 3:00 The system designs its own parts (60 s)
Show `sim/opt/leaderboard_malaise.md` and `sim/opt/LOG.md`.
- The optimizer proposes printable breakers and motions, runs each across weak / medium / strong clumps, and ranks by the worse of two checks: its first run, and freshly packed clumps. No design wins on one lucky clump; round 2's 0.700 "leader" fell to 0.42 and was dropped.
- **The winner, B-164f355a, scores 0.630 and frees 94% of fresh clumps,** against 0.45 for our hand-designed breaker with the buzz and 0.23 for no breaker. Its pins are 8 mm, shorter than the 12 mm we'd have printed.
- It writes down why the losers lost, and it found on its own that gated containers can't sort on a symmetric seesaw.
- **On the seesaw itself, it found a design that sorts every class at 100% in the sim:** plinko rods 4.7 / 1.5 mm, ±14° with a 0.35 mm buzz, scoring 0.998. With the seesaw alone, nothing beats 0.35. The buzz is the lever.
- **Parameters to G-code with no hand-drawing:** B-164f355a is sliced at 57 min and 19.6 g. Show the printed part if it's done.

## 4:00 Bench and honesty (30 s)
- Forum's bench prototype: a printed 5 mm tray on a handheld DeWalt tool, sorting pasta from rice.
- The sim **ranks** designs. Calibrating it takes 10 minutes of bench counts (`sim/BENCH.md`): grain calipers, the box spacing, the rock angle and period.

## 4:30 What's next (30 s)
- Calibrate against bench counts.
- Real Malaise insect mixes: the sim already has the real size shares, 57% under 1.5 mm.
- Spray tuning for clumps.
- Hand it to BioKEA as drop-in parts for their tower.

## Assets
| What | Where |
|---|---|
| Mascot / banner | `docs/assets/mascot.png` |
| CAD previews | `cad/out/breaker_*.png`, `cad/out/seesaw_*.png`, `cad/out/sieve_insert_*_across.png`, `cad/out/win*_tower.png` |
| Replays | **Sieve Render Lab**, a private artifact with 10 runs in one viewer and a Run menu: https://claude.ai/artifact/4KRY8zRw61tjvsagchb9Wx. Share it from its Share menu before the demo if teammates present. |
| Clips (local `media/`, never committed) | `hero_forum_vs_sim.mp4`, `hero_clump_breaker.mp4`, `hero_optimizer_breaker.mp4` and the tower clips, all captioned "MuJoCo sim, uncalibrated" |
| Leaderboards | `sim/opt/leaderboard_malaise.md` (the breaker), `sim/opt/leaderboard_seesaw.md`, `sim/opt/leaderboard.md` |
