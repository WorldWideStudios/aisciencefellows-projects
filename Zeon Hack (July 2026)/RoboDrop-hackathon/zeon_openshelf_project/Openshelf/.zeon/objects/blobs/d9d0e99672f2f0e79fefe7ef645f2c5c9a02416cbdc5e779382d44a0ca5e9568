# Zeon verification loop

The seeded `pipette_demo` is this project's read-only golden reference. Its
workflow, canvas, saved world, six pipette skills, and shared `skills/utils.py`
are pinned by SHA-256 in `golden_pipette_demo.json`.

Do not regenerate that manifest or edit a pinned file unless the user explicitly
authorizes a new golden baseline.

## Automated gate

Run the full local gate from the project root:

```bash
python3 scripts/verify_zeon_project.py
```

Keep it running while authoring:

```bash
python3 scripts/verify_zeon_project.py --watch
```

For a quick pass over only the current Zeon diff:

```bash
python3 scripts/verify_zeon_project.py --changed-only
```

The focused right-arm horizontal plate pickup also has a task contract:

```bash
python3 scripts/verify_pickup_plate.py
```

It pins the skill and simulation workflow to `horizontal_grip`, requires the
named `RIGHT_FORWARD_FRONT` transition and canonical-grip snap, rejects
left-arm commands, old-orientation approach moves, and stale pickup anchors.
It confirms the plate, holder, and OpenShelf collision flags and validates the
horizontal pre-grasp geometry in `openshelf_sucess`.

The end-to-end pickup and OpenShelf placement has a separate contract:

```bash
python3 scripts/verify_move_plate_to_testphyw.py
```

It freezes the UI-confirmed `pickup_plate` by SHA-256, requires the workflow to
run pickup before placement, keeps the direct placement move on the carried
`horizontal_grip` orientation, and verifies that `testphyw` contributes only
the final position. It also checks attachment verification, release ordering,
collision flags, and the ordered pair of placement joint transitions.

The gate checks:

- every pinned golden file is byte-identical;
- no pinned path appears in the Zeon working-tree diff;
- Python syntax and skill entry-point names;
- changed skills use step-start logging, raise instead of returning
  `success=False`, return a success payload, load Cartesian geometry from
  anchors, and use named joint transition constants;
- workflow graphs, `$input` references, and node parameters against real Python
  skill signatures;
- YAML object models, URDF references, anchors, finite transforms, grasp width,
  and standoff;
- world object-model references, poses, quaternions, and collision flag types;
- `project.json` points to an existing workflow and world.

Ruby's standard YAML parser is used because the system Python does not include
PyYAML. No project dependency is installed.

## Required loop

1. Read `CLAUDE.md` and the relevant live Zeon docs.
2. Run `zeon sync` before editing, then run the automated gate.
3. Create new files for new behavior. Never modify the golden demo.
4. Keep the watcher running while editing.
5. Review `zeon status` and `zeon diff`.
6. Run the full gate again. Any error blocks sync.
7. Sync with a descriptive message and confirm local and remote heads match.
8. Refresh the already-open Zeon app, load the intended workflow and world, and
   reset the simulation and variables.
9. A person starts the cloud-simulation run. Inspect the first failing node,
   run log, arm branch, object pose, orientation, and collision behavior.
10. On failure, stop, preserve the first useful error, edit locally, and repeat
    from step 4. Hardware remains blocked until the simulation acceptance checks
    pass and the operator verifies the physical robot at the machine.

The local gate is deliberately not a motion simulator. The installed
`zeon verify` command currently reports that its server-side IK and collision
endpoint is not implemented, so cloud simulation is the required dynamic gate.
