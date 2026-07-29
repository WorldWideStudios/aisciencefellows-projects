# Zeon project

A Zeon lab-automation **project** is a plain directory of text files — Python
skills, JSON workflow graphs, JSON world scenes, URDF + YAML objects, an
optional React canvas — versioned in the cloud and executed in a simulator or
on real robot arms.

This one is freshly scaffolded, so it still carries the seeded **pipette demo**
(see *What's here now* below). Build on it, replace it, or delete it.

> **If the `zeon-projects` skill is available to you, use it.** It bundles format
> references, the execution-function API, and a validator you can run locally.
> Entirely optional — everything here works without it, and the docs links in
> the next section cover the same ground. (Two commands to install; see the end
> of the next section.)

## Read the docs before you author

**File formats and the robot API are documented at
<https://readme.zeonsystems.app> — fetch the relevant page before writing a
skill, workflow, world, object, or canvas.** Machine index of every page:
<https://readme.zeonsystems.app/llms.txt>; append `.md` to any page URL for
clean markdown. Formats are deliberately not duplicated in this file — a copy
here would go stale.

| Writing this | Read this first |
|---|---|
| Anything at all | [Key concepts](https://readme.zeonsystems.app/docs/key-concepts.md) |
| `skills/<id>/robotic_code.py` | [Authoring a skill](https://readme.zeonsystems.app/docs/authoring-a-skill.md), [Skill runtime API](https://readme.zeonsystems.app/docs/skill-runtime-api.md), [Skill authoring patterns](https://readme.zeonsystems.app/docs/skill-authoring-patterns.md) |
| Arm motion / grasps | [Arm motion and the gripper](https://readme.zeonsystems.app/docs/arm-motion-and-the-gripper.md), [Anchors](https://readme.zeonsystems.app/docs/anchors.md), [Anchor snapping](https://readme.zeonsystems.app/docs/anchor-snapping.md) |
| Pipetting | [Pipetting](https://readme.zeonsystems.app/docs/pipetting.md) |
| `workflows/<id>.json` | [Authoring a workflow](https://readme.zeonsystems.app/docs/authoring-a-workflow.md), [The workflow file](https://readme.zeonsystems.app/docs/workflows-json.md) |
| `canvas/<id>_screen.tsx` | [Creating a canvas](https://readme.zeonsystems.app/docs/creating-a-canvas.md) |
| `worlds/` or `objects/` | [Worlds and objects](https://readme.zeonsystems.app/docs/worlds-and-objects.md), [The world state file](https://readme.zeonsystems.app/docs/worlds-world-state-json.md), [The object model file](https://readme.zeonsystems.app/docs/objects-object-model-yaml.md) |
| `zeon` CLI / syncing | [CLI reference](https://readme.zeonsystems.app/docs/cli-reference.md), [Syncing your work](https://readme.zeonsystems.app/docs/syncing-your-work.md) |

**Installing the `zeon-projects` skill** (the shortcut mentioned at the top) —
it bundles format references, the execution-function API, and the
`scripts/validate.py` / `scripts/inspect.py` tools:

```
/plugin marketplace add zeonsystems/zeon-project-skill
/plugin install zeon-project-skill@zeon
```

## Layout

| Path | Purpose |
|------|---------|
| `project.json` | Manifest — name, description, `active_workflow`, `active_world` |
| `skills/<id>/` | `robotic_code.py` (the behavior), `metadata.yaml`, `modules.py` |
| `skills/utils.py` | Constants and helpers shared across skills |
| `workflows/<id>.json` | Skill graph — one file per workflow |
| `worlds/<id>/` | `world_state.json` (the scene) + `live_state.yaml` (mutable per-object state) |
| `objects/<type>/` | `<type>.urdf` + `<type>.object_model.yaml`; meshes resolve from the shared mesh database |
| `canvas/<workflow_id>_screen.tsx` | Optional run-setup UI |
| `data/` | Per-run artifacts, keyed by execution id |

## Conventions that hold across every Zeon project

- **A skill's parameters are its Python function signature** — not
  `metadata.yaml`. Change the signature to change the parameters.
- **Workflows bind by reference.** Node parameters use `{"$input": <name>}`
  against declared workflow `inputs`; object inputs are world object **names**,
  never UUIDs.
- **Geometry comes from object-model anchors, not numbers in code.** Read grasp
  widths, standoffs, and well positions from `load_object_anchor(...)`; re-teach
  an anchor and the motion follows with no code change.
- **Calibration and counters live in `live_state.yaml`**, keyed by object UUID —
  per-instance offsets, tip counters, and similar mutable state. Skills read it
  with `get_world_state(id)` and write it with `set_world_state(id, {...})`.
  Missing entries usually degrade silently to a zero offset, so check that the
  instance you bind actually has a table.
- **Relocate arms through transition poses.** Long free-space Cartesian moves
  invite IK failures and elbow flips mid-run; a `move_arm_js` to a named joint
  configuration has no IK solve at all. `skills/utils.py` carries the standard
  grid (`LEFT_FORWARD_DOWN`, `RIGHT_OUTER_DOWN`, …). Start and end skills at one
  so they compose. **Never send an arm `INNER_*` while the other arm is also
  toward the center** — clear it first, explicitly.
- **Failure is raised, not returned.** Returning `{"success": False}` does *not*
  fail a workflow node; raise to stop the run.
- **Naming is strict**: lowercase `[a-z_][a-z0-9_-]*` for item folders,
  underscores in `skill_id` / `workflow_id`. Strict JSON — no comments, no
  trailing commas.
- **Never hand-author binaries.** Real geometry comes from the mesh database via
  `zeon new object` or the World Builder.

## Safety

Skill code moves physical arms in a lab.

- Copy motion parameters (speeds, approach offsets, waits) from existing skills
  in this project rather than inventing values, and read grip geometry from
  anchors.
- A clean sim run is not proof a grasp is safe — snapping asserts poses, it does
  not measure them.
- You author and validate files; runs are started by a person from the Zeon app.

## Working here

1. **Write new files rather than overwriting the examples.** New workflow → a
   new `workflows/<id>.json`; new canvas → a new `canvas/<id>_screen.tsx`. Only
   repoint `project.json`'s `active_workflow` / `active_world` when asked to make
   something live.
2. **Look before you write.** The existing skills and workflows are the working
   reference for this bench; `scripts/inspect.py` from the skill prints every
   skill signature, workflow graph, world instance, and object anchor in one go.
3. **Validate before declaring done** — `scripts/validate.py` checks node
   parameters against real skill signatures, call sites against the real robot
   API, and anchors against the object models. Without it, at minimum re-read
   your JSON and confirm every `skill_id` exists under `skills/`.

## What's here now

The seeded example: a `pipette_demo` workflow that moves one volume between two
wells — grab pipette → attach tip → aspirate → dispense → eject tip → place
pipette — over a deck of well plates, tip racks, and two electronic pipettes,
with a canvas for run setup. The skills are left-arm only and stage at a shared
pose so they compose in any order.

**Rewrite this section as the project becomes yours.** Describe your deck, your
protocol, and anything about this bench a new session could not infer from the
files. Keep everything above it — that is what makes the next session start
informed.
