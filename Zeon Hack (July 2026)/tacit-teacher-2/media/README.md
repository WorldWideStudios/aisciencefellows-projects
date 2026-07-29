# media

## The rule: no binaries in this tree

`zeon sync` pushes **every file in the working tree, including ones listed in
`.gitignore`** — verified by probe, not assumed. A 200 MB screen recording
dropped in here goes to the cloud on every sync, for all four of us, permanently.

| Where | What |
|---|---|
| `media/stills/` | small PNG/JPG only — screenshots, diagrams. Keep under ~500 KB each. |
| `media/MANIFEST.md` | links to everything heavy, hosted elsewhere |
| shared drive | video, raw interview audio, anything large |

If you are about to `cp` something over 1 MB into this directory, put it on the
shared drive and add a line to the manifest instead.

## What we actually need captured

The submission is a story, and the story needs footage taken *while things are
happening* — nobody can reconstruct it at 13:00 on Sunday.

- **The expert being interviewed.** This is the project. Audio at minimum.
- **The robot failing first**, then succeeding after the knowledge transfer. The
  before/after pair is the whole argument; the failure is worth more than the success.
- **The screen** during an agent run — the questions it chose to ask.
- **Stills of the physical setup** — the deck, the object, the gripper at the
  moment of contact.
