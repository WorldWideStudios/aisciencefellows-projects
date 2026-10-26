# Agent prompts

Task briefs written in LamaSu's planning session for coding agents (Claude Code) working in this repo. Each file is self-contained: context, verified facts, tasks in priority order, acceptance checks and a report format.

| File | For | Task |
|---|---|---|
| [sample-registry.md](sample-registry.md) | LamaSu's agent | Build the SQLite sample registry and well ledger: schema, adapter, labels, scan page, API, bridge to the planner, CLI |
| [8channel-generator.md](8channel-generator.md) | ebrinz's agent | Make the Flex protocol generator and the planner work with the 8-channel 1000 µL pipette (column batches, stock plate), plus robot-client gates and a per-command feed |

## How to use

In your Claude Code session, on your own branch, paste:

> Read `docs/agent-prompts/<file>.md` completely, then `docs/opentrons-integration.md` and `CLAUDE.md`. Do the tasks in the order given, commit small, run the verification commands, and finish with the report described in the file.

## If the files are not in your clone yet

They live on the planning branch until it is merged to `main`:

```bash
git fetch origin lamasu/goals-and-plan
git checkout origin/lamasu/goals-and-plan -- docs/agent-prompts docs/opentrons-integration.md GOALS.md
```

This copies the files into your working tree and leaves your branch history alone.
