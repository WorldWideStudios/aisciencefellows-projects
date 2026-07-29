# Plate pick/place snapping convention

Wellplate pick-and-place skills **snap** the plate to known poses so the
simulation stays deterministic. In sim the plate's true resting pose is uncertain
(it settles/falls a little on release, and the amount varies), so instead of
trusting where the plate *is*, we assert where it should be — in the gripper on a
pick, on the destination on a place.

The one invariant is **how the plate sits in the gripper**. The plate's
`grasp_shortside` anchor is the point that is always at the gripper when held. Snap
that onto the gripper on every pick and the whole cycle is repeatable — every carry
is identical, so every release is identical.

## Two rules

| When | Rule | Call |
|------|------|------|
| **Pick** (grab) | Snap `grasp_shortside` onto the gripper, then attach | `snap_plate_into_gripper(plate_id)` |
| **Place** (release) | Snap the plate's seat anchor onto the destination anchor | `snap_object_anchor_to_world_pose(plate_id, <plate_anchor>, dest["xyz"], dest["wxyz"])` |

- The **grip snap** is what makes it consistent. Call it right after the gripper
  closes on the plate. Consistency comes entirely from this.
- The **seat snap** is for making sim look seated and giving the *next* pick a
  known target. It's not required for consistency.

## The helper — `utils.py`

`snap_plate_into_gripper(object_id, arm="right_arm", grasp_anchor="grasp_shortside")`
reads the live TCP, snaps the grasp anchor exactly onto it, and attaches. One
canonical grip, one call.

## Which plate anchor for the seat snap?

The seat anchor must match what the destination anchor *means*:

- **Side-grab seats** (shaker slot, sealer) → `grasp_shortside`. The destination
  anchor is itself a grasp pose.
- **Flat rests** (stand top) → `bottom_center` → `top_center`. The destination is
  where the plate's base sits.

## The `_unload` anchor pattern

On release the plate settles a few mm below where it was held. Fixtures encode this
as a `*_unload` anchor ~3–4 mm below the load/grasp anchor, along the grasp
approach axis (the anchor's local `+Z`):

- shaker: `slot_N` (place height) → `slot_N_unload` (settled/grab pose)
- sealer: `plate_load` (place height) → `plate_unload` (settled/grab pose)

**Place** releases at the load anchor and seat-snaps the plate to the `_unload`
anchor. **Unload** descends to the `_unload` anchor and grip-snaps — so both agree
on the settled pose and there is no pick/drop drift. (The extra few mm is also a
real-hardware benefit: the fingers close *under* the settled plate.)

## Where it's used

| Skill | Role | Snap |
|-------|------|------|
| `wellplate_grab` | pick | grip: `grasp_shortside` → gripper |
| `wellplate_shaker_unload` | pick | grip: `grasp_shortside` → gripper (at `slot_N_unload`) |
| `platesealer_platemax_unload` | pick | grip: `grasp_shortside` → gripper (at `plate_unload`) |
| `wellplate_shaker_load` | place | seat: `grasp_shortside` → `slot_N_unload` |
| `platesealer_platemax_load` | place | seat: `grasp_shortside` → `plate_unload` |
| `wellplate_drop` | place | seat: `bottom_center` → `top_center` |

## Caveats

- Assumes every pick goes through the grip snap. If a plate is attached some other
  way, a following place trusts a grip that was never asserted.
- Snapping means sim always shows a perfect grip, so it hides a real-world grab
  that slipped. Good for a deterministic demo; not for catching bad grasps.
