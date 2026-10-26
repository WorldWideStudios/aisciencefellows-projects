# The seesaw tower in the sim

Seesaw session, 2026-10-25. Task: [docs/SYSTEM.md](../docs/SYSTEM.md) §3 and §5. Each tray rocks about its own pivot across its middle, and neighbours run in opposite phase. Code: `rocking.py`, plus small hooks in `sorter.py`.

## How it works

- **One body per level.** `stroke={"profile": "seesaw", ...}` on an `inserts:` tower puts each holder box on its own body with a hinge. The insert, its invisible notch covers, and (for the top box) the walls and lid above it all ride on that body. The catch pan is the bottom level. The hinge axis is **Y** through the box's centre: x = y = 0, half way up the box. Only the tub floor of a spaced tower stays in the lab.
- **Lab frame, prescribed angles.** Gravity stays −Z. Before every step, each hinge's `qpos` and `qvel` are written from θ_k(t) = sign_k · deg · f(t / period_s). The sign is +1, −1, +1, … from the top down. θ > 0 tips the +X (tab) end down. Contacts see the trays' real velocities, so nothing approximates the rotation. Each level body weighs 1e6 g, with its mass on the hinge axis, so particles can't push it within a step and gravity has no torque on it.
- **Tray–tray contacts are off,** because the trays are driven. Whether neighbours touch is checked geometrically instead (below).
- **Zones turn with their level.** A particle's zone is tested in the rest frame of the level that holds that zone (`assign_zones(..., local=)`). The bounds for "lost" grow to cover every box at full tilt.
- **Translation strokes are unchanged.** They still run in the tray frame, and a translation run gives bit-identical `traj.npz` and `scene.json` to `main`'s `sorter.py`. A seesaw run has no translation on top.

### Stroke options (`--stroke seesaw:k=v,...`, all optional)

| key | default | meaning |
|---|---|---|
| `deg` | 10 | amplitude either side of level, degrees (SYSTEM.md: ±10° while the user picks from the 5 / 10 / 15° renders; search 5–15°) |
| `period_s` | 2.0 | one full cycle (the optimizer searches 0.4–6 s) |
| `shape` | `constant_speed` | constant angular speed with reversals smoothed over `ramp_s`, as the firmware drives its stage; or `sine` |
| `ramp_s` | 0.02 | reversal time for `constant_speed` |
| `ramp_in_s` | 0 | ease the amplitude in from zero after the settle (0 starts at full speed, as the firmware does) |
| `alternate` | 1 | 1: neighbours in opposite phase; 0: all levels in phase |
| `catch` | 1 | 1: the catch pan rocks as the next level down; 0: it stays level |
| `vib_mm` | 0 | a small fast buzz on top of the seesaw (the handheld tool's): sine amplitude of the whole tower, mm; 0 is off |
| `vib_hz` | 40 | its frequency (the puck resonates at 40 Hz). Peak acceleration is vib_mm · (2π vib_hz)²: 0.3 mm at 40 Hz is 1.9 g |
| `vib_angle_deg` | 90 | its direction: 0 along X (the tilt direction), 90 straight up |
| `vib_deg` | 0 | a fast angular buzz added to every hinge, degrees, in each level's own phase (same `vib_hz`) |

The buzz shakes every level together, so `sorter.py` applies it the way it applies any translation stroke: a uniform pseudo-force (exact for a shared translation), recorded as `tray_d`, so the viewer draws it with no changes. The hinges turn inside that translating frame. With `vib_mm=0` and `vib_deg=0` a seesaw run is the same as before.

Angle, period and profile are all **assumed** (SYSTEM.md §3). So are the pivot height (half way up the box) and whether the catch pan rocks.

### Recording

- `traj.npz` → `level_q`: frames × levels × 4 (w x y z), each level's orientation in the lab. Particle `pos` / `quat` are in the lab frame (`tray_d` stays zero).
- `scene.json` → `levels[k]`, top to bottom: `name`, `zone`, `pivot` (mm), `axis`, `sign`, `amp_deg`, `body_id`, `mj_geom_ids` (MuJoCo geom ids), and `geoms` (indices into `scene["tray"]["geoms"]`, which leaves the invisible lids out).
- `results.json` → `seesaw`: the stroke options, the levels, the pitch and the clearance check.

### Viewer

There are no viewer edits on this branch. Bambu's viewer (PR #13) already reads `level_q` and each level's `pivot` and `geoms`, and ignores the extra keys. `--rig bugsorter` draws the axles at the recorded level pivots. One difference: the replay draws the zone boxes level, while the sim tests each zone in its level's frame.

## Do neighbouring trays touch? The level pitch they need

When neighbours tilt opposite ways, their facing ends close in. `rocking.py` poses the levels at 41 points over a cycle and finds the closest approach between neighbouring boxes with MuJoCo's `mj_geomDistance` (the invisible lids are left out). The trays only move by their prescribed angles, so this is exact for the geometry as modelled. Every run reports it, and prints `TOUCHING` if the boxes overlap.

The worst point is the **+X mounting tab.** It sticks 22 mm past the end, so it sits 92 mm from the pivot, against 70 mm for the plain −X end. The tabs of neighbouring boxes line up (both at y ≈ 0), so they meet tip to tip. Pitch is box bottom to box bottom:

| amplitude | pitch where the boxes just touch, with the tab (CAD today) | for 5 mm clearance, with the tab | just touch, without the tab | 5 mm clearance, without the tab |
|---|---|---|---|---|
| ±20° | 86.5 mm | 91.4 mm | 71.5 mm | 76.4 mm |
| ±25° | 100.4 mm | 105.5 mm | 81.9 mm | 86.9 mm |
| ±30° | 113.7 mm | 118.7 mm | 91.7 mm | 96.7 mm |

These match the closed form pitch = 2 (a sin θ + (H/2) cos θ) + clearance. Here a = 92 mm with the tab and 70 mm without, and H = 25 mm. At 3 mm clearance the sim gives 89.4 / 103.5 / 116.8 mm with the tab and 74.4 / 84.9 / 94.7 mm without. Bambu measured the real holder solids in `cad/seesaw_tower.py` (PR #14, SYSTEM.md §3) and got the same to within 0.1 mm. **The 65 mm pitch the replay assumed is too tight at any amplitude in this range.** At 65 mm the boxes touch from ±12.8° with the tab (±17.1° without). For the default ±25°, a pitch of **110 mm** leaves 9.6 mm between the tabs. If the seesaw's pivot pins replace the +X tab, about 87 mm will do. That's for Bambu's CAD and rig.

```
wsl: python rocking.py inserts:5mm,2mm,pitch=110 --deg 20,25,30 --clear 5
```

## The demo run: inserts:5mm,2mm with pasta, rice and quinoa

```
wsl: python sorter.py --design inserts:5mm,2mm,pitch=110 --mix pasta=15,rice=40,quinoa=40 --stroke seesaw:deg=25,period_s=2,shape=constant_speed --duration 10 --dt 0.000125 --timeconst 0.00025 --fps 60 --out out/runs/seesaw_tower
python viewer.py out/runs/seesaw_tower                 # add --rig bugsorter for the tower frame and the axles
```

The setup: 5 mm over 2 mm over the catch pan, 110 mm apart (9.6 mm between the tabs at full tilt). The grains are poured in and settle for 1 s, then 10 s of seesaw follow (5 cycles). Each tray swings ±25° at constant angular speed, 2 s per cycle, and neighbours run in opposite phase. It took 285 s of wall time on one core for 11 s simulated (88,000 steps). The largest overlap was 0.18 mm on the trays and 0.06 mm between particles, with no unstable resets. The replay is `sim/out/runs/seesaw_tower/view.html` (2 MB, gitignored).

Counts on 5 mm / on 2 mm / in the catch / lost:

| t (s) | pasta (15) | rice (40) | quinoa (40) |
|---|---|---|---|
| 1.0 (end of the pour, still level) | 15 / 0 / 0 / 0 | 19 / 21 / 0 / 0 | 11 / 29 / 0 / 0 |
| 2.0 | 15 / 0 / 0 / 0 | 7 / 28 / 4 / 1 | 5 / 12 / 22 / 1 |
| 3.0 | 15 / 0 / 0 / 0 | 3 / 32 / 4 / 1 | 3 / 8 / 28 / 1 |
| 5.0 | 15 / 0 / 0 / 0 | 1 / 32 / 6 / 1 | 3 / 2 / 34 / 1 |
| 11.0 (end) | **15** / 0 / 0 / 0 | 1 / **31** / 7 / 1 | 3 / 0 / **36** / 1 |

What it shows:

1. **The seesaw tower sorts the three classes within two or three cycles.** All the pasta stays on 5 mm, 31 of the 40 rice end on 2 mm and 36 of the 40 quinoa end in the catch. Nothing changes after about t = 5 s except one more rice grain leaking through 2 mm end-first. Shaken straight up, the old rim-on-rim stack kept only 7 of 40 rice on 2 mm by 11 s (README), so tipping the ends up and down is much gentler on the 2 mm class. (`results.json` gives rice a recovery of 0.25. The sim's ideal rule sends rice to the catch, because a 2.0 × 1.7 mm grain fits a 2 mm square hole corner to corner. For the demo, rice on 2 mm is the outcome we want.)
2. **2 of 95 grains bounced out of the catch pan's low end** (1 rice, 1 quinoa, both at t = 1.3–1.5 s, when most of the material comes down). Each one fell about 100 mm from the 2 mm level onto the pan while the pan was tipping its +X end down (14–20°). It bounced toward the low end and cleared the end wall. At that tilt, the top of the low end wall is about level with the middle of the pan floor. The holder box's 22 mm walls are low for a tray that tips 25° and catches grains falling 100 mm. Higher end walls or a lip on the catch pan (and maybe on every box) would stop this. On the bench tower those grains would land in the tub. In the sim they fall to the invisible tub floor, and past its ±200 mm edge, so the viewer clamps their positions.
3. **Grains can ride "rails" that run along X.** 3 quinoa and 1 rice never leave the 5 mm tray. The rice lies on top of the middle rib. Two quinoa lie on the 3.2 mm solid strips between that rib and the first row of holes, and one is balanced on a 1.2 mm bar. A seesaw about Y only tips the tray along X, so nothing pushes those grains sideways: they slide end to end along the rail forever. On the bench, vibration and the spray would probably knock them off. In the CAD, narrower solid strips beside the middle rib would help, or a little roll (tilt about X) in the motion.
4. **The trays never come closer than 9.6 mm** (tab to tab, at full tilt).

Angle, period and profile are still assumptions. This is one seed with the default friction, so read it as "the motion works and sorts", not as a percentage to quote (SYSTEM.md §5).

## Seesaw + vibration: does a buzz move the stuck quinoa and chia? (12:30)

The 11:20 angle renders (PLAN.md) left half the quinoa and most of the chia on the 5 mm tray at every angle from ±5° to ±15°. A gentle seesaw is below the ~22° at which grains slide on plastic, so they sit on solid ribs instead of finding a hole. This test puts a 40 Hz vertical buzz of the whole tower on top of the ±10° seesaw.

```
wsl: python sorter.py --design inserts:5mm,2mm,pitch=85 --mix pasta=8,chickpea=4,rice=12,white_rice=12,brown_rice=12,black_rice=12,wild_rice=10,quinoa=20,couscous=20,chia=25 --stroke seesaw:deg=10,period_s=2,vib_mm=0.3,vib_hz=40 --duration 8 --dt 0.000125 --timeconst 0.00025 --fps 30 --out out/runs/vib_a0.3
```

All 10 grain kinds (135 grains), 5 mm over 2 mm over the catch pan at an 85 mm pitch, ±10° at constant speed, 2 s per cycle, neighbours in opposite phase. After a 1 s settle, 8 s of seesaw (4 cycles). End counts, on 5 mm / on 2 mm / in the catch / lost:

| kind (n) | buzz 0.15 mm (1.0 g) | buzz 0.3 mm (1.9 g) | buzz 0.5 mm (3.2 g) |
|---|---|---|---|
| pasta (8) | **8** / 0 / 0 / 0 | **8** / 0 / 0 / 0 | **8** / 0 / 0 / 0 |
| chickpea (4) | **4** / 0 / 0 / 0 | **4** / 0 / 0 / 0 | **4** / 0 / 0 / 0 |
| rice (12) | 4 / 7 / 1 / 0 | 0 / 2 / 10 / 0 | 0 / 3 / 9 / 0 |
| white_rice (12) | 3 / 7 / 2 / 0 | 0 / 4 / 7 / 1 | 0 / 6 / 6 / 0 |
| brown_rice (12) | 1 / **11** / 0 / 0 | 0 / **10** / 2 / 0 | 0 / **11** / 1 / 0 |
| black_rice (12) | 0 / **12** / 0 / 0 | 0 / **12** / 0 / 0 | 0 / **12** / 0 / 0 |
| wild_rice (10) | 2 / 6 / 2 / 0 | 0 / **8** / 2 / 0 | 0 / **9** / 1 / 0 |
| quinoa (20) | 0 / 3 / **17** / 0 | 0 / 0 / **20** / 0 | 0 / 0 / **20** / 0 |
| couscous (20) | 0 / 0 / **20** / 0 | 0 / 0 / **20** / 0 | 0 / 0 / **20** / 0 |
| chia (25) | 2 / 0 / **23** / 0 | 0 / 0 / **24** / 1 | 0 / 0 / **25** / 0 |

What it shows:

1. **A buzz of 0.3 mm or more clears the 5 mm tray of everything that should pass.** No quinoa, couscous or chia is left on 5 mm after t = 3 s. All of the quinoa and couscous and 24–25 of the 25 chia end in the catch. At 0.15 mm (1 g) 2 chia and a few rice grains still sit on the 5 mm ribs.
2. **The cost is the long white rices on 2 mm.** The buzz stands the 2.0 mm wide `rice` and `white_rice` grains up in the 2 mm holes. At 0.3 mm, 10 of 12 `rice` and 7 of 12 `white_rice` reach the catch, against 1 and 2 at 0.15 mm. The sim's ideal rule puts both kinds in the catch anyway, since they fit a 2 mm square hole corner to corner (see the demo run above). Brown, black and wild rice stay on 2 mm at every amplitude.
3. **Pasta and chickpea stay on 5 mm in every case.**
4. **It's stable.** There were no resets, the largest overlap was 0.21 mm on the trays and 0.07 mm between particles, and the boxes never came closer than 28.4 mm.
5. **The no-buzz baseline from this exact setup is missing.** That run was stopped when the machine ran low on memory, before it wrote anything. The only no-buzz reference is the 11:20 renders (9 kinds, the same pitch and period, 8 s).

One seed, default friction, uncalibrated (SYSTEM.md §5). Read it as "the buzz moves the stuck fines", not as percentages. Ribs across the tilt (bambu's `5mm_across` insert) haven't been tried here yet.

## Limits

- The trays are driven exactly, so nothing about the motor, pins, lever or frame is modelled (SYSTEM.md §5).
- Particles that bounce out between boxes fall to the invisible tub floor and count as `lost`.
- Seesaw runs are slow cycles (seconds). The stiff contact settings (dt 0.125 ms, time constant 0.25 ms) are for the 100 mm drops between levels, not for the rocking itself.
- The optimizer's `rocking()` wrapper in `optimize.py` (`stroke["rock"]` with profile `none`) turns every particle in one shared tilted frame, so it can't alternate levels (SYSTEM.md §5). It can switch to emitting `{"profile": "seesaw", "deg": ..., "period_s": ...}` and drop the wrapper. The key is deliberately not its `stroke["rock"]`, so the two can't both act on one run.
