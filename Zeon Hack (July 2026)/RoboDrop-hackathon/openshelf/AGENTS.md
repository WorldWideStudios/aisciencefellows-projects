# Pipette Demo project

A Zeon lab-automation **project** is a self-contained directory of skills,
worlds, workflows, objects, and an optional canvas UI. This one is a minimal,
runnable example — pick up the electronic pipette, grab a fresh tip, and aspirate
from one well of a PCR plate. Read it to learn how a project is laid out, then
build your own workflow alongside it (copy the patterns; never overwrite the
examples — see below).

`project.json` defaults: `active_workflow` → `pipette_demo`, `active_world` →
`pipette_demo_world`.

## Do not edit the example files

These are **reference templates**. Copy their patterns; never overwrite them:

| File | Purpose |
|------|---------|
| `workflows/pipette_demo.json` | Structural reference (nodes, edges, inputs, `canvas_ui`) |
| `canvas/pipette_demo_screen.tsx` | Canvas reference (React sandbox, `zeon.*` globals) |

**When the user asks you to build a workflow:**

1. **Create a new file** — `workflows/<your_workflow_id>.json`.
2. **Optional canvas** — `canvas/<your_workflow_id>_screen.tsx` (new file; do not touch `pipette_demo_screen.tsx`).
3. **Do not write into `pipette_demo.json`** even if `project.json` `active_workflow` is still `pipette_demo`.
4. **Switch the live workflow** — update `project.json` `active_workflow` to your new `workflow_id` **only when the user explicitly asks** to make it the default / run it in the UI.

Wrong: editing `pipette_demo.json` because it matches `active_workflow`.
Right: new workflow file + tell the user to set `active_workflow` when they want it live.

## Layout

| Path | Purpose |
|------|---------|
| `skills/<skill_id>/` | `robotic_code.py` (behavior), `metadata.yaml` (description, tags) |
| `objects/<type>/` | URDF + `.object_model.yaml` (geometry/anchors) |
| `worlds/<world_id>/` | `world_state.json` — scene + instance poses/names; `live_state.yaml` — mutable per-object state (e.g. tip-box counters) |
| `workflows/<workflow_id>.json` | Skill graph (one file per workflow) |
| `canvas/<workflow_id>_screen.tsx` | Optional custom run-setup UI |
| `data/` | Run artifacts |

World for this deck: `worlds/pipette_demo_world/`.

## Choosing skills

1. List `skills/` and read `metadata.yaml` for intent.
2. Open `robotic_code.py` — the function signature is the **parameter schema**.
3. **Atomic** skills do one step (`epipette_grey_pick`, `epipette_grey_aspirate`, …).
4. **Meta** skills bundle several atomic skills into one step — their `robotic_code.py` imports and calls other skills' functions in sequence, and they carry a `meta` tag in `metadata.yaml`. This demo ships only atomic skills, but you can author a meta skill the same way: a new `skills/<id>/` whose `robotic_code.py` imports the atomics it needs (e.g. `epipette_grey_pick` → `epipette_grey_attach` → `epipette_grey_aspirate`) and calls them in order, exposed as one callable skill.
5. Shared arm poses and constants live in `skills/utils.py`.

Wire existing skills unless the user asks for new ones. The shipped skills are a
self-contained pipette closure: `epipette_grey_pick`, `epipette_grey_attach`,
`epipette_grey_aspirate`, `epipette_grey_eject`, `epipette_tip_check`, and
`laser_read` (the tip-presence sensor, which reports a tip in simulation).

## Authoring a new workflow

Read `workflows/pipette_demo.json` for structure. Write your workflow to a **new path**.

**Nodes** — `type`: `start` | `end` | `skill` | `conditional` | `loop`. Skill nodes need `skill_id` + `parameters`.

**Edges** — `condition.type`: `default` (from start), `on_success`, `if_true`, `if_false`.

**Inputs** — Declare run-time roles. Bind in node `parameters` with `$input`:

```json
"inputs": [
  { "name": "plate",  "type": "object", "is_array": false, "description": "PCR plate" },
  { "name": "volume", "type": "float",  "description": "Volume in µL", "defaultValue": 5 }
],
"parameters": {
  "object": { "$input": "plate" },
  "volume": { "$input": "volume" }
}
```

Object inputs use world object **names** (not UUIDs). Common names in
`pipette_demo_world`: `epipette_grey`, `wellplate_pcr_parts_1`..`wellplate_pcr_parts_4`,
`tipbox_10ul_1`..`tipbox_10ul_3`, `fixture_plate`, `pipette_stand`.

**Required top-level fields** (see the example workflow for the full shape):

```json
{
  "workflow_id": "<your_workflow_id>",
  "name": "...",
  "description": "...",
  "version": "1.0.0",
  "author": "...",
  "created_at": "...",
  "updated_at": "...",
  "simulation_validated": false,
  "objects": [],
  "inputs": [],
  "nodes": [],
  "edges": []
}
```

`"objects": []` is required even when empty.

**JSON** — Strict JSON only (no trailing commas, no comments).

## World and object binding

Instances in `worlds/pipette_demo_world/world_state.json` carry a `metadata.type`
(e.g. `wellplate_pcr`) and a `metadata.name` (e.g. `wellplate_pcr_parts_1`). Object
models resolve **by type** — the matching `objects/<type>/` directory wins, then the
global mesh database. Workflow `inputs` expose **roles**; the run UI maps each role
→ a world instance by name. Never hardcode UUIDs in workflow JSON.

> Note: `epipette_grey_attach` keys its tip-box registry to the specific tip-box
> UUIDs in `pipette_demo_world`. If you re-export or rebuild the world, keep those
> tip-box instances (and one marked `active` with a `tip_index` in `live_state.yaml`).

## Canvas (optional run UI)

Copy patterns from `canvas/pipette_demo_screen.tsx` into a **new**
`canvas/<your_workflow_id>_screen.tsx`.

**Wire it in your workflow JSON:**

```json
"canvas_ui": {
  "kind": "react",
  "source_ref": "canvas/<your_workflow_id>_screen.tsx",
  "enabled": true,
  "version": 1,
  "updated_at": "..."
}
```

**Rules:**

- `export default` a React component; only `import ... from "react"`.
- Host globals: `zeon.schema`, `zeon.worldObjects`, `zeon.defaults`, `zeon.submit(values)`, `zeon.onValidationErrors(cb)`.
- Submit values keyed by workflow `input` names; object values are world **names**.

Omit `canvas_ui` or set `"enabled": false` to use the default auto-generated form.

## Common skill pattern

- **Pipette:** `epipette_grey_pick` → `epipette_grey_attach` → aspirate/dispense → `epipette_grey_eject` → place back.

## Done checklist (for a *new* workflow)

- [ ] New file at `workflows/<workflow_id>.json` — did **not** modify `pipette_demo.json`
- [ ] Every `skill_id` in the graph exists under `skills/`
- [ ] Parameters wired via `$input` or literals
- [ ] `pipette_demo_world` loadable; object inputs mappable in the UI
- [ ] If canvas: new `canvas/<workflow_id>_screen.tsx`; `source_ref` matches
- [ ] `project.json` `active_workflow` updated only if the user asked to switch the live workflow

## Out of scope unless asked

- Editing skill Python, URDFs, or world state files
- Editing `pipette_demo.json` or `pipette_demo_screen.tsx`
- Monorepo services (`services/execution`, gateway, etc.)
