# Skills — authoring guide

Anchor-driven lab-automation skills for `hackathon_v2`. Each skill is one robot
step (grab a plate, pick a seal, open a lid). The rule that makes them reusable:
**geometry comes from object-model anchors, not from numbers baked into the code.**
Re-teach an anchor and the motion follows — no code change.

## Layout

Each skill is a directory under `skills/<skill_id>/`:

| File | Purpose |
|------|---------|
| `robotic_code.py` | The behavior. The `<skill_id>(...)` function signature **is** the parameter schema. |
| `metadata.yaml` | `skill_id`, `version`, `description`, `tags` (+ optional pre/postconditions). |
| `modules.py` | Always just `from execution.execution_functions import *`. |

Import execution helpers via `from .modules import (...)`; import shared arm poses
via `from utils import (...)`.

## The anchor-driven pattern

- Object inputs are `SkillObject`; use `object.id` to address the world instance.
- `load_object_anchor(id, "anchor", joint_config=None)` → dict with
  `xyz`, `rpy`, `wxyz`, `standoff`, `width`, `gripper_variant`, `object_id`.
- `anchor_preapproach(anchor, default_standoff=…)` → a world-frame standoff point,
  backed off along the anchor's approach axis (the anchor's local −Z). The anchor's
  own `standoff` wins when set; otherwise the default is used.
- **Gripper widths and standoffs come from the anchor's `grasp` block** — read
  `anchor["width"]` / `anchor["standoff"]`, don't hardcode them.

```python
grasp = load_object_anchor(obj.id, "grasp_shortside")
pre   = anchor_preapproach(grasp, default_standoff=0.15)
move_arm(arm="right_arm", position=pre,          orientation=grasp["rpy"], speed=40)
move_arm(arm="right_arm", position=grasp["xyz"], orientation=grasp["rpy"], speed=10)
set_gripper(arm="right_arm", width_m=grasp["width"])
```

## Articulated objects (lids, drawers)

For anything with a moving part (`lid_joint`, `drawer_joint`, …):

1. Resolve the grab anchor **at a chosen joint angle**:
   `load_object_anchor(id, "lid_open", joint_config={"lid_joint": 0.0})`.
2. Sweep the arm between the two extremes with
   `interpolate_anchor_to_anchor(arm, id, "lid_open", "lid_open",
   start_joint_config={"lid_joint": a}, end_joint_config={"lid_joint": b},
   interpolate=True, steps=6, speed=…)` (the same anchor at two angles traces the arc).
3. **Commit the joint in sim** with `update_object_joint_config(id, {"lid_joint": b})`
   — the skill owns the world-model sync; the sweep does not do it for you.

Set the *precondition* state at the start too (e.g. model the drawer open before a
load), the same way `platesealer_platemax_load` does. Read the joint presets
(closed/open angles) from the object model, not from memory.

## Gotcha: `move_relative` is world-frame

`move_relative(arm, delta_xyz=…)` adds the delta to the **world-frame** TCP
position — `[d, 0, 0]` is always world +X, regardless of object orientation. For an
**object-aligned** slide (e.g. peeling a seal out along its approach axis), derive a
unit direction from the anchors and scale it:

```python
out  = [grasp_pre[i] - grasp["xyz"][i] for i in range(3)]        # grasp -> its preapproach
n    = (out[0]**2 + out[1]**2 + out[2]**2) ** 0.5
udir = [c / n for c in out] if n > 1e-9 else [0.0, 0.0, 0.0]
move_relative(arm, delta_xyz=[dist * c for c in udir], speed=…)  # slide out, object-aligned
move_relative(arm, delta_xyz=[0, 0, lift_m], speed=…)            # lift stays world +Z
```

## What stays hardcoded (and why)

Calibrated **joint poses** — swing / stow / intermediary clearance stances — are not
derivable from anchors. Keep them as named skill-local constants (or import from
`utils.py`, e.g. `RIGHT_ARM_STOW_JOINTS`) and comment that they're cell-calibrated.

## Holding a plate consistently

After closing on a plate, assert the **canonical grip** so it's held identically on
every pick: `snap_plate_into_gripper(plate.id)` (snaps the plate's grasp anchor onto
the gripper and attaches). For a plain attach use `attach_object_to_arm(id, arm=…)`;
release with `detach_object_from_arm(id)`.

## Boilerplate

- Start with `print_log(runlog=True, runlog_type="step_start")` then a `print_log`
  naming the skill + key inputs; end with a completion `print_log`.
- Return `{"success": True}`.
- Prefer parameters with sensible defaults over inline magic numbers; expose the
  anchor names, speeds, and tunable distances so the skill is reusable.

## Authoring checklist

- [ ] New dir `skills/<skill_id>/` with `robotic_code.py`, `metadata.yaml`, `modules.py`.
- [ ] Geometry (poses, widths, standoffs) resolved from anchors — nothing world-baked.
- [ ] Articulated parts: resolve at a `joint_config`, sweep, then `update_object_joint_config`.
- [ ] Object-aligned relative slides derive their direction from anchors (not world axes).
- [ ] Calibrated swing/stow poses kept as commented skill-local constants.
- [ ] `metadata.yaml` `skill_id` matches the function name; tags name the object + arm.
- [ ] `python3 -m py_compile skills/<skill_id>/robotic_code.py` passes; then verify in sim.
