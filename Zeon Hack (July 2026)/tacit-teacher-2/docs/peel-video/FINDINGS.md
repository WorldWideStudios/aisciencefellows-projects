# Peel video pass — what we got, and what the video could not tell us

**2026-07-25** · task `peel_seal` (removing a rubber sealing mat from a 1 mL
deep-well plate) · nine clips, one operator

## What happened

Nine narrated phone clips went through one Gemini 2.5 Flash call each, on Vertex
AI, with structured output. Two prompts, because the clips answer different
questions: the four correct takes produce the procedure, the five deliberate
errors produce the failure modes. A tenth call merged them into
[`HOW-TO.md`](HOW-TO.md) and [`WHAT-NOT-TO-DO.md`](WHAT-NOT-TO-DO.md).

Raw per-clip extraction is in [`observed.json`](observed.json). Every claim in
both documents carries a `[V<n>@MM:SS]` citation back to it.

| V-id | file | | what it shows |
|---|---|---|---|
| V1 | `IMG_0764` | good | full narrated walkthrough, 84 s |
| V2 | `IMG_0766` | good | slow even peel |
| V3 | `IMG_0767` | good | mat off without disturbing wells |
| V4 | `IMG_0774` | good | "two forces, one from the side, one against the table" |
| V5 | `IMG_0768` | **error** | too fast → splash |
| V6 | `IMG_0770` | **error** | too fast → cross-contamination |
| V7 | `IMG_0771` | **error** | insufficient upward pressure → mat stays sealed |
| V8 | `IMG_0772` | **error** | plate flips out, contents spill |
| V9 | `IMG_0773` | **error** | mat set face-down → benchtop contamination |

Clips live at `gs://tacit-teacher-media/media/peel-vids/` — see
[`media/MANIFEST.md`](../../media/MANIFEST.md). Nothing heavy is in this tree.

## What the video could not answer

This is the part that matters. The video is good at geometry and timing and
blind to everything else, which is exactly the split
[`tacit/QUESTIONS.md`](../../tacit/QUESTIONS.md) already draws.

Every good clip independently put **force** in `cannot_determine`, unprompted by
any example:

- sufficient force to hold the plate down [V1]
- pressure applied during peeling [V1, V2]
- torque applied during peeling [V2]
- grip pressure on the mat [V2]
- force applied by index and thumb [V3]

The model declined to guess, which is the behaviour we wanted. **These numbers
have to come from the person.**

### The interview agenda

Ask only these. They are what the footage failed to settle.

1. **How hard do you press the plate down?** Would half that hold it? All four
   good clips describe securing the plate; none reveal the force.
2. **How hard do you grip the mat corner** before it tears, or slips?
3. **Is the peel angle 45° or steeper?** V1–V3 read as ~45°, V4 reads as 60–90°.
   Same operator, same technique — did something change, or is the estimate just
   unreliable? (See "the pipeline caught itself" below.)
4. **How do you know it worked, before you look at the wells?** The narration
   says *"this is complete successful procedure"* but never says what was
   checked. This is the highest-value question on the list and video cannot
   touch it.
5. **In V7 the mat stayed sealed. Do you retry, or reposition?** How many times
   before stopping?
6. **What changes with a full plate versus half-full? Cold versus room
   temperature?** One plate, one mat, one temperature is all we filmed.

## Three findings that change the robot design

**V7 is the most valuable clip.** Four of the five failures end in spilled blue
dye. V7 does not — the mat stays sealed, nothing spills, the wells stay clean,
and the task is simply not done. *"The mat stays sealed. Task is incomplete."*

A verification that looks for spilled dye **passes V7**. So the skill needs two
independent checks, not one:

- *did anything spill?* → contamination check (V5, V6, V8, V9)
- *is the mat actually off?* → completion check (V7)

That came out of the footage, not out of anyone reasoning about it.

**The pipeline caught its own unreliability.** Peel angle across the four good
clips: 45°, ~45°, ~45° (decreasing through the pull), 60–90°. One operator, one
technique, a 45–90° spread. The synthesis reported the disagreement rather than
averaging it, which is the correct behaviour and the reason every extracted
value needs a `method:` marker. **This number cannot enter a skill until the
expert confirms it or it is measured.**

**Both hands are working, and the operator says so.** V4: *"Two forces, one from
the side, one against the table."* Planar stability is not an inference we made,
it is a stated requirement — so it earns a citation from the transcript and from
the video. The robot gets it from a fixture; the point is that we know we need
it.

## Weaknesses in this pass

Recorded because they tell the next person where to dig.

**`cannot_determine` came back empty on four of the five error clips**, and on
V4. By our own rule — an empty `unknowns` means nobody pushed hard enough — that
is a prompt failure, not a clean result. The error-clip prompt does not force a
blind-spot list the way the good-clip prompt does. Fix before the next capture.

**Verification is thin.** Only V3 and V4 produced anything under
`verification`, and both amount to "the narrator said it worked". Track C is
half dexterity and half physical verification; this pass delivered the first
half.

**No slow-motion footage.** All nine clips are 30 fps, and Gemini samples video
at a fixed 1 fps. V5's splash occupies 00:13–00:16, so roughly three sampled
frames cover the actual event. It worked here, but a faster failure would be
invisible. Film failure modes in the phone's slow-motion mode and record the
`time_scale` — durations read off a slow-motion clip are wrong by the slowdown
factor and look entirely plausible.

**One operator, one session.** Everything here is a single person's technique on
a single plate. `variation` is empty for a reason, and that reason is not that
there is no variation.

## Re-running

```bash
gcloud auth application-default login          # once
python3 tacit/observe.py                       # 9 clips -> out/peel_seal/observed.json
python3 tacit/synthesize.py                    # -> out/peel_seal/{HOW-TO,WHAT-NOT-TO-DO}.md
```

Output goes to `out/`, never straight into a reviewed directory — a human
promotes a checked copy into `docs/peel-video/`, same discipline the runbook
applies to drafted skills.

Inference runs through **Vertex AI**, not an AI Studio API key. The Gemini API
defaults new projects to a *prepay* balance separate from Cloud billing, and
Cloud Welcome credits cannot be spent on it at all — so an API key cannot reach
the project's credit no matter how billing is linked. Vertex is an ordinary
Cloud service and bills normally.

## Next

The nine clips are processed and the agenda is written. The remaining work is
the interview — six questions, one person — and then
`tacit/sessions/peel_seal/` can be a complete session that actually validates.
Nothing in `tacit/sessions/` yet, which is why `python tacit/validate.py`
currently passes on zero sessions rather than on real ones.
