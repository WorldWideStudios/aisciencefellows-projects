# Task: break up the clump. This is the system's real job

> Read [docs/SYSTEM.md](../SYSTEM.md) first. It's the one description of the rig, the mounting, the motion and the scope, and it overrides this brief where they differ.

**From the user (Oct 25, ~10:15 PT):** Malaise samples often arrive as a **compacted ball or mound of insects**, mixed with **leaves, twigs and dirt**. The input to our system is **a clump**, not loose specimens. The first stage has to **break the clump apart**; size sorting comes after. That's the true point of the system, so it's now the top priority for every session. Submission is at 14:30.

## What we're designing
A **breaker stage** on top of the sorting stack:
- **In:** a wet clump of tangled insects, plus debris.
- **Out:** loose specimens falling onto the existing sorting trays. Leaves are held back on top (scalped). Dirt washes down to the catch.

It uses what the rig already has: the shaker (the up-and-down / angled stroke from [demo-rig.md](demo-rig.md)) and the spray jets (`sim/spray.py` already pushes and wets particles).

**Assumptions** (unmeasured; tell the user, and correct them when the team says otherwise):
- **The clump:** a ball 20–40 mm across, of 50–300 small specimens (mostly 2–6 mm flies, a few > 6 mm). It's held together by tangled legs and wings and by the ethanol / water film.
- **Debris:** leaf pieces 10–40 mm across and about 0.2 mm thick; twigs 1–3 mm × 10–30 mm; soil grains 0.1–1 mm.
- **Gentle:** specimens go on to imaging and DNA barcoding. Breaking legs or antennae, or crushing them, is a failure, not just a slowdown.

## Shared interface: the breaker layer
**bambu** builds it in CAD and the **optimizer** builds it in the sim. Use the same names in both, so a sim winner prints as is.

`breaker:open=<mm>,bar=<mm>,pin_d=<mm>,pin_h=<mm>,pitch=<mm>,tip=<round|flat>`
- **The layer:** a drop-in like `cad/sieve_insert.py`. Same 131.4 × 95.4 mm footprint and the same pull tabs, so it sits on top of the stack.
- **The floor:** a square grid. The openings (`open`, 6–12 mm) let freed specimens through and hold leaves back; `bar` is 1.2–2.5 mm.
- **The pins:** blunt pins rise from the grid nodes, `pin_d` 1.5–4 mm across, `pin_h` 5–20 mm tall, every `pitch` 6–15 mm. The shake throws the clump onto them and they tease it apart.
- **Printable:** features ≥ 0.4 mm, openings on 0.1 mm steps, pin heights on 0.2 mm layers, printed without supports (pins point up).
- **The stack under it:** the current winner tower, or `inserts:5mm,2mm` for the demo rig.

## A. Clump session (`clump-sim`, from 11:15): clumps and debris. **This unblocks everything**
0. **Rocking moved to the new seesaw session** (10:55; see [SYSTEM.md](../SYSTEM.md) §3 and §5). The clump session does the clumps now (moved from physics at 11:15). Put them in `sim/clumps.py` with a minimal hook in `sorter.py`.
1. **A `clump` particle:**
   - N specimens (`insects.py` kinds, or grain surrogates for the bench demo) packed into a ball.
   - Each touching pair is joined by a **breakable bond**: an equality `weld` / `connect`. Each step, set `d.eq_active[i] = 0` once the bond's constraint force (from `efc_force`) exceeds `bond_N`.
   - **Wetting weakens bonds:** use the wetness `w` from `spray.py`, with `bond_N(w) = bond_dry · (1 − k_wet · w)`.
   - Bond strength is unknown. Run it as 3 sets (weak / medium / strong), like the friction sets, and rank designs across all three.
2. **Debris kinds:**
   - `leaf`: a thin, light plate (rigid is fine for now; say so).
   - `twig`: a capsule.
   - `dirt`: small, dense spheres.
3. **Metrics,** added to `run_metrics` or as a new helper. Don't break existing callers.
   - **Break-up:** the fraction of specimens free (no live bonds) over time, t50 / t90 to free, and the largest cluster left at the end.
   - **Damage proxy:** the peak contact force on each specimen body, and the share over a fragility threshold (make it a parameter and report it).
   - **Leaf blinding:** the share of grid openings covered by a leaf.
   - Then the usual sort metrics for the specimens downstream.
4. **Write `sim/CLUMPS.md`:**
   - the model and its assumptions;
   - a first comparison on the demo stack, with and without a simple pin layer;
   - strokes: flat vs up and down vs angled, at equal peak acceleration;
   - spray on vs off.
5. **PR early**, as soon as a clump builds and breaks: the optimizer is waiting on it. Keep workers ≤ 8 while the optimizer runs, and watch memory: the laptop is short.

## B. Bambu session (`bambu-viz`): CAD of the breaker layer
1. Write `cad/breaker_layer.py`, parametric with the names above, plus a preview, checks (`*_checks.json`) and a slice. Start from `cad/sieve_insert.py`.
2. Build one sensible default, e.g. `open=8,bar=1.6,pin_d=2.5,pin_h=12,pitch=10,tip=round`. Slice it and add it to `sim/opt/print_plan.md`. It should print after the current winner plate.
3. **Bench demo clump** (a suggestion to the team; write it in the print plan):
   - Make a surrogate clump by binding rice, quinoa and pasta with a little water-soluble binder (e.g. sugar water), plus some leaf bits.
   - Show it breaking up under the shake and spray, then sorting.
4. **Viewer:** show the clump breaking apart on the breaker layer, once physics has a clump run.
5. **Fix the replay's motion** ([SYSTEM.md](../SYSTEM.md) §3). The boxes must pitch about their +X tab, not slide up and down as one block. Don't show `demo_tower_stiff` as the real motion: the user says it misreads the rig. Re-render once physics's rocking stroke lands; the viewer has to apply the tray's rotation, not just its offset.

## C. Optimizer session (`design-opt`): the `malaise` study
1. **Wrap up the demo study** so `winners.json` is final for the current print.
2. Add **`sim/designs_breaker.py`** (the `breaker:` spec above, on top of a chosen stack). Add **study `malaise`**: clumps + debris + some loose specimens. Use physics's clump model when it lands; until then, build the geometry and the search space.
3. **Score:**
   - break-up completeness and t90;
   - minus the damage proxy and leaf blinding;
   - then the existing sort score for what gets through.
   - Robust across the bond-strength sets × friction sets × seeds.
4. **Search space:** breaker parameters + the stroke + spray on/off/flow.
   - **Stroke:** use physics's **rocking** stroke once it lands: yaw up to ±30° about the +X tab by default, with `rock_deg`, `rock_axis`, `rock_hz` and `phase_deg` on top of the mount stroke (SYSTEM.md §3). Translation-only angles are a simplification.
   - Also re-score the current demo winners under rocking before the pitch quotes them.
5. **Leaderboard:**
   - `sim/opt/leaderboard_malaise.md` and `winners_malaise.json`;
   - **EXPLORATORY** (bond strengths aren't measured);
   - with the reasoning in `LOG.md` as before.

## Main session
README reframed around the clump. This brief. Merging PRs as they arrive.
