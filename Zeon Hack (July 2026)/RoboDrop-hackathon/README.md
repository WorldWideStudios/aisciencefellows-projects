# Zeon Systems × OpenShelf Hackathon

This repository contains a hackathon project exploring how a
[Zeon Systems](https://zeonsystems.app/) lab-automation setup can integrate with
OpenShelf.

The goal was to connect Zeon's robot skills, workflows, world models, and
simulation tooling with an OpenShelf system for storing and retrieving labware.
The project includes experimental workflows for moving plates and other lab
objects, controlling the shelf, replaying calibrated robot waypoints, and
testing the full interaction in simulated OpenShelf environments.

## Repository layout

- `zeon_openshelf_project/Openshelf/` — the Zeon project synchronized with the
  Zeon cloud. It contains robot skills, workflow graphs, object definitions,
  calibrated worlds, verification scripts, and Zeon version metadata.
- `openshelf/` — supporting OpenShelf project files, robot skills, worlds, and
  integration experiments.
- `openshelf/zeon-systems/` — computer-vision experiments, training images,
  annotations, model weights, and inference tools used during the hackathon.
- `ADK/` — an experimental agent component used alongside the integration.

## What we explored

- Calling OpenShelf operations from Zeon workflows.
- Coordinating shelf movement with robot-arm actions.
- Storing and retrieving plates and other labware.
- Replaying calibrated waypoints for physical robot motion.
- Modeling the shelf, labware, fixtures, and robot workcell in Zeon worlds.
- Using computer vision to detect and estimate the pose of objects.
- Verifying workflows in simulation before attempting physical execution.

## Project status

This is experimental hackathon software, not a production-ready automation
system. Robot motions and calibration data are specific to the original
workcell. Review and revalidate all poses, anchors, devices, and safety
assumptions before running any workflow on physical hardware.

## Zeon project

The primary Zeon project is located at:

```text
zeon_openshelf_project/Openshelf
```

With the Zeon CLI installed and authenticated, its synchronization status can
be inspected from that directory:

```bash
zeon status
```

See the project-specific `AGENTS.md` and `CLAUDE.md` files for its structure,
authoring conventions, and safety notes.
