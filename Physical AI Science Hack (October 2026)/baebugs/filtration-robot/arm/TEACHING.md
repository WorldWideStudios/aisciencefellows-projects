# Teaching the arm

You move the **leader**, the follower copies it, and you save named positions ("poses"). Routines (pick, place, move a filter, dump the dish) are built from those poses. All commands run from the project folder in PowerShell.

## 0. Before you start

- **Power:** leader on the **5 V** supply, follower on **12 V**. Keep a hand near the follower's power switch.
- **Close anything else using the arms** (`mirror`, `lerobot-teleoperate`): only one program can use the COM ports.
- **The dish needs the same spot every time** the arm grabs it. Push it into a corner guide (two strips of tape, a block, a 3D-printed ring). The arm repeats positions; it doesn't look for the dish (yet).
- Rehearse anywhere, without the arm: `& $env:USERPROFILE\lerobot-env\Scripts\python.exe arm\teach.py --practice teach`

## 1. Start the teaching session

```powershell
cd $env:USERPROFILE\Documents\filtration-robot
& $env:USERPROFILE\lerobot-env\Scripts\python.exe arm\teach.py teach
```

The follower glides over to the leader and copies it. Type `todo` any time to see what's left, `save NAME` to store a pose (saving again overwrites it), `where` to see joint values.

## 2. Teach these poses, in this order

| Pose | How to set it |
|---|---|
| `rest` | Folded, resting on its own support. The arm goes limp here at the end of every run. |
| `gripper/open` | Gripper wide open (only the gripper value is used). |
| `gripper/closed` | Gripper fully closed **on nothing**. Used to spot a missed grab. |
| `rig/carry` | Facing the filter shelf, **pulled in close to the base**, holding a filter level, high enough to turn freely. The arm only turns between the two sides from here. |
| `rig/top/front` | **Holding a filter**, lined up straight in front of the top slot at the same height as the slot, far enough out that the back of the filter clears the shelf. |
| `rig/top/in` | Slide straight in from `front`: filter seated, gripper around its handle. Save it with the gripper **open**; the routine closes it. |
| `rig/middle/...`, `rig/bottom/...` | Same `front` and `in` for the other two slots. |
| `storage/carry` | Same as `rig/carry`, facing the storage shelf. Check the turn between the two carry poses is clear of the extrusion. |
| `storage/top/...` etc. | `front` and `in` for each storage slot. |
| `dish/above` | Gripper open, just above the dish's rim. |
| `dish/grip` | Fingers around the rim, ready to close. |
| `dish/lift` | Dish lifted clear of the table, level. |
| `pour/above` | Dish level, above the top filter, high enough to clear the shelf. |
| `pour/tilt` | From `pour/above`, roll the wrist to pour. |

Tips: move the leader slowly and let the follower settle before `save`. For `front` → `in`, the routine moves in a straight-ish line between them, so keep them lined up. If two poses are far apart, the arm moves straight between them in joint terms, so teach an extra pose if that path could hit something and add it to the routine in `layout.json`.

## 3. Test, in this order

Type these in the same session. Mirroring pauses while they run; type `follow` to go back to copying the leader. **Ctrl+C** stops a routine and the arm holds where it is.

1. `goto rest`, `goto rig/carry`: single poses, no routing.
2. `check rig/top` (and each slot): goes in and back out with the gripper open. Nothing is grabbed.
3. With a filter in the top slot: `pick rig/top`, then `place rig/top` to put it back.
4. `move rig/top storage/top`, then `move storage/top rig/top`.
5. With an **empty** dish first: `dump`. Then with a few objects.

If a pick stops with "missed grab", the gripper closed on nothing: re-teach that slot's `in` pose so the fingers sit around the handle.

## 3b. Wrist camera and filter markers

With the wrist camera plugged in (`wrist_camera` in `layout.json`, set to `CAM1`), the arm reads each filter's ArUco marker from the slot's `front` pose before going in. Close the live view first: only one program can use the camera.

- **While teaching each `front` pose:** with a filter in the slot, type `look rig/top` (the follower keeps copying the leader). It should name the filter, e.g. `rig/top: A (F1) (marker 1, +12 px across / -30 px down from the middle)`. If it says `no marker in view`, adjust the pose (or the camera angle) until it reads, then `save` again. Close to the middle (small px numbers) is best.
- `scan`: visits every slot's `front` and notes which filter is where (no marker = empty). `inventory` shows the result.
- `pick rig/top A` (or `F1`): only takes the filter if the camera sees A there; otherwise it stops in front of the slot with the gripper open. Without a filter name, `pick` takes whatever is there and notes what it was. `move FROM TO A` works the same way.
- Picks and places keep `arm/inventory.json` up to date; `?` means a filter whose marker couldn't be read. If the camera is unplugged or busy, routines say so and carry on without the check.

Outside the session, the same routines run on the follower alone (the leader can stay plugged in):

```powershell
& $env:USERPROFILE\lerobot-env\Scripts\python.exe arm\teach.py run move rig/top storage/top
& $env:USERPROFILE\lerobot-env\Scripts\python.exe arm\teach.py run dump
```

## 4. Adjusting

Everything is in `arm/layout.json`:
- `speeds`: `normal` and `slow` in degrees per second (start low; raise once it's reliable).
- `sides`: slot names per side. Add or rename slots, then teach their `front` and `in`.
- `dump`: the dish routine's steps. Add `["move", "NAME"]` waypoints, or change the shake (`["shake", "wrist_roll", 8, 4]` = 8 degrees, 4 times).
- `missed_grab_at`: how closed the gripper may get (0–1) before it counts as empty.
- `wrist_camera`: part of the camera's name (see `vision\cameras.py`), or `null` for none. Every marker check and every pulled filter saves a photo to `arm/captures/`.

Poses are saved in `arm/poses.json` as you go. They only work while the shelf, the arm's base and the arm calibration stay where they are; if anything moves, re-teach the affected poses.
