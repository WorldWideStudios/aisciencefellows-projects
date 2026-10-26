# filtration-robot

Demo-day system: a camera looks at a petri dish of mixed objects (pebbles, dry noodles, seeds...), measures their sizes, picks which filters to use, and an SO-101 robot arm swaps those filters into a 3-slot vertical filtration rig.

```
[1] vision        →   [2] planner              →   [3] arm
dish photo → sizes →   current layout + target  →   pick(slot) / place(slot)
→ filter plan          → list of moves              with checks
```

## Layout

| Path | What |
|---|---|
| `arm/` | SO-101 tools: motor probe, position watcher, leader→follower mirroring, calibration backups |
| `vision/` | Object sizing from dish photos (`dish_sizer.py`), sample images |
| `CLAUDE.md` | Project notes: hardware facts, design decisions, build order |

## Setup (Windows)

```powershell
python -m venv $env:USERPROFILE\lerobot-env
& $env:USERPROFILE\lerobot-env\Scripts\python.exe -m pip install -r requirements.txt
```

Commands below use that environment's `python.exe` directly; no activation needed.

## Arm

- **Power:** leader arm on the **5 V** supply, follower on **12 V**. 12 V on the leader triggers over-voltage errors on its motors.
- **Ports:** leader = COM5, follower = COM6 (check with `arm/probe_arms.py COM5 COM6`; the leader's motors read ~5 V).
- **Mirror the leader:** `arm\mirror.cmd` (or `mirror` if it's copied into a folder on your PATH). Hold the follower before pressing Ctrl+C: it goes limp when mirroring stops.
- **Teach and repeat:** `arm\teach.py` saves named positions while the follower copies the leader, then replays routines (pick, place, move a filter between the rig and storage, dump the dish) on the follower alone. Step-by-step guide: [arm/TEACHING.md](arm/TEACHING.md). With the wrist camera, it reads each filter's marker before a pick (`pick rig/top A` only takes filter A), `scan` notes which filter is in every slot, and `teach.py inventory` shows it. Add `--practice` to try anything without the arm. Tests: `cd arm; python -m unittest test_motion`.
- **Calibration backups:** `arm/calibration/` mirrors `%USERPROFILE%\.cache\huggingface\lerobot\calibration\` (`robots\so_follower\`, `teleoperators\so_leader\`). Copy them back if that cache is lost.

```powershell
& $env:USERPROFILE\lerobot-env\Scripts\python.exe arm\probe_arms.py COM5 COM6   # voltage, errors, positions (read-only)
& $env:USERPROFILE\lerobot-env\Scripts\python.exe arm\watch_arm.py COM6 15       # record min/max positions while you move joints
```

## Vision

Cameras are picked by name because Windows renumbers them when one is plugged in or out. `vision\cameras.py` lists them; `vision\live_view.py` shows one live with a focus meter and saves full-resolution photos (Space) to `vision\captures\`:

```powershell
& $env:USERPROFILE\lerobot-env\Scripts\python.exe vision\cameras.py                 # list cameras
& $env:USERPROFILE\lerobot-env\Scripts\python.exe vision\live_view.py --camera XWF --rotate 180  # USB webcam (1920x1080); T turns the picture live
```

```powershell
& $env:USERPROFILE\lerobot-env\Scripts\python.exe vision\dish_sizer.py vision\samples\dish_phone_01.webp --px-per-mm 9.12 --out vision\output\annotated.png --json vision\output\objects.json
```

Outputs each object's length and width in mm (width decides whether it passes a filter) plus an annotated image. Without `--px-per-mm`, the scale comes from `vision\calibration.json`, measured for the mounted webcam (13.9 px/mm). The scale changes whenever the camera height or angle changes, so after moving the camera, photograph a mm ruler lying flat **beside** the dish (never under it) and re-measure. Measure it from a ruler in the photo with a strip across its mm ticks that avoids glare and the dish rim:

```powershell
& $env:USERPROFILE\lerobot-env\Scripts\python.exe vision\ruler_scale.py vision\samples\dish_phone_02.webp --along vertical --strip 333 348 60 440 --strip 333 348 1040 1330
```

| Sample | px/mm |
|---|---|
| dish_phone_01 | 9.12 |
| dish_phone_02 | 12.89 |
| dish_phone_03 | 11.84 |

Then turn the measurements into a filter plan for the rig (filters stacked coarse on top to fine at the bottom):

```powershell
& $env:USERPROFILE\lerobot-env\Scripts\python.exe vision\filter_plan.py vision\output\objects.json --json vision\output\plan.json --image vision\samples\dish_phone_01.webp --out vision\output\plan.png
& $env:USERPROFILE\lerobot-env\Scripts\python.exe vision\filter_plan.py vision\output\objects.json --target 3 6   # catch 3-6 mm objects on one shelf
```

- **split** (default): picks the 3 filters that sort the objects into the most separate groups, with hole sizes as far from any object as possible.
- **target**: picks filters so one shelf catches objects whose width is in the given range (later selectable with a microcontroller button).
- **coarse** (for piles): from the recogniser's rough estimate, picks filters that give the largest common types a shelf of their own first. Each type's width comes from `vision/types.json`.

```powershell
& $env:USERPROFILE\lerobot-env\Scripts\python.exe vision\pile_types.py predict photo.png --out vision\output\types.png --json vision\output\estimate.json
& $env:USERPROFILE\lerobot-env\Scripts\python.exe vision\filter_plan.py --estimate vision\output\estimate.json --json vision\output\plan.json
```

- Hole sizes live in `vision/filters.json` (F1–F3 measured; F4 and F5 are targets until they're printed and measured).
- Tests: `cd vision; python -m unittest test_filter_plan`.

### Filter markers (wrist camera)

Each filter carries a printed ArUco marker (4×4 set) so the wrist camera knows which filter it's holding. `vision/filter_markers.pdf` has markers A–E (ids 1–5, mapped in `filters.json`) at 15, 20 and 25 mm: print at 100% / actual size (check the 50 mm bar), cut along the dotted line (the white margin is needed), and stick the size that fits on each filter.

```powershell
& $env:USERPROFILE\lerobot-env\Scripts\python.exe vision\markers.py sheet --sizes 15 20 25           # regenerate the sheet
& $env:USERPROFILE\lerobot-env\Scripts\python.exe vision\markers.py read photo.png --out marked.png    # which filters are in a photo
& $env:USERPROFILE\lerobot-env\Scripts\python.exe vision\live_view.py --camera CAM1 --save-dir vision\captures\wrist   # wrist camera live
```

Photo tips that matter more than code: light from underneath (backlight) or a plain matte coloured background, camera straight overhead at a fixed height, full-resolution images, objects not touching.
