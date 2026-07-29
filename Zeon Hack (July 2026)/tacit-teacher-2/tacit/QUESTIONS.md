# The interview taxonomy

The questions we always ask. This file is the reusable asset — the skill for one
task is disposable, but a question set that reliably extracts what a robot needs
transfers to every task after it.

**The rule that keeps an interview short:** only ask what changes what the robot
does. "How long have you been doing this?" is rapport, not a parameter. "Does it
give suddenly or gradually?" is a force threshold.

Every question below maps to a field in [`schema.md`](schema.md). If a question
does not map to a field, either add the field or drop the question.

---

## 1. Geometry — where things are and how you get there

- Where does the object sit at rest, and how repeatably? Does it need locating first?
- From which direction do you approach? Is there a direction that does not work?
- Is there a pose you move to *before* the real one? (This is the prepose, and
  experts almost never mention it unprompted — they just do it.)
- Do you reorient once you have it, before moving away?
- How far do you retract, and in which direction? Straight up, or along an axis?

## 2. Force — how hard, and how you know

- How firmly do you hold it? Would it slip at half that? Deform at twice?
- Does the resistance change during the motion? At what point?
- Is there a moment where you *feel* it succeed? Describe the feeling.
- What would tell you, by feel alone, that it has gone wrong?

## 3. Speed and timing — where haste costs you

- Which parts do you do quickly, and which slowly? Why the difference?
- Do you pause anywhere? What are you waiting for?
- Does anything need to settle before the next step?

## 4. Verification — how you know it worked

- After this step, how do you *check* before moving on?
- What does success look like, from the outside? What does failure look like?
- Could it look right and be wrong? What would you check then?
- If you couldn't see it — only feel it — could you still tell?

## 5. Failure and recovery — the part that never gets written down

- What goes wrong most often?
- When that happens, what do you do — retry, back off, start over, stop?
- How many times would you retry before stopping?
- Is there a failure where retrying makes it *worse*?
- What would you never let a trainee do here?

## 6. Variation — what the robot will meet that you didn't mention

- Does this differ between brands, sizes, or batches?
- What changes when the object is full versus empty? Cold versus room temperature?
- Is there a variant of this object where your technique does not work?

---

## Asking well

**One question at a time.** Experts compress; a multi-part question gets a
one-part answer and you lose the rest.

**Ask for the number, then the tolerance.** "About 3 centimetres" is a parameter.
"Does 2 work? Does 5?" turns it into a range, which is what a robot needs.

**Chase the verbs.** "Then you *ease* it off" — ease how? Slower, or lighter, or
at a different angle? The verb is where the tacit knowledge hides.

**Record the answer before you interpret it.** The transcript is evidence; the
extracted parameters are an interpretation. When the robot fails, you need to
know which one was wrong.
