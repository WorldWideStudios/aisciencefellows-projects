# peel_seal — what happened when the robot tried it

Filled in after the first run. This closes the loop and is the most valuable file
in the session for anyone reading later.

## Status: not yet attempted

No robot run. Two things block it, both outside this file:

- **The `peel_corner` anchor does not exist** on any wellplate object model.
  Confirmed by search: only `grasp_short` and well anchors are defined. It has to
  be taught before any motion can be authored. (Check the anchors on the new
  `wellplate_grab` / `wellplate_place` skills first — they may already cover it.)
- **The interview has not happened**, so every force parameter is in `unknowns`.
  A skill can be drafted from geometry and timing alone, but it would be guessing
  at the one variable that separates V1 from V5 and V7.

## What a simulator run will and will not prove

Worth stating before anyone reads a green sim result as success.

**A rubber sealing mat peeling is not modelled.** It is a deformable body under
tension, and the simulator does not simulate that. Anchor snapping asserts poses;
it does not measure them.

So a clean sim run proves:

- the motion is reachable and IK-solves
- the arm does not collide with the deck or itself
- the skill composes with its neighbours at the transition poses

and proves nothing about:

- whether the mat comes off
- whether anything is contaminated
- whether the hold-down force is sufficient

All three verification checks in `20-extracted.yaml` — `mat_detached`,
`no_contamination` and `plate_not_disturbed` — are unverifiable in simulation.
They need the real bench and a camera.

**The camera exists.** `capture_image(arm, capture_name, save_to_project)` runs
off the right arm's wrist camera and returns a path, handling its own errors and
returning `None` on failure — see `skills/left_arm_pose_sequence_1`, which takes
a still after every waypoint. Nothing in the peel skills uses it yet.

That is worth acting on, because all three of Q4's conditions are things a person
can settle from one photograph: is the mat off, is there liquid where it should
not be, has the plate shifted. The knowledge to check has been extracted and the
instrument to check with is available — they have simply not been connected.
A still after the final retract would close the loop this file exists to close.

## Run 1

- **Result:** _pending_
- **Where it diverged:** _pending_
- **Which was wrong — the transcript or the extraction?** _pending_

  This is the distinction the whole directory structure exists to preserve, and
  this session has a third possibility the template does not anticipate: the
  parameter may have come from **video** rather than from the expert. When a
  number fails, check its `source` kind first. A wrong `V` source means the
  camera misled us; a wrong `Q` source means the expert did. They fail
  differently and they are fixed differently.

  The prime suspect is already named: `geometry.peel_angle_deg` is a disputed
  `vlm_estimate` spanning 45–90°.

- **What we changed:** _pending_
- **New question for next time:** _pending_
