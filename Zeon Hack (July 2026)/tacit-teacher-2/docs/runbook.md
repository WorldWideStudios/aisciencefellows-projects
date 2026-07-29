# Runbook — four people, one cloud HEAD

The thing that will hurt us is not the code. It is that **Zeon has a single cloud
HEAD and `zeon sync` merges into it**, so two people editing the same file at the
same time get conflict markers written into a Python skill that a robot is about
to run. Ownership lanes are not bureaucracy here; they are how we avoid that.

## Lanes

Each directory has exactly one owner. Anyone may *read* anything; you *edit* your
own lane, or you ask.

| Lane | Owns | Deliverable |
|---|---|---|
| **Robot** | `skills/`, `workflows/`, `worlds/`, `objects/` | a skill that runs in sim, then on the arm |
| **Agent** | `agent/` | the interview → draft-skill pipeline |
| **Knowledge** | `tacit/` | at least one complete session, transcript through outcome |
| **Demo** | `media/`, `docs/pitch/`, the README | the story, told in under three minutes |

`CLAUDE.md`, `project.json` and `requirements.txt` are shared — announce before
editing.

**The Robot and Agent lanes collide by design**, because the agent's whole job is
to write into `skills/`. Rule: **the agent writes to `out/`, never to `skills/`.**
A human copies a drafted skill into `skills/` when it is ready. That keeps one
writer per file and gives us a review step we would want anyway.

## Sync discipline

```bash
zeon sync                     # ALWAYS pull before you start editing
# ... work in your lane ...
zeon status && zeon diff      # look at what you are about to push
zeon sync -m "what changed"   # commit + merge + push, atomically
```

**Sync often — every 20–30 minutes.** Long-lived divergence is what turns a merge
into an incident. If `zeon sync` writes conflict markers into a file, do not
hand-resolve a skill you do not own: tell the owner.

Then, in the web app, **hit Refresh in the header** — an open tab does not see
your push. Workflows run only through the web UI, never the CLI.

## Git and Zeon are both live

They are not redundant, and neither one is optional:

- **Zeon** is how work reaches the robot. `zeon clone` gets you a working tree.
- **Git** is review and history. It does not move anything to the robot.

Clone from Zeon, not from git.

## No binaries in this tree

**`zeon sync` pushes everything, including files listed in `.gitignore`** —
verified, not assumed. A video dropped in `media/` goes to the cloud on every
sync, for everyone, forever.

So: `media/stills/` takes small PNGs only. Everything heavy — screen recordings,
robot video, raw audio from interviews — lives on the shared drive, with a link in
`media/MANIFEST.md`. See [`media/README.md`](../media/README.md).

## Definition of done, per lane

Nobody is done because their code runs. Done means the next person can use it.

- **Robot:** the skill runs in the simulator, parameters come from the function
  signature, and `metadata.yaml` describes it truthfully.
- **Agent:** it runs model-free with no API key. If it only works with a live
  model, it is not done — that is the single point of failure we refuse to have.
- **Knowledge:** a session directory with all four files, every parameter carrying
  a `source`, and `unknowns` non-empty.
- **Demo:** someone who has never seen the project understands it in 90 seconds.

## Standing decisions

- **The model-free path is the demo path.** A live model is the most likely thing
  to fail on stage, so it is never what the demo depends on.
- **`gemini-2.0-flash` has zero free-tier quota** — 429 on the first call. Use
  `gemini-2.5-flash`; override with `TACIT_MODEL`.
- **A skill's parameters come from the Python signature**, not `metadata.yaml`.
- **`get_object_pose` matches by display name, not UUID.**
- **`zeon init` does not seed a project.** Only `zeon new project` does. We lost
  twenty minutes to this; do not repeat it.
