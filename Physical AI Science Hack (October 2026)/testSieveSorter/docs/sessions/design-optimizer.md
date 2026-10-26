# Task: a design optimizer that uses the sim to pick the best sieve design

> **Read [docs/SYSTEM.md](../SYSTEM.md) first** (added 10:30). It's the one description of the system: the input is a clump; the rig is separate trays one above the other, each held at its +X tab and overhanging, so they **rock**. It overrides this brief where they differ.

**Goal:** a loop that proposes design variants, runs them in the MuJoCo sim, scores them, and keeps improving. Its output is a ranked shortlist of designs with parameters the CAD can build directly. This is the main deliverable for the rest of the hack. Submission is Sun Oct 25 at 2:30 PM PT.

**Owner:** a dedicated **optimizer session**: worktree `Documents\Github\testSieveSorter-opt`, branch `design-opt`. The bambu session builds and slices whatever wins. The physics session (`physics-bench`) keeps working on benchmarking and the stroke and stays available as an extra hand.

**Sharing with physics:**
- MuJoCo runs in WSL2 (Ubuntu): venv `~/venvs/sieve`, uv-managed Python 3.12, with mujoco 3.17.0 and cadquery 2.8.0. Use it as is, don't recreate it, and log any package you add in `sim/opt/LOG.md`.
- Physics has uncommitted edits to `sim/sweep.py`. **Import from `sweep.py`; don't edit it.**
- Cap the optimizer at **16 parallel workers**, so the physics benchmarks keep some cores.

> **Update (05:50):** also search over **stroke angle** (0° horizontal to 90° vertical), and include the demo rig as a baseline row. **The rig is separate trays stacked one above the other** (06:20 correction): the baseline is the stacked printed inserts `inserts:5mm,2mm` (already in `BASELINES`), not the single `inserts:5mm`. See [demo-rig.md](demo-rig.md), part C.
>
> **Update (06:05):** `angle_deg` has been on `main` since 05:57 (PR #2), with `sorter.py` and the stroke dicts as `{"profile": "sine", "amp_mm": .., "freq_hz": .., "angle_deg": 45}`. `git merge origin/main` and add the angle as a stroke parameter. Treat older candidates that have no angle as 0°.

## Autonomous loop (how this runs without anyone watching)
`optimize.py run` already proposes, simulates, scores and refines on its own. Around it, the session keeps the loop going and publishes each round:
1. Run rounds back to back. `optimize.py run --study demo --rounds 1` resumes from the cache, so each call is one more round.
2. After each round:
   - Run `optimize.py report`.
   - Commit `sim/opt/LOG.md`, `sim/opt/leaderboard*.md` and `sim/opt/winners*.json`, push `design-opt`, and open or update its PR. The main session merges it.
3. Read the round's **Next hypothesis** in `LOG.md`. When it calls for something parameters can't express, implement it as a new family before the next round. That's the self-improving part, and it needs the session, not just the script.
4. Run this under `/loop` so it continues without prompts. Stop at the ~11:00 winners deadline and leave the leaderboard on `main`.
5. The bambu session runs its own `/loop`: merge `origin/main` and, when `winners.json` changes, build and slice the winners.

## Timeline (PT)
- **~09:00:** the optimizer runs end to end on one design family. First leaderboard on `main`.
- **~11:00:** `sim/opt/winners.json` on `main` with the top 3. Bambu starts CAD + slicing.
- **~12:30:** winners printed. Then a bench run if there's time.
- **14:30:** submit.

## What already exists (reuse it, don't rewrite it)
- **`sim/sweep.py`**
  - `run_jobs()` runs jobs in parallel child processes (`WORKERS = cpu_count - 4`). Use the worker count that `PERF.md` settles on.
  - `make_cfg()` builds a run config.
  - `param_sets()` gives the low / best / high friction sets, or the fitted ones once `calibration.json` exists.
  - `run_metrics()` already computes, per run: recovery per kind, contamination per zone, jams (`between` / `lost`), t50 / t90, `moved`, and penetration.
- **`sim/designs.py`:** `build(spec)` builds a design from a spec string, e.g. `pool:w5p0,t1p4`, `inserts:5mm,2mm`, `plinko`. The pool family and the holder families (`designs_holder.py`) are already parametric.
- **`sim/sorter.py`:** a single run; `results["particles"]` holds each particle's final and ideal zones.
- The **`sieve-gate-design` skill** (`.claude/skills/`) turns a sample spec into gate sizes. Use it to seed the search ranges.

## Build
1. **Add the gated container to the sim** (`gated:<slope>,<strip>,...`), from `cad/gated_container.py`'s parameters. It's the README's "final design", but the sim can't build it yet.
2. **`sim/optimize.py`:**
   - **Search space:** the parameters of each family. Gate widths and tunnel heights, floor slope, rod gap and spacing, hole size, plus the stroke within firmware limits: constant-speed, speed ≤ 50 mm/s (the firmware cap), amplitude about 5–15 mm.
   - **Hard constraints:**
     - Printable: features ≥ 0.4 mm, openings on 0.1 mm steps; tunnel heights on 0.2 mm layer multiples for vertical features.
     - Fits the holder pocket: 131.4 × 95.4 mm.
     - Same mounting as today: tabs and the stack order.
   - **Score:** worst class of min(purity, recovery). Then:
     - penalty for jams (`between`) and losses (`lost`);
     - a small penalty for t90 (throughput);
     - any NaN / unstable run scores as a **failure**, never skipped;
     - runs with penetration ≥ 0.5 × gate clearance are flagged as untrustworthy.
   - **Robustness:** the sim isn't calibrated yet. Score every candidate across all 3 friction sets × ≥ 3 seeds, and rank by the worst case or mean − 1 sd, so nothing wins on one lucky setting.
   - **Search method:**
     - Multi-fidelity: screen many candidates with short runs (about 8–10 s of sim), then promote the top ~20% to full 30 s runs (successive halving).
     - Within a family: Latin-hypercube start, then a few rounds of cross-entropy / CMA-style refinement around the leaders. Plain numpy; no new dependencies unless you note them in `docs/sessions/README.md`.
3. **The "learning" part: a design log.** After each round, write `sim/opt/LOG.md`:
   - what was tried and what won;
   - **why the losers failed** (where particles stuck, which class leaked where);
   - the next hypothesis.

   Structural ideas that parameters can't express go there as proposals, for example a new gate shape or a different slope layout. Implement them as new families when they look promising. That's how the system improves the design, not just tunes it.
4. **Outputs:**
   - Raw runs go to `sim/out/opt/` (gitignored).
   - `sim/opt/leaderboard.md` (committed): the top 10 with scores and per-class purity / recovery / jams.
   - `sim/opt/winners.json` (committed): the top 3, with the exact parameters the CAD scripts need and the sim spec string.
   - A `view.html` replay for each winner.

## Classes to score
- **Demo set:** the surrogate grains, pasta / rice / quinoa (plus chickpea). This is what we can bench today.
- **Real target:** insects in BugPicker's classes, under 2 mm, 2–6 mm and over 6 mm (`sim/insects.py`). Score them as a second leaderboard, labelled **exploratory** (no real specimens measured yet).
- Demo targets (`docs/gates-verdict.md`): ≥ 90% purity and ≥ 90% recovery per class, ≥ 99% total recovery, and no manual clearing.

## Bambu session's side
- `git fetch origin && git merge origin/main` every ~30 min. When `sim/opt/winners.json` appears or changes, for each winner:
  1. build the parts from its parameters;
  2. render previews;
  3. run `slice.py` for time and grams on the P1S.
- Put the results in `cad/out/` and a short table in `sim/opt/print_plan.md`, then open a PR.
- If a winner can't be printed cleanly (bridging, too-thin features), write that back into `sim/opt/LOG.md` as a constraint, so the optimizer stops proposing it.

## Honesty rules
- The sim ranks designs; it doesn't predict real percentages until `calibrate.py` has bench data. Say so on the leaderboard.
- Report the full count matrix for the winners, not just a score.
- Don't tune the score to make a favourite design win.
