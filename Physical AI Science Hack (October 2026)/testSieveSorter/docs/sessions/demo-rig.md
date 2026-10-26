# Task: simulate the demo rig, with up-and-down shaking

> **Read [docs/SYSTEM.md](../SYSTEM.md) first** (added 10:30). It's the one description of the system: the input is a clump; the rig is separate trays one above the other, each held at its +X tab and overhanging, so they **rock**. It overrides this brief where they differ.

> **Correction (06:20, from the user): the rig is separate trays stacked one above the other**, not one tray. Coarse is on top and finer below, with a catch pan at the bottom; the whole stack shakes up and down together. Forum's photo shows one of those trays. In the sim, that's the holder tower: **`inserts:5mm,2mm`** (one insert per holder box, the boxes stacked straight up, the catch pan under them; see `sim/designs_holder.py`). Use a 3-class mix so each level holds one class: pasta stays on 5 mm, rice on 2 mm, quinoa in the catch. `inserts:5mm` (one tray plus the catch pan) is just a single level of it. The VERTICAL.md results so far are on that single level only.

**What the user wants (Oct 25, ~05:50 PT).** This replaces the stroke-measurement idea in `forum-footage.md`.
1. **Forum's photos are the demo example.** The rig: a white 3D-printed square-grid sieve tray, with ribbed windows and a pull tab (it looks like `cad/sieve_insert.py`'s 5 mm insert), bolted onto a handheld DeWalt 20V MAX cordless tool. It sorts tube pasta (ditalini) from rice and darker grains.
   **The sim models only the tray, the grains and the shaking motion. Do NOT model the tool:** no drill or saw geometry, no motor, no handheld dynamics. The tool is just what moves the tray, and in the sim that's the stroke (a translation of the tray).
2. **The video shows the motion we want: up and down.** Today the sim shakes along the tray's flow axis, horizontally. Adding vertical motion, and combined angled "throwing" motion like lab vibratory sieve shakers use, is the big improvement.

Photos: `C:\Users\ajfil\Documents\Github\testSieveSorter\media\forum-2026-10-24\` (local only, gitignored). Deadline: submission at 2:30 PM PT.

## A. Vertical and angled strokes (physics session, `physics-bench`)
- **Already there:** `sorter.py` takes `stroke["axis"]`, a 3-vector (line ~247), and sets tray-frame gravity to `-a(t)·axis - g·z`. That's exact for any pure translation, so vertical is `axis = (0,0,1)`.
- **The gap:** the CLI's `--stroke profile:k=v,...` can't pass a vector. Add `angle_deg`: 0 = along the design's flow axis, 90 = straight up, in between = angled throw. Keep `axis` for the Python API.
- **Stability:** vertical impacts raise contact speeds. Check penetration against the gate clearance, and QACC warnings, with the `instab.py` tooling. If a smaller dt is needed, say what it costs in runtime.
- **The comparison that answers the question:** on the demo tray (B below) with the demo mix, compare 0°, 45° and 90° at the **same peak acceleration**. Report recovery, contamination, jams and t90 per class across the 3 friction sets. Write it up in `sim/VERTICAL.md`.
- **Get A onto `main` early** (PR). The optimizer and bambu sessions both depend on it.

## B. Demo-tray design spec (physics, small)
- Make sure a single 5 mm printed insert builds as a design, e.g. `inserts:5mm`. Add it if only two-insert stacks build today.
- Demo mix: pasta (ditalini, already in `grains.py`) + rice. Add a dark rice variant only if it changes anything physically; colour alone doesn't matter to the sim.
- Stroke ranges (amplitude, frequency) are plain assumptions; the tool itself isn't modelled. Write them in `sim/VERTICAL.md`.

## C. Optimizer (optimizer session, `design-opt`)
- Once A is on `main`, add **stroke angle (0–90°)** to the search space, alongside amplitude and frequency, and rank designs × shake directions together.
- Include the demo tray (`inserts:5mm`) as a baseline row on the leaderboard, so the winners are measured against what the team actually built.

## D. Demo visual (bambu session, `bambu-viz`)
> **06:15:** A is on `main` (PRs #2 and #3). The up-and-down demo-tray run for the viewer is in `sim/VERTICAL.md` under Reproduce: `sorter.py --design inserts:5mm --mix pasta=15,rice=40 --stroke sine:amp_mm=1.24,freq_hz=20,angle_deg=90 --duration 10 ...`. The sim says vertical sorts the demo mix fine, just 2-3x slower than shaking along the tray.

- In the sim viewer: **the stack of separate trays** (`inserts:5mm,2mm`: 5 mm tray above the 2 mm tray above the catch pan, no tool) with pasta + rice + quinoa, the whole stack shaken **up and down**. The physics session is rerunning the vertical comparison on the stack (physics-handoff.md step 2). Until that lands, make the run yourself with the command above, using `--design inserts:5mm,2mm --mix pasta=15,rice=40,quinoa=40`.
- Viewer work as before: camera from URL params, a **Copy camera** button, and a **Record** button (`canvas.captureStream()` + `MediaRecorder`) in `sim/viewer_template.html`.
- Match the viewer camera to one of Forum's photos (`IMG_1316.JPG` shows the tray on the tool from the side; `IMG_1318.JPG` is top-down).
- **Side-by-side:** Forum's photo (a still) next to the sim replay, labelled "Bench prototype" and "MuJoCo sim, uncalibrated". Write it to `media/demo_side_by_side.mp4` in the main checkout. It's local only and never committed.
