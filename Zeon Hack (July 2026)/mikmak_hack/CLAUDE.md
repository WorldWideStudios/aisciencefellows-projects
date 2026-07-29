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

Built on top of that: a **TEM-1 beta-lactamase CFPS screening bench**, run as a
closed Plan → Simulate → Approve → Execute → Analyze loop (`pipeline/`, Google
ADK + beads + marimo), across three round types:

- **`kinetics`** (`workflows/tem1_kinetics_characterization.json`) — standalone
  purified-TEM1 x nitrocefin-substrate grid, read kinetically. Prerequisite: its
  fit sets the nitrocefin working concentration and endpoint timing used below.
- **`cfps_expression`** — Part 1 (`workflows/cfps_mastermix.json`, pre-existing,
  own canvas) expresses TEM1 via CFPS; Part 2
  (`workflows/cfps_sfgfp_confirmation.json`) reads sfGFP on the same plate as a
  go/no-go gate before spending a screen on it.
- **`inhibitor_dose_response`** (`workflows/cfps_inhibitor_dose_response.json`,
  `canvas/cfps_inhibitor_dose_response_screen.tsx`) — doses a confirmed-expressed
  well with compound + nitrocefin per position and reads kinetically; the initial
  slope of A490 vs time is TEM-1's velocity, and inhibition drops it.

**The loop is driven conversationally.** `pipeline/agents/tem1_pipeline/` is an
ADK coordinator (`root_agent`) over five sub-agents — `planner`, `syncer`,
`simulator`, `executor`, `analyst` — one per stage. Chat with it:

```bash
cp pipeline/agents/tem1_pipeline/.env.example pipeline/agents/tem1_pipeline/.env  # add GOOGLE_API_KEY
adk web pipeline/agents        # or: adk run pipeline/agents/tem1_pipeline
```

The agents hold no scientific logic of their own — every tool wraps a plain
function in `plan_agent.py` / `simulate.py` / `watch_execution.py` /
`analyze_agent.py` / `zeon_sync.py`, and every stage transition still goes
through `beads_writer`, so `bd show <round>` remains the record of what happened.
Three constraints are wired into the agents' instructions on purpose:

- **The chat cannot start a run.** The `zeon` CLI has no run command. `executor`
  approves the round, hands over the workflow + exact `run_name` + deck, then
  polls `data/logs/` until the human-triggered run lands.
- **Pushing is asked for every time.** `syncer` bakes a round's preset into the
  target workflow's `inputs[].defaultValue` (that — not `inputs/<round>.json` —
  is what pre-fills the app's run-setup canvas), then requires an explicit
  go-ahead before `zeon commit`/`push`.
- **`zeon_sync.SYNC_PATHS` scopes every commit** to `project.json`, `workflows/`,
  `skills/`, `worlds/`, `objects/`, `canvas/`, `inputs/`, `data/`. A bare
  `zeon commit` snapshots the whole tree, which here would push the beads DB and
  `graphify-out/` into the cloud lab project. **`zeon sync` and `zeon pull` both
  finish with an unscoped whole-tree commit** — so don't reach for them directly;
  `zeon_sync.reconcile_with_cloud()` does the same merge, then resets HEAD back to
  the cloud tip and rebuilds the commit from `SYNC_PATHS` only. A push that fails
  with "the cloud has changed since your last sync" (a run finishing in the app
  writes its logs back to the cloud ref) retries through it automatically.

`pipeline/beads_writer.py` is the **single writer** to the beads (`bd`) DAG — every
stage transition of every round goes through it, nothing else calls `bd` directly.
`pipeline/agents/plan_agent.py` and `analyze_agent.py` are Google ADK agents (their
actual decision logic is plain, LLM-free functions the ADK tools wrap);
`pipeline/simulate.py` runs `scripts/validate.py` (+ `zeon verify` once that
command exists — it isn't implemented on this CLI build yet); `pipeline/apps/`
holds the marimo Approve gate and results dashboard; `pipeline/watch_execution.py`
notices a human-triggered Zeon run landing (there's no programmatic run trigger)
and links it to its round.

`pipeline/library/compounds.csv` is a **3-row placeholder** — swap in the real
compound library (same columns: `compound_id,source_well,stock_conc_um`) without
touching any other file. `pipeline/agents/analyze_agent.py`'s `parse_gen5_export`
is a **stub** returning synthetic but realistically-shaped data — swap its body
for real Gen5 PDF parsing once a sample export (endpoint and kinetic) is in hand.
Grid sizes, default concentration ranges, and stock concentrations throughout
`plan_agent.py` are placeholders flagged in-line; nothing scientific here is
tuned yet, only wired correctly end to end (traced with fabricated data through
every stage, beads events landing in the right order, for all three round types).

**Rewrite this section as the project becomes yours.** Describe your deck, your
protocol, and anything about this bench a new session could not infer from the
files. Keep everything above it — that is what makes the next session start
informed.


<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:6cd5cc61 -->
## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

**Architecture in one line:** issues live in a local Dolt DB; sync uses `refs/dolt/data` on your git remote; `.beads/issues.jsonl` is a passive export. See https://github.com/gastownhall/beads/blob/main/docs/SYNC_CONCEPTS.md for details and anti-patterns.

## Agent Context Profiles

The managed Beads block is task-tracking guidance, not permission to override repository, user, or orchestrator instructions.

- **Conservative (default)**: Use `bd` for task tracking. Do not run git commits, git pushes, or Dolt remote sync unless explicitly asked. At handoff, report changed files, validation, and suggested next commands.
- **Minimal**: Keep tool instruction files as pointers to `bd prime`; use the same conservative git policy unless active instructions say otherwise.
- **Team-maintainer**: Only when the repository explicitly opts in, agents may close beads, run quality gates, commit, and push as part of session close. A current "do not commit" or "do not push" instruction still wins.

## Session Completion

This protocol applies when ending a Beads implementation workflow. It is subordinate to explicit user, repository, and orchestrator instructions.

1. **File issues for remaining work** - Create beads for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **Handle git/sync by active profile**:
   ```bash
   # Conservative/minimal/default: report status and proposed commands; wait for approval.
   git status

   # Team-maintainer opt-in only, unless current instructions forbid it:
   git pull --rebase
   git push
   git status
   ```
5. **Hand off** - Summarize changes, validation, issue status, and any blocked sync/commit/push step

**Critical rules:**
- Explicit user or orchestrator instructions override this Beads block.
- Do not commit or push without clear authority from the active profile or the current user request.
- If a required sync or push is blocked, stop and report the exact command and error.
<!-- END BEADS INTEGRATION -->
