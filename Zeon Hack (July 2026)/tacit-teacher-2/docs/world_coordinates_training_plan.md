# World-Coordinates Training Plan

A way to build a trajectory directly from live poses and gripper commands,
without going through the anchor system. Anchors remain the default and
recommended way to author reusable motion in this project (see `CLAUDE.md`:
*"Geometry comes from object-model anchors, not numbers in code"*) — this plan
is for prototyping a trajectory quickly, or for one-off motion that doesn't
need to survive an object or world changing underneath it.

## Why you'd do this instead of teaching anchors

- Faster to iterate on a multi-point trajectory (e.g. a diagonal peel motion)
  than round-tripping through the Object Database's anchor editor for every
  waypoint.
- Useful for validating a motion in sim before deciding which points, if any,
  are worth promoting to real anchors.

## Tradeoff, stated plainly

A hardcoded pose is only valid for the exact object placement it was measured
against. Move the object, load a different world, or hand the skill a second
instance of the same object type, and the pose is simply wrong — there is no
re-resolution against wherever the object actually is, the way
`load_object_anchor()` gives you. Treat anything built this way as
world-specific and temporary unless deliberately promoted to an anchor (see
Step 5).

## Steps

### 1. Jog to each waypoint and capture its pose

- Jog the arm to the pose you want, using either:
  - the Transform Controls panel's live X/Y/Z/Roll/Pitch/Yaw readout (World
    Builder / Workflow Editor sidebar), or
  - `get_arm_pose(arm)` called from a throwaway skill — returns
    `[x, y, z, roll, pitch, yaw]` in the world frame, in metres/radians,
    without moving the arm.
- Record the six numbers for that waypoint.

### 2. Note the gripper state at each waypoint

- At each point, decide what the gripper should be doing (open / closed /
  specific width) and write that width down alongside the pose.
- There is no function to *read* current gripper width — `set_gripper` is
  write-only. This has to be tracked by hand, the same way `wellplate_grab`
  stashes its own width into `shared_state` rather than reading it back.

### 3. Encode the captured sequence directly in a skill

Plain ordered calls in `robotic_code.py`, using the literal captured numbers,
no `load_object_anchor()` calls at all:

```python
move_arm(arm="left_arm", position=[x1, y1, z1], orientation=[r1, p1, y1], speed=...)
set_gripper(arm="left_arm", width_m=w1)
move_arm(arm="left_arm", position=[x2, y2, z2], orientation=[r2, p2, y2], speed=...)
set_gripper(arm="left_arm", width_m=w2)
# ... repeat per waypoint
```

### 4. Test and iterate in sim

Run via Skills Editor / Practice Skill against the same world the poses were
captured in. Adjust speeds and waypoints; recapture any point that doesn't
move cleanly (IK failure, collision, wrong orientation).

### 5. Decide what to do with it once it works

- Leave it hardcoded if this is genuinely a one-off, single-world trajectory.
- Or promote the key waypoints to real anchors afterward, so the skill
  becomes reusable if the object moves or a different world uses it. To
  convert a captured world-frame pose into an anchor's object-relative
  `link_T_anchor`:

  ```
  anchor_local_pos  = R(object_world_quat)⁻¹ · (arm_world_pos − object_world_pos)
  anchor_local_quat = object_world_quat⁻¹ · arm_world_quat
  ```

  i.e. `anchor_local = inverse(object_world_pose) ∘ arm_world_pose` — the
  inverse of the compose used to place an object onto a target anchor (see
  `wellplate_place`'s bottom-center-anchor snap logic for the forward
  direction of the same math).

## Open question

The app has a **"Waypoint Recording"** panel (World Builder / Workflow Editor
sidebar) that, by name, may automate steps 1–2 directly — capture a live pose
and store it as a named waypoint without manually copying numbers out of the
Transform Controls readout. Not yet confirmed what it actually does or
whether it writes anchors, a separate waypoint list, or something else —
worth checking before doing this by hand.
