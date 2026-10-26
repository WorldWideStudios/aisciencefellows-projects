# Sim performance on the new laptop

Measured 2026-10-25 by the physics session (`physics-bench`). The recorded runs are in `sim\out\` (gitignored).

## Machine and setup

- Lenovo 83F3: Intel Core Ultra 9 275HX, 24 cores and 24 threads (P- and E-cores, no hyper-threading), 31.4 GB RAM, RTX 5070 Laptop GPU.
- **Smart App Control is on**, and it blocks the unsigned MuJoCo, OCP and VTK DLLs on Windows. The sim therefore runs in **WSL2 Ubuntu 26.04**, using the venv `~/venvs/sieve` (uv Python 3.12.15, mujoco 3.17.0, numpy 2.5.4). WSL sees all 24 cores and 15 GB of RAM. See `docs/sessions/README.md` for how to run it.
- The repo stays on the Windows side (`/mnt/c/...`). Each run reads only a few small files, so the cross-filesystem penalty doesn't matter.
- MuJoCo runs on the CPU, one thread per run. The GPU isn't used. MJX and MuJoCo Warp only pay off when batching thousands of copies of a scene, while our sweeps are tens of runs with mesh colliders and dense contacts. That would be a separate experiment.

## Reference run

Same config as the old `current_mesh` run, copied from its `results.json`. The brief said dt was 0.5 ms; it was 0.25 ms.

```
sorter.py --design inserts:mesh5,mesh2 \
  --mix rice=20,quinoa=20,chickpea=5,pasta=5,insect_compact=8,insect_elongate=8,insect_longleg=4 \
  --stroke constant_speed:amp_mm=10,speed_mm_s=50,ramp_s=0.01 --duration 15 --settle 1 --seed 1 \
  --dt 0.00025 --timeconst 0.0005 --friction 0.4
```

| | Old machine (Windows) | This laptop (WSL) |
|---|---|---|
| Wall time, 16 s simulated, 64000 steps, 70 bodies | 517.3 s | **45.1 s** (11.5x faster) |
| Max overlap, particle vs tray | 0.113 mm | 0.119 mm |
| Max overlap, particle vs particle | 0.149 mm | 0.031 mm |
| Recovery: rice / quinoa / chickpea / pasta | 0.40 / 0.90 / 1.00 / 1.00 | 0.45 / 0.90 / 1.00 / 1.00 |
| Recovery: insects compact / elongate / longleg | 0.62 / 0.50 / 0.25 | 0.62 / 0.50 / 0.25 |

The outcomes match to within one particle per kind. Contact-rich runs diverge chaotically across platforms and floating-point paths, so a bit-identical rerun isn't expected. The old 517 s probably ran alongside other jobs: the old `compare_grains` sweep took 549 to 2532 s for identical 31 s runs, which points to heavy contention there.

## Sweep scaling and the worker default

The batch was 48 jobs: `sweep.py compare --seeds 4 --duration 3 --dt 0.00025 --timeconst 0.0005` (2 designs x 2 strokes x 3 frictions x 4 seeds, 76 particles, 4 s simulated each), with the machine otherwise idle.

| Workers | Total wall | Speedup vs 1 | Median wall per job | Slowest job / median |
|---|---|---|---|---|
| 1 | 453 s | 1.0x | 9.1 s | 1.35 |
| 4 | 126 s | 3.6x | 9.9 s | 1.19 |
| 8 | 90 s | 5.0x | 14.3 s | 1.24 |
| 16 | 70 s | 6.5x | 22.1 s | 1.34 |
| 20 | 64 s | 7.1x | | |
| **22** | **48 s** | **9.5x** | | |
| 24 | 47 s, repeat 56 s | 8.1-9.7x | 20.9 s | 1.31 |

- A single job slows down as more jobs run at once: 9 s alone, 14 s with 8 running, 21 s with 16 or more. That's the laptop's all-core power and turbo limit, plus shared memory bandwidth. Total throughput still keeps rising up to all 24 cores.
- The P-core/E-core mix produces mild stragglers: the slowest job takes about 1.3x the median. That only matters on the last round of a small sweep.
- Totals jump in steps with the number of rounds (`ceil(jobs / workers)`): 20 workers needs 3 rounds for 48 jobs, while 22 needs 2 plus a short third. Run-to-run noise is about +/-10% (thermals), e.g. 47 s vs 56 s for the two 24-worker runs.
- **Default: `WORKERS = cpu_count - 2`**, which is 22 here. It matches the throughput of 24 and leaves 2 cores for the OS and the other sessions. Override with `sweep.py ... --workers N`. Memory isn't a limit: 22 runs x 128 MB arena fits in WSL's 15 GB.

## Instabilities (`Nan, Inf or huge value in QACC`)

**What the old log showed.** The old machine's `MUJOCO_LOG.TXT` had 15 warnings between 20:54 and 22:17 on Oct 24. All of them came at t ≤ 0.51 s, inside the 1 s settle, on DOFs up to 696 (mixes of more than 100 bodies). Several repeat exactly (DOF 183 at t=0.0495, DOF 31 at t=0.1195), so they were deterministic reruns of the same config.

**The real problem was that they were silent.** MuJoCo answers a NaN/Inf/huge QPOS, QVEL or QACC by resetting `mjData` to the initial state and carrying on. An unstable run therefore finished with plausible-looking results, and only the log file showed anything. None of the saved old results were hit: every `sim_s` in `compare_grains` and `dtcheck` matches its expected length, and a reset would have made it short. So the unstable runs from that evening left no results; they were probably quick tests or killed jobs. The sim was committed in one commit afterwards, so git can't show which code produced them.

**Fix.** `run()` now lists every reset in `results["unstable_resets"]` (step times). `sorter.py` prints `UNSTABLE ... the results are not valid`, and `sweep.py` tags the run in its log. Unstable runs are **flagged, not skipped**. Resets are detected by `d.time` going backwards: the reset also clears MuJoCo's warning counters, so a counter check misses every reset after the first. Verified by injecting a NaN-level velocity twice into one run: both resets were caught (an earlier counter-based version caught only the first).

**Reproducing them.** `sim/instab.py` runs short settle+shake jobs and stops at the first reset, recording its time, phase, warning and particle kind. With the current code on this machine there were **0 resets in 840 runs**:
- 384 horizontal runs: `pool:w5p0,t1p4`, `inserts:mesh5,mesh2`, `inserts:5mm,2mm` and `plinko`; mixes of 76 grains, 70 grains plus insects, and 120 grains plus insects; (dt, timeconst) of (0.5, 2), (0.25, 0.5), (0.25, 1) and (0.125, 0.5) ms; 8 seeds. These used the probe's first version, which watched QACC only.
- 456 runs with vertical and angled strokes of up to 8 g, including stiffer contacts (see `VERTICAL.md`).

The most likely explanation is that the old warnings came from development versions before the settle damping (`SETTLE_DAMPING`, which caps the drop speed at about 100 mm/s). That's unprovable, because the earlier code isn't in git.

**What a smaller timestep buys.** Penetration, not NaN, is the real limit. Horizontal strokes at the production settings (dt 0.25 ms, tc 0.5 ms) give a median maximum tray overlap of 0.10 mm. Vertical strokes give 0.15–0.27 mm at 2–4 g. Holding vertical strokes under the 0.3 mm gate clearance takes dt 0.125 ms with tc 0.25 ms, at about 2.5x the runtime. Details and recommendations are in `VERTICAL.md`.

## Defaults chosen

| Setting | Value | Where |
|---|---|---|
| Sweep workers | `cpu_count - 2` (22) | `sweep.py WORKERS`, `--workers` |
| Timestep / contact time constant, horizontal strokes and loose gates | 0.25 ms / 0.5 ms | `--dt 0.00025 --timeconst 0.0005` (the `RunConfig` default of 0.5 / 2 ms is too soft: about 0.5 mm of overlap) |
| Same, vertical strokes on tight gates (≤ 0.3 mm clearance) | 0.125 ms / 0.25 ms | `--dt 0.000125 --timeconst 0.00025` |
| Unstable runs | flagged in `unstable_resets`, never skipped | `sorter.py`, `sweep.py` |

The `RunConfig` default (0.5 ms / 2 ms) is unchanged, because other sessions and the earlier sweeps depend on it. Pass the settings above explicitly.
