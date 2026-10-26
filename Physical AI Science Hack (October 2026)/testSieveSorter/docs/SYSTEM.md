# The system: read this first

The one description of what we're building that every session works from. **If a brief, a doc or the code disagrees with this file, this file wins.** Tell the main session (or the user) instead of working around it. Facts come from the user and the team's photos, as of Oct 25 ~10:55 PT. Assumptions are marked.

## 1. The job
- **Input:** a Malaise-trap sample. It's thousands of mostly tiny flies in ethanol, and often a **compacted clump**: a ball or mound of tangled insects, mixed with **leaves, twigs and dirt**.
- **Step 1, the real point of the system:** **break the clump apart, gently.** Specimens go on to imaging and DNA barcoding, so crushed bodies or snapped legs are failures.
- **Step 2:** **size-sort** the freed specimens into classes. BugPicker's are > 6 mm, 2–6 mm and < 2 mm. Leaves are held back on top; dirt goes to the bottom.
- Pasta, rice and quinoa are the bench surrogates for the size classes.

Details: [docs/sessions/clump-breakup.md](sessions/clump-breakup.md).

## 2. The hardware: separate trays, one above the other
- **The stack:** separate holder boxes (about 140 × 104 × 25 mm), each holding one sieve insert (131.4 × 95.4 mm). Coarse is on top, finer below, and a catch pan at the bottom. The breaker layer (step 1) goes on top.
- **The boxes are separate**, stacked one above the other. They aren't one block, and they aren't side by side.

## 3. The motion: each tray seesaws, neighbours alternate (confirmed by the user, 10:50)
- **Seesaw, ends tip.** Each tray rocks about **its own pivot across its middle**: a horizontal axis along the tray's width (Y), through its centre. The two short ends (−X and +X) go up and down in turn. **The angle is smaller than first said:** after seeing ±25° in the replay (11:20), the user said that's too wide. Renders at ±5°, ±10° and ±15° are being made so the user can pick. Until then, use **±10° as the default and sweep 5–15°**. Don't use 20–30°. Grains slide end to end across the sieve, as in a gold pan; rice on plastic starts sliding at about 22°.
- **Each level has its own pivot, and neighbours alternate:** opposite phase, so when one tray tips its −X end down, the trays above and below tip it up. The user chose this so material doesn't fly off. Whatever drops from a level lands on a tray tilted the other way.
- **Consequence for the hardware:** when neighbours tilt opposite ways, their facing ends close in by about L·sin θ (L ≈ 140 mm: 48 mm at 20°, 59 mm at 25°, 70 mm at 30°). Measured on the real holder solid (`cad/seesaw_tower.py`, PR #14, 3 mm clearance, pivot assumed at the box centre). The **+X mounting tab** decides the spacing:

  | Tilt | Pitch with the tab | Tab cut off |
  |---|---|---|
  | ±20° | 89.5 mm | 74.4 mm |
  | ±25° | 103.6 mm | 84.9 mm |
  | ±30° | 116.7 mm | 94.7 mm |

  A middle pivot doesn't need the tab, so cut it off for the seesaw: about 85 mm at ±25°. Otherwise allow about 105 mm. The sim should use a `pitch=` in this range and check that trays never touch at either end.
- **Not known yet (ASSUMED; sweep them):**
  - the exact angle (default ±10° while the user picks from the 5 / 10 / 15° renders; search 5–15°);
  - the period (the optimizer's seesaw uses 0.4–6 s per cycle);
  - the motion profile: constant angular speed with hard reversals (as the firmware drives its stage) or a smooth sine.
- **Superseded:** earlier notes in this file (rigid up-and-down translation, then "yaw about the +X tab") and the optimizer's default `rock_axis: x` (long sides tipping). The axis is **Y** (the ends tip). The pure translation strokes (`angle_deg`, the firmware stroke, VERTICAL.md, the leaderboards before 10:50) are simplifications; re-check them under the seesaw before the pitch quotes them.

## 4. Liquid
Samples are in ethanol, and the rig sprays from fixed jets above. `sim/spray.py` models push, wetting and capillary adhesion. Wetting should also weaken clump bonds.

## 5. What the sim models, and what it doesn't
- **Modelled:** the trays (with their real mount point and rocking), the particles (specimens, grains, clumps, debris), the stroke and the spray.
- **Not modelled:** the tool, the motor, the frame, the hand. The frame in the replay (`sim/rig.py`) is display only.
- **The seesaw in the sim:** levels rock **differently** (alternating), so one shared non-inertial tray frame can't do it, and neither can the optimizer's current `rocking()` wrapper, which turns every particle in phase.
  - Run seesaw cases in the **lab frame**, with **each level its own body on a hinge** (axis Y through the level's centre).
  - Prescribe its angle kinematically: write the hinge `qpos` / `qvel` each step from θ_k(t) = ±Θ·profile(t), the sign alternating by level. Gravity stays −Z.
  - Then contacts see the real tray velocities, and nothing approximates the rotation.
  - Translation strokes keep the existing tray-frame path.
- **Recording, so the replay shows each level rocking:**
  - `level_q`: frames × levels × 4 (w x y z), each level's orientation in the lab;
  - `scene["levels"][k]`: that level's `pivot` (mm) and the ids of the geoms that belong to it.
  - **The viewer side is done (PR #13, merged 11:15).** Seesaw session: **don't edit `viewer.py` / `viewer_template.html`.** Record exactly this:
    - `level_q`: frames × levels × 4, w x y z;
    - `scene["levels"][k] = {"pivot": [x, y, z] mm, "geoms": [indices into scene["tray"]["geoms"]]}`;
    - in a lab-frame run, `tray_d` = 0.
  - The display rig (`sim/rig.py`) now hangs each tray on an axle across its middle.
- **Clumps** (clump session): `sim/clumps.py`. Specimens are joined by breakable bonds (`eq_active` off above a force that drops with wetness), with a minimal hook in `sorter.py`'s step loop. Debris: leaf / twig / dirt. See clump-breakup.md part A.
- **The sim ranks designs; it does not predict real percentages until it's calibrated against bench counts.**

## Who owns what
| Area | Session |
|---|---|
| Per-level seesaw in the sim (`sim/rocking.py` + minimal hooks in `sorter.py`), per-level recording, the rocking tower run | **seesaw** (`seesaw-tower`, new at 10:55) |
| Clumps and debris (`sim/clumps.py` + a minimal hook in `sorter.py`), break-up metrics | **clump** (`clump-sim`, new at 11:15; physics stays on grains and verification) |
| `sim/optimize.py`, `sim/designs_*.py` for searched families, `sim/opt/` | optimizer (`design-opt`) |
| `cad/`, slicing, `sim/viewer*`, `sim/rig.py`, replays and clips | bambu (`bambu-viz`) |
| `README.md`, `docs/`, this file, merging PRs | main |

Seesaw and physics both touch `sorter.py`. Keep those edits to small hooks, put the logic in your own module, and merge `origin/main` before you open a PR.
