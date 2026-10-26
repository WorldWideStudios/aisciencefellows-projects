# [P] Physics engine test on the new laptop

> **Read [docs/SYSTEM.md](../SYSTEM.md) first** (added 10:30). It's the one description of the system: the input is a clump; the rig is separate trays one above the other, each held at its +X tab and overhanging, so they **rock**. It overrides this brief where they differ.

Worktree `Documents\Github\testSieveSorter-physics`, branch `physics-bench`. Read [README.md](README.md) first for the shared venv and the Smart App Control blocker. **MuJoCo doesn't import on Windows here yet.** Fixing that is step 1.

## This laptop
- Intel Core Ultra 9 275HX: 24 cores, 24 threads (no hyper-threading; a mix of P- and E-cores)
- 31.4 GB RAM
- NVIDIA RTX 5070 Laptop GPU, plus Intel graphics. MuJoCo runs on the CPU here. MJX/Warp on the GPU would be a separate experiment, only if it's worth it.

## Baseline from the old machine
`sim\out\` isn't committed. These numbers come from the previous machine's logs:
- `inserts:mesh5,mesh2` (current mesh inserts): **16.0 s simulated in 517.29 s wall**, 64000 steps at 0.5 ms, 70 bodies. Max overlap 0.113 mm on the tray and 0.149 mm between particles. Recovery: rice 0.40, quinoa 0.90, chickpea and pasta 1.00, insects 0.25 to 0.62.
- `sim\MUJOCO_LOG.TXT` holds about 10 `Nan, Inf or huge value in QACC ... The simulation is unstable` warnings, from 20:54 to 21:37 on 2026-10-24. That was before the dt check sweep (`dtcheck`).
- The `compare_grains` sweep was left part-finished: 27 jobs, with only some `.out.json` files written.

## Scope
1. Get `import mujoco` working (see README.md; WSL2 is the first try).
2. Rerun the reference case from `sim\` and compare wall time with 517 s:
   `python sorter.py --design inserts:mesh5,mesh2 ...` (copy the args from `sorter.py`'s docstring and the old `current_mesh` run).
3. Measure how `sweep.py` scales with worker count (1, 4, 8, 16, 24) and pick the default for this CPU. P- and E-cores run at different speeds, so watch for stragglers.
4. Look into the QACC instabilities: which designs and particle counts trigger them, and whether a smaller timestep or other contact settings fix them without blowing up runtime. Don't hide them by skipping the NaN runs.
5. Write the results to `sim\PERF.md` (machine, settings, timings, and the chosen defaults).

## Not this session
- CAD, Bambu, and new geometry: that's the bambu session.
- Calibration against bench counts: it waits for the bench data in `sim\BENCH.md`.
