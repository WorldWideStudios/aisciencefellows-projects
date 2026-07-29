# tacit-teacher

**Zeon 24hr AI-for-Science hack · Track C — dexterity and physical verification**

Getting the part of a technique that never makes it into the protocol out of a
person's hands and into a robot's.

---

## The thesis, and where we found it

A protocol says *"pick up the pipette."* The seeded `epipette_grab` skill in this
repo says something much more specific:

```python
set_gripper(arm="left_arm", width_m=0.05)     # open
move_arm(..., speed=50)                       # approach fast
move_arm(..., speed=30)                       # but slow down onto the grasp
time.sleep(0.5)                               # let it settle before closing
set_gripper(arm="left_arm", width_m=0.035)    # close to contact
...
set_gripper(arm="left_arm", width_m=0.012)    # then clamp
move_relative(delta_xyz=[0.0, 0.0, 0.05])     # retract 5 cm, straight up
```

Nobody derived those numbers. Someone *learned* them, by watching it fail. The
same file carries this comment:

> Stash the grasp point resolved here (while the pipette is still at its home
> location) so `epipette_place` descends to the real grab pose instead of
> re-resolving the anchor against the pipette once it is attached to the arm and
> elevated (which would yield an elevated, wrong point).

That is tacit knowledge — the kind that exists only in the hands and head of
someone who has done the task a thousand times, and that a robot needs and never
gets. Today it reaches the robot by accident, as magic numbers and comments
written by whoever debugged it last.

**tacit-teacher makes that transfer deliberate.** An agent interviews the person
who knows the technique, asks only the questions that change what the robot does,
and writes the answers out as a Zeon skill — keeping a transcript of what the
expert actually said, separately from what was inferred from it.

```
expert  ──interview──▶  agent  ──authors──▶  skills/<name>/robotic_code.py
                          │                            │
                    transcript.md                  zeon sync
                  (what they said)                      │
                                              simulate → real arms
```

The transcript and the skill are kept apart on purpose. When the robot gets it
wrong, you need to know which of the two was at fault: did the expert not say it,
or did we not hear it?

Each interview becomes a session directory of four numbered files — brief,
transcript, extracted parameters, outcome. **Every parameter cites the question
that justifies it.** `python tacit/validate.py` fails the session if one does
not, because an uncited number is a guess wearing the costume of knowledge, and
`width_m=0.035` looks identical either way once it is sitting in a Python file.
The format is in [`tacit/schema.md`](tacit/schema.md).

---

## Start here (first ten minutes)

```bash
zeon auth login --global      # opens a browser, once per machine
zeon clone tacit-teacher      # THIS gets you a runnable tree — git clone does not
cd tacit-teacher && pip install -r requirements.txt
python -m agent               # should print a transcript path, no key needed
```

### Just want to look at it?

A plain `git clone` is enough to run everything that does not need a robot:

```bash
git clone https://github.com/ebrinz/tacit-teacher && cd tacit-teacher
pip install -r requirements.txt
python -m agent            # the interview agent, model-free
python tacit/validate.py   # the provenance check on extracted knowledge
```

Both exit 0 with no API key, no network, and no Zeon account.

**What a git clone cannot do is drive the robot.** This repo holds only our work;
the Zeon scaffold underneath it — the seeded pipette skills, object models,
canvas, `CLAUDE.md`, `project.json` — is the vendor's material and is
deliberately not republished here. `zeon clone` delivers it, and the team Drive
has a copy. `skills/`, `workflows/` and `worlds/` look empty for that reason:
they hold only what *we* author.

Then read, in this order:

1. [`docs/runbook.md`](docs/runbook.md) — which lane is yours, and how not to
   collide with the other three.
2. [`tacit/QUESTIONS.md`](tacit/QUESTIONS.md) — the interview taxonomy. Read it
   even if knowledge capture is not your lane; it is what the project is *for*.
3. `skills/epipette_grab/robotic_code.py` — the seeded skill. It is both our
   reference for how a skill is written and the exhibit for why this project
   exists.

---

## What's in this repo

**Not in this repo, but on disk once you `zeon clone`** — a complete, working
pipette demo, seeded by the platform. Don't treat it as boilerplate: it is the
reference for how a skill is written and the source of the primitives we compose.

```
skills/epipette_*  grab · place · attach · eject · aspirate · dispense
                   + utils.py (shared poses: LEFT_FORWARD_DOWN, ...)
workflows/         pipette_demo.json          ← the active workflow
worlds/            pipette_demo_world         ← the active world
objects/           12 models (epipettes, tipboxes, well plates, shaker,
                   fixture plates) as URDF + object_model.yaml
canvas/            pipette_demo_screen.tsx    ← React input form
CLAUDE.md          Zeon's authoring guide + docs index. Read it.
project.json       manifest: active_workflow, active_world
```

These are the vendor's files, so we keep them out of a public repo — but
`skills/` and `workflows/` are still tracked, so **anything we author lands
here.**

**Ours, and all of what this repo contains** — the agent layer is ported from
[green-knight](https://github.com/ebrinz/green-knight), this team's Track A
entry, where the shape was verified end to end against a live model.

```
agent/             core.py — ADK tools + model-free orchestrator + gated live agent
                   handoff.py — write a request, wait for a result
tacit/             QUESTIONS.md — the interview taxonomy (the reusable asset)
                   schema.md — what one interview turns into
                   validate.py — every parameter must cite the transcript
                   sessions/<task>/ — brief · transcript · extracted · outcome
media/             stills + a manifest. NO BINARIES — see media/README.md
docs/              runbook.md (four-lane ownership) · design/ · pitch/
out/               agent scratch output — drafts land here, never in skills/
```

## Working as four

Read [`docs/runbook.md`](docs/runbook.md) first. The short version: Zeon has a
**single cloud HEAD**, so two people editing one file get conflict markers in a
skill a robot is about to run. Four lanes, one owner each — Robot (`skills/`,
`workflows/`, `worlds/`, `objects/`), Agent (`agent/`), Knowledge (`tacit/`),
Demo (`media/`, `docs/pitch/`). Sync every 20–30 minutes.

**The agent writes to `out/`, never to `skills/`.** A human promotes a draft when
it is ready — one writer per file, plus a review step we would want anyway.

## The runtime API, as observed in the seeded skills

Read [the docs](https://readme.zeonsystems.app) before authoring, but this is the
shape:

| Call | Does |
|---|---|
| `move_arm(arm, position, orientation, speed, wait)` | Cartesian move to a pose |
| `move_arm_js(arm, joint_angles, speed)` | joint-space move (used for home poses) |
| `move_relative(arm, delta_xyz, delta_rpy)` | offset from current pose — retracts |
| `set_gripper(arm, width_m)` | gripper opening in metres |
| `load_object_anchor(object_id, anchor)` | named anchor on an object → `{xyz, rpy}` |
| `attach_object_to_arm(object_id, arm)` | object travels with the arm |
| `get_object_pose(name)` | current world pose, **matched by display name, not UUID** |
| `set_skill_variable`, `shared_state` | pass state between skills in a workflow |
| `print_log(...)` | run log; `runlog_type="step_start"` marks a step |

**A skill's parameters come from the Python function signature** in
`robotic_code.py` — not from `metadata.yaml`. Editing the metadata to add a
parameter does nothing. Objects are typed `SkillObject`; anchors are strings, so
one skill works for any object carrying that anchor.

## Working on this

```bash
pip install -r requirements.txt
python -m agent               # model-free — no API key, no network
python -m agent --agent       # live agent; needs GEMINI_API_KEY
python tacit/validate.py      # every extracted parameter traces to a transcript
```

### The Zeon loop

```bash
zeon auth login --global          # once per machine, opens a browser
zeon clone tacit-teacher          # teammates start here
zeon sync                         # pull before you edit
#   ... edit skills/ workflows/ worlds/ ...
zeon status && zeon diff          # review
zeon sync -m "what changed"       # commit + merge + push, atomically
```

Then open the web app, **hit Refresh in the header** (it will not see your push
otherwise), and run against the simulator before any real arm moves.
**Workflows execute only through the web UI, never from the CLI.**

Git and Zeon are both in play here: **Zeon is how work reaches the robot**, git is
for review and history. `.zeon/` is gitignored — clone from Zeon, not from git, to
get a working tree.

## Three things that will cost you an hour if nobody says them

**`gemini-2.0-flash` has no free-tier quota.** It returns `429
RESOURCE_EXHAUSTED` with `limit: 0` — it fails on the *first* call, not under
load, so it reads as a broken integration rather than a quota problem. Default
here is `gemini-2.5-flash`; override with `TACIT_MODEL`.

**`zeon init` does not seed a project.** It pushes whatever is already on disk and
requires `skills/`, `workflows/`, `worlds/` to exist. Only `zeon new project` gets
you the seeded scaffold from the server. We learned this by creating an empty
project and having to consolidate onto the seeded one.

**`get_object_pose` matches by display name, not UUID.** Resolve the name first.

**`zeon sync` pushes files `.gitignore` excludes.** Probed, not assumed: a PNG
dropped in `media/stills/` shows up as `Added`. It does auto-exclude
`__pycache__` and `.pyc`, which is exactly enough to lull you — content files
have no such protection. Keep binaries out of the tree; see
[`media/README.md`](media/README.md).

## Principles carried from Track A

- **The model-free path is the demo path.** A live model is the most likely thing
  to fail on stage, so it is never what the demo depends on.
- **Confine model-supplied file paths.** A hallucinated `../../` is a real
  overwrite; only basenames survive.
- **"Validated" means checked against a source of truth**, not "it parsed". On
  Track A a hand-written molecule parsed cleanly and was the wrong compound.
- **Put the human at the checkpoints that cost something.** Between a cheap step
  and an expensive one, stop and ask.

## Open design question

The tools in `agent.py` are placeholders. The build depends on how the expert's
knowledge actually gets in, and we have not settled it:

1. **Agent interviews the expert** — plain-language description, agent asks the
   follow-ups that change robot behaviour, then authors the skill. No extra
   hardware; the transcript is the artifact.
2. **Human demonstrates once, agent generalizes** — teleop or kinesthetic trace
   becomes a parameterized skill. Compelling, but depends on trace capture.
3. **Human corrects a failed attempt** — robot tries, fails, human says why in one
   sentence, agent edits the skill. Best narrative; needs a task that fails
   reliably and a fast enough sim cycle.

Pick one before writing the real tools.
