# Parallel sessions

> **Next steps for every session: [PLAN.md](PLAN.md)** (11:45 → 14:30 submission).
>
> **Every session: read [../SYSTEM.md](../SYSTEM.md) first.** It's the one shared description of the system (clump input, stacked trays, mounted at the +X tab, rocking motion, sim scope, who owns what).
>
> **Top priority since 10:15: [clump-breakup.md](clump-breakup.md).** Malaise samples arrive as a compacted clump of insects and debris. Breaking it apart is the system's real job, with parts for physics (A), bambu (B) and the optimizer (C).

Four Claude Code sessions work on this repo at the same time. Each has its own git worktree and branch, so none of them edits another's files. Merge into `main` through PRs on https://github.com/filiko/testSieveSorter.

| Session | Folder | Branch | Brief |
|---|---|---|---|
| Main / GitHub / coordination | `Documents\Github\testSieveSorter` | `main` | — |
| Bambu + visualization / 3D modeling | `Documents\Github\testSieveSorter-bambu` | `bambu-viz` | [bambu.md](bambu.md) |
| Physics engine test on the new laptop | `Documents\Github\testSieveSorter-physics` | `physics-bench` | [physics-handoff.md](physics-handoff.md) (current), [physics.md](physics.md), [demo-rig.md](demo-rig.md) A-B |
| Design optimizer (sim-driven, self-improving) | `Documents\Github\testSieveSorter-opt` | `design-opt` | [design-optimizer.md](design-optimizer.md), [demo-rig.md](demo-rig.md) C |

**Shared venv.** There is one venv, `testSieveSorter\.venv` (Python 3.12, from `requirements.txt`). Each worktree has a `.venv` junction that points at it, so `..\.venv\Scripts\python.exe` works from `cad\` and `sim\` in any folder. A `pip install` in one session changes the venv for all of them, so say so in the PR.

## Blocker shared by both [P] sessions: Smart App Control

This laptop (Lenovo 83F3, Windows 11) has **Smart App Control ON** (`VerifiedAndReputablePolicyState = 1`). It blocks the unsigned native DLLs in three wheels:

| Package | Status | Error |
|---|---|---|
| numpy, trimesh | OK | — |
| mujoco 3.17.0 | blocked | `DLL load failed while importing _specs: An Application Control policy has blocked this file.` |
| cadquery 2.8.0 (OCP) | blocked | same, on `OCP` |
| vtk 9.6.2 | blocked | same, on `vtkWebCore` |

Options; the user decides which one:
1. **WSL2 (Ubuntu) venv.** SAC doesn't apply inside WSL. Run the sim and CAD there and keep the repo on the Windows side (`/mnt/c/...`), or clone it inside WSL for speed. This needs no change to the Windows security policy. It's the recommended first try.
2. **Turn off Smart App Control** (Windows Security > App & browser control). It's **one-way**: it can't be turned back on without reinstalling Windows. Ask the user first.
3. Conda-forge builds. Probably also unsigned, so they'd likely be blocked too. Only worth a quick check.

Whichever option is chosen, record it here so the other session doesn't redo the work.

### Chosen: option 1, WSL2 (2026-10-25, set up by the bambu and physics sessions)

Smart App Control is still **on**; nothing in the Windows policy was changed.

- Distro: `Ubuntu` (26.04 LTS, WSL2), already installed. It sees all 24 cores but only about 15 GB RAM (the WSL default is half the host's). Raise it in `%UserProfile%\.wslconfig` (`[wsl2]` `memory=24GB`) if a sweep needs more.
- Venv: **`~/venvs/sieve`** inside WSL, built with uv on **Python 3.12.15** (uv-managed cpython, not Ubuntu's system 3.14). It has mujoco 3.17.0, cadquery 2.8.0 (OCP 7.9.3), vtk 9.6.2, numpy 2.5.4 and trimesh 5.2.0; `import mujoco` and `import cadquery` both work.
- uv is in `~/.local/bin`. Install packages with `uv pip install --python ~/venvs/sieve/bin/python ...` (there's no pip in the venv), and say so in the PR because the venv is shared.
- The repo stays on the Windows side. Run from the worktree's folder, for example:
  `wsl -d Ubuntu -- bash -lc "cd /mnt/c/Users/ajfil/Documents/Github/testSieveSorter-physics/sim && ~/venvs/sieve/bin/python sorter.py ..."`
  From Git Bash, set `MSYS_NO_PATHCONV=1` first, or it rewrites `/mnt/c/...` paths.
- CAD: build in WSL (cadquery), slice in **Windows** (`slice.py` on the Windows venv: it no longer imports cadquery, and Bambu Studio is a signed Windows app).
- VTK previews render through WSLg. Ignore the `bad X server connection` warning; the PNGs come out fine.
- Speed: the reference `inserts:mesh5,mesh2` run takes 45 s wall in WSL, against 517 s on the old machine. See `sim/PERF.md`.
- Incident: at 05:22 the physics session ran `python3 -m venv ~/venvs/sieve` on top of the uv venv while it was being built (most likely by the bambu session). That rewrote `pyvenv.cfg`. It has been repaired (uv-format `pyvenv.cfg`, stray `lib/python3.14` and `bin/pip*` removed), and the packages were not affected. Don't recreate this venv; add packages to it instead.

## Contact settings for sim runs (physics, 2026-10-25)

For every session that runs the sim (optimizer, bambu replays):
- **`sim/contact_rule.py`** picks the timestep and contact time constant from a design's tightest gate clearance and its stroke: `python contact_rule.py --clearance 0.14 --stroke constant_speed:amp_mm=14,speed_mm_s=41,ramp_s=0.01`, or `contact_rule.pick(clearance_mm, stroke)` from Python. It's a new file, so nothing that imports `optimize.py` or `sweep.py` changed. The measurements and the reasoning are in `sim/VERTICAL.md`, under "Contact rule".
- **`sim/verify.py`** is the second opinion on `sim/opt/winners.json`: it reruns the top 3 and the demo tray with fresh seeds, a heavy load and stiffer contacts, and writes `sim/opt/VERIFY.md`. It imports `optimize.py` and doesn't edit it.
