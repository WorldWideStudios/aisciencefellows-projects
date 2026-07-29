# peel_seal — what the video showed

**Evidence, not interpretation** — the same standing as `10-transcript.md`, from
a different sense. This file records what a camera could resolve; the transcript
records what a person could say. `20-extracted.yaml` interprets both.

```yaml
clips: V1-V9
time_scale: 1.0          # video seconds per real second; all clips 30 fps, no slow-motion
source: gs://tacit-teacher-media/media/peel-vids/
model: gemini-2.5-flash (Vertex AI, structured output, temperature 0)
captured: 2026-07-25
raw: ../../../docs/peel-video/observed.json
```

Clip → object mapping is in [`media/MANIFEST.md`](../../../media/MANIFEST.md).

---

## Timeline — correct practice (V1–V4)

All four clips show the same four-phase structure. Timestamps are per clip.

| Phase | V1 | V2 | V3 | V4 |
|---|---|---|---|---|
| Secure the plate | 00:15–00:37 | 00:06–00:11 | 00:06–00:28 | 00:05–00:13 |
| Grip mat edge/corner | 00:37–00:57 | 00:11–00:15 | 00:10–00:15 | 00:13–00:19 |
| Peel, slow and continuous | 00:57–01:15 | 00:15–00:34 | 00:15–00:28 | 00:19–00:36 |
| Set mat down | 01:15–01:23 | 00:34–00:38 | 00:30–00:31 | 00:36–00:42 |

Peel duration: **13 s (V3), 17 s (V4), 18 s (V1), 19 s (V2)**. No pauses in any
clip.

## Narration — correct practice

Verbatim, as spoken during the task.

**V1@00:15** — "The first element is to hold the plate tightly at place with
sufficient enough force so the plate does not move in any direction. I accomplish
it by using my right hand and pushing it against the table while squeezing it
from both sides."

**V1@00:37** — "Next step, I will find the edge of the rubber seal. Push my thumb
underneath and slowly start peeling while holding with the first joint of my
finger of my index finger, so [it] does not go too fast."

**V1@00:57** — "Then slowly while [it] is being peeled, I increase the pressure
and slowly continue it without shaking any of the liquid."

**V2@00:11** — "And we're going to hold the edge of the seal and mat … and move
it upwards gently with equal pressure throughout the whole mat."

**V3@00:15** — "Gently pull it upwards while firmly pressing index and thumb. We
gently with equal force pull it towards the other angle without disturbing the
liquid."

**V4@00:05** — "First we tightly secure the plate from the sides and press it
against the table. **Two forces, one from the side, one against the table.**"

**V4@00:22** — "While maintaining the force, we make sure that we don't increase
the speed of peeling because we're gonna contaminate the wells. We slowly
continue until the last well is removed."

## Failure modes — deliberate errors (V5–V9)

All five were staged with blue dye in the wells, which is why every symptom is
visible. That is a capture technique, not a property of the task: **the dye
converts an invisible failure into a camera-detectable one.**

| id | What was done wrong | Visible symptom | At |
|---|---|---|---|
| V5 | peeled too fast and forcefully | dye splashed onto plate surface and mat | 00:16 |
| V6 | peeled too fast and forcefully | dye on bench, on mat underside, on plate rim — transfer between wells | 00:13 |
| V7 | **insufficient upward pressure** | **mat stays sealed, fails to detach; liquid stays contained** | 00:15 |
| V8 | pulled one corner upward too fast | plate flips out, contents spill | 00:17 |
| V9 | mat set face-down on bench, then replaced | dye residue on bench where the mat lay | 00:26 |

**V5@00:16** — "…and then we move faster. Whoa, look at that. We see how the
elements of our protein extract are contaminated and they are outside of the
plate. This is failed experiment."

**V7@00:15** — "it doesn't pull because we don't apply enough upward pressure.
The mat stays sealed. Task is incomplete."

**V9@00:26** — "This is failure because we put it the same way how it was on the
plate. And we have cross contamination that you can visibly see on the table from
multiple wells."

---

## What the video could not see

The blind spots, recorded per the rule that an empty list means nobody pushed
hard enough.

### Force — every good clip flagged this independently

- sufficient force to hold the plate down [V1]
- pressure applied during peeling [V1, V2]
- torque applied during peeling [V2]
- grip pressure on the mat [V2]
- force applied by index and thumb [V3]

The model declined to estimate any of these rather than producing a plausible
number. **These come from the person or they do not exist.**

### Disputed, not unknown — the peel angle

Four estimates of the same motion by the same operator: **45° [V1], ~45° [V2],
~45° decreasing through the pull [V3], 60–90° [V4]**. Recorded as a range and a
disagreement rather than averaged. This is what `method: vlm_estimate` is for.

### Not answerable from this footage at all

- **Recovery.** No clip shows anyone reacting to a failure — the errors are
  staged and end there. What you *do* after V7 was never filmed.
- **Verification.** Only V3 and V4 produced anything, and both amount to "the
  narrator said it worked". Nobody is shown checking.
- **Variation.** One operator, one plate, one fill level, one temperature.

### Known weakness in this pass

`cannot_determine` came back **empty on four of the five error clips** and on V4.
By our own rule that is a prompt failure, not a clean result — the error-clip
prompt does not force a blind-spot list the way the good-clip prompt does. Fix
before the next capture.

**No slow-motion footage.** All nine clips are 30 fps and Gemini samples at a
fixed 1 fps, so V5's splash at 00:13–00:16 is covered by roughly three frames.
It resolved here; a faster failure would not. Film failure modes in slow motion
and set `time_scale` accordingly — a duration read off an 8× slow-motion clip is
wrong by 8× and looks entirely reasonable.
