# Sorter sim

A MuJoCo simulation of grains and preserved insects moving through the team's sorters. Grains (rice, quinoa, chickpeas, pasta) are the calibration set: count them on the bench, then tune the sim until it matches. The team's pantry photo added white rice as photographed, brown, black and wild rice, chia and couscous; [GRAINS.md](GRAINS.md) has every grain's numbers, sources and what to measure. Insects are the real target. A three.js page replays every recorded run in the browser.

Status: first build, 2026-10-24. Nothing here is calibrated yet. Until the bench numbers in [BENCH.md](BENCH.md) are in, results rank designs against each other but don't predict real percentages.

## How it works

- **Engine.** MuJoCo 3.17 on the CPU. Units are mm, g and s.
- **Shaking.** The sim runs in the tray's own frame. The shake is applied as an extra force on every particle: gravity minus the tray's acceleration. This is exact for a tray that slides without rotating. Jets stay fixed in the lab while the tray moves under them.
- **Geometry.** Built from the same parameters as the CAD in `..\cad\`, so the sim follows the CAD when it changes.
- **Contacts.** Soft: a pressed grain sinks a little into the tray, and the tightest gates leave only 0.15–0.3 mm of room (quinoa in a 1.4 mm tunnel). `RunConfig`'s default (2 ms contact time constant at a 0.5 ms step) lets grains sink about 0.5 mm, so pass the settings from [PERF.md](PERF.md) explicitly, or let `contact_rule.py` pick them from the design's tightest clearance and the stroke (see [VERTICAL.md](VERTICAL.md), Contact rule). Each run reports its worst overlap, so you can check it against the clearance.

## Files

| File | What it is |
|---|---|
| `sorter.py` | Core: builds the scene, shakes it, records it, and counts where everything ends up |
| `rocking.py` | The seesaw: each box of a tower on its own hinge across its middle, neighbours in opposite phase, driven in the lab frame; also checks that neighbouring boxes never touch ([SEESAW.md](SEESAW.md)) |
| `clumps.py` | The real input: a clump of specimens (or grain surrogates) with leaves, twigs and dirt, packed into a ball and held by breakable bonds that weaken when wet; break-up, damage and leaf-blinding metrics ([CLUMPS.md](CLUMPS.md)) |
| `clump_study.py` | A clump across bond sets x spray on/off x seeds, in parallel, with a summary table |
| `designs.py` | Pool sorter, plus the registry for every design spec |
| `designs_holder.py` | BioKEA's holder tower with sieve inserts (glued mesh or printed), and the plinko layers |
| `grains.py` | Rice, quinoa, chickpeas, pasta (frozen for the optimizer), plus white rice as photographed, brown rice, black rice, wild rice, chia and couscous |
| [GRAINS.md](GRAINS.md) | Every grain kind: size, spread, density, shape, colour, sources and assumptions; the photo identification; what to caliper |
| `insects.py` | Generated preserved specimens: compact, elongate, long-legged |
| [INSECT_AUDIT.md](INSECT_AUDIT.md) | What `insects.py` gets right and wrong against real Malaise samples, and six ranked proposals |
| `spray.py` | Fixed jets: push, wetting, wet friction and capillary cling |
| `viewer.py` | Builds a standalone three.js replay page for a run |
| `record_view.py` | Renders a run's replay page to a frame-exact MP4 through headless Chrome |
| `side_by_side.py` | Real footage next to a sim clip, scaled, labelled and synced, for the demo |
| `sweep.py` | Batches of runs in parallel, with a report |
| `calibrate.py` | Fits contact parameters to bench counts, then checks them on a held-out run |
| `instab.py` | Stability probe: short runs that stop at the first MuJoCo reset and record the worst overlap, tray-wide and on gates only |
| `contact_rule.py` | Picks the timestep and contact time constant from a design's tightest gate clearance and the stroke |
| `verify.py` | Second opinion on the optimizer's winners: fresh seeds, a heavy load, per-design contacts; writes `opt/VERIFY.md` |
| [BENCH.md](BENCH.md) | What to measure on the bench, and which template each number goes in |

## Run

From `sim\`, with the repo venv (`..\.venv\Scripts\python.exe`):

```
python sorter.py --design pool:w5p0,t1p4 --mix rice=30,quinoa=30,chickpea=8,pasta=8 --stroke sine:amp_mm=3,freq_hz=10 --duration 10 --out out/runs/pool_demo
python viewer.py out/runs/pool_demo --open
```

Outputs go in `sim\out\`, which is not committed.

### Camera, recording and the real-vs-sim clip

> **Neither clip below shows the real motion.** Both runs slide the trays straight up and down as one block. The real trays each seesaw about their own pivot across their middle, ±20–30°, with neighbouring levels in opposite phase ([docs/SYSTEM.md](../docs/SYSTEM.md) §3). Both clips carry that warning in their captions, and both get re-rendered once the seesaw session's run is on `main`. The replay page is ready for it. A run that records `level_q` (frames × levels × 4, w x y z) and `scene["levels"][k]` (`pivot` in mm, `geoms` as indices into `scene["tray"]["geoms"]`) is drawn with each level turning about its own pivot. A single rocking tray frame (`tray_q` about `scene["tray"]["pivot"]`) works too (see `viewer.py`).

The replay page reads its camera from the URL: `view.html?cam=x,y,z&target=x,y,z&fov=35&aspect=16:9` (mm, lab frame; FOV is vertical). Set the angle by eye against a photo (the **Frame** menu sets the aspect ratio, **FOV** dollies so the tray keeps its size), then **Copy camera** copies the URL. **Record** plays the run once in real time and downloads a `.webm` with the zone labels and the sim clock drawn in; its frame rate depends on the machine. For the demo clip, render frame-exact instead and put it next to Forum's photo of the bench prototype (demo-rig.md part D):

```
wsl: python sorter.py --design inserts:5mm,2mm --mix pasta=15,rice=40,quinoa=40 --stroke sine:amp_mm=1.24,freq_hz=20,angle_deg=90 --duration 10 --dt 0.00025 --timeconst 0.0005 --fps 240 --out out/runs/demo_stack
python viewer.py out/runs/demo_stack
python record_view.py out/runs/demo_stack --view "?cam=108.1,-188.3,130.2&target=8,0,44&fov=45&aspect=4:3" --speed 0.2 --start 0 --duration 2.4 --height 960 -o out/runs/demo_stack/sim_stack_0p2x.mp4
python side_by_side.py --real ../../testSieveSorter/media/forum-2026-10-24/IMG_1316.JPG --sim out/runs/demo_stack/sim_stack_0p2x.mp4 --height 960 --real-label "Bench prototype" --sim-label "MuJoCo sim, uncalibrated" --caption "Sim at 1/5 speed. The photo shows one tray; the sim shows the stack: 5 mm tray over 2 mm tray over the catch pan.\nGrains are poured in; from t 1 s the whole stack shakes up and down (20 Hz, ±1.24 mm, assumed).\nPasta stays on 5 mm, rice mostly on 2 mm, quinoa falls to the catch. Shaken longer, rice leaks through end-first: 7 of 40 stay after 10 s."
```

- **The run** is the demo rig as it really is: separate trays stacked one above the other (demo-rig.md, 06:20 correction), 5 mm over 2 mm over the catch pan, shaken up and down, recorded at 240 fps. At the default 30 fps a 20 Hz shake aliases into a slow wobble that isn't there. It takes about 20 s to run.
- **What it shows** (VERTICAL.md, Result: the stacked rig): by t = 2.0 s all 15 pasta are on 5 mm, 31 of 40 rice are on 2 mm, and 32 of 40 quinoa are in the catch. Shaken straight up, rice stands on end and keeps leaking through the 2 mm holes: 21 stay at t = 4 s, 7 at t = 11 s. Shaking along the trays keeps 86-90% of it.
- **The camera** looks at the long wall with the mounting-tab end on the right, as in `IMG_1316.JPG`. It is 4:3 landscape, not the photo's 3:4: in portrait the stack only fits small, and the rice and quinoa on the lower levels disappear.
- **The clip** shows sim t = 0–2.4 s at 1/5 speed (12 s). The pour runs to t = 1 s, with no shaking. At 1/5 speed the 20 Hz shake plays as a visible 4 Hz bounce.
- **Forum's photos and the clip stay local:** `media/` is gitignored. Copy the clip into the main checkout's `media/`.

**The bench tower.** BioKEA's BugSorter hangs its holder boxes one above the other in an extrusion frame, with open air between them, each on a pivot across its middle, with a spray plate above and a water tub below. `pitch=` on an `inserts:` design spaces the boxes like that; the default is still rim on rim. For a ±25° seesaw with neighbours in opposite phase, SYSTEM.md asks for 80–100 mm, not the 65 mm used below. `viewer.py --rig bugsorter` draws the frame, the pivot axles and knobs (at the run's level pivots when it records them, otherwise at each box's centre), the spray plate, controller, tub and acrylic around the run. The tower is display only (`rig.py`), so it never touches the physics, and its sizes are estimated from the team's photo until someone measures the unit. A grain that bounces out through a gap lands on an invisible tub floor and counts as lost. The drop between boxes needs the stiffer contacts: 0.42 mm overlap at the production settings, 0.14 mm at these.

```
wsl: python sorter.py --design inserts:5mm,2mm,pitch=65 --mix pasta=15,rice=40,quinoa=40 --stroke sine:amp_mm=1.24,freq_hz=20,angle_deg=90 --duration 10 --dt 0.000125 --timeconst 0.00025 --fps 240 --out out/runs/demo_tower_stiff
python viewer.py out/runs/demo_tower_stiff --rig bugsorter
python record_view.py out/runs/demo_tower_stiff --view "?cam=-139.2,382.5,354.4&target=0,0,100&fov=45&aspect=7:8" --speed 0.2 --start 0 --duration 2.6 --height 960 -o out/runs/demo_tower_stiff/sim_tower_0p2x.mp4
python side_by_side.py --real <photo of the tower> --sim out/runs/demo_tower_stiff/sim_tower_0p2x.mp4 -o ../../testSieveSorter/media/tower_side_by_side.mp4 --height 960 --real-label "BugSorter tower (bench)" --caption "..."
```

On the replay page, the **Bench tower** checkbox hides the tower; in the URL, `rig=0` hides it and `jets=1` shows the jet cones, which are hidden by default when the tower is drawn and the spray is off.

`side_by_side.py` writes `..\media\demo_side_by_side.mp4`, capped under 19 MB. A photo as `--real` is held for the whole sim clip. A video works too (`--slow`, `--loops`). It also takes a Record-button `.webm` and fixes Chrome's colour-range tagging (light greys would otherwise clip to white).
