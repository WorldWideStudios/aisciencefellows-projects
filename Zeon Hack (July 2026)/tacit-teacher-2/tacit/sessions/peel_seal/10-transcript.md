# peel_seal — transcript

Verbatim. **Evidence, not interpretation.** Do not clean up the expert's phrasing:
"it kind of gives" is a force threshold, and rewriting it to "the resistance
decreases" throws away the hedge that tells you it is approximate.

Number every question — `20-extracted.yaml` cites these ids.

---

## Interview conducted

Video pass produced the agenda below; Q1–Q6 answers are below.
Narration from V1–V9 stays in [`15-observed.md`](15-observed.md) as `V<n>@MM:SS`,
not as `Q<n>`.

### The agenda — six questions, in priority order

Derived from what the video could not determine. Ask in this order; the first
four are the ones that block the skill.

**Q1.** How hard do you press the plate down? Would half that force still hold
it? _(Every good clip shows the plate being secured; none reveal the force.
Blocks: `force.hold_down`.)_

**Q2.** How hard do you grip the mat corner — at what point does it tear, or
slip out of your fingers? _(Blocks: `force.grip`.)_

**Q3.** Is the peel angle about 45°, or steeper? _(V1–V3 read as ~45°, V4 reads
as 60–90°. Same person, same technique. Did something change between takes, or
is the estimate just unreliable? Blocks: `geometry.peel_angle_deg`.)_

**Q4.** How do you know it worked, before you look at the wells? _(The narration
says "this is complete successful procedure" but never says what was checked.
Highest-value question here, and video cannot touch it. Blocks:
`verification`.)_

**Q5.** In V7 the mat stayed sealed and nothing spilled. Do you retry, reposition,
or start over? How many times before you stop? _(Blocks: `failure_modes.*.recovery`
and `max_retries` — currently unknown for all five modes.)_

**Q6.** What changes with a full plate versus a half-full one? Cold from the
fridge versus room temperature? _(Blocks: `variation`, which is currently
empty — one operator, one plate, one temperature.)_

---

**Q1:** How hard do you press the plate down? Would half that force still hold
it?

**A1:** Press hard enough such that the plate doesn't move left/right or up
during the peeling process. Pushing is through thumb and forefinger. It is a
pretty hard push

**Q2:** How hard do you grip the mat corner — at what point does it tear, or
slip out of your fingers?

**A2:** as hard as humanly possible, because the mat will not break and gripping
it strongly gives control to the user.

> **Corrected 2026-07-25.** The first answer recorded here described gripper
> positions on a UFactory arm. The expert does not have access to that robot, so
> that answer was not their technique — it was someone else's implementation
> notes recorded in the expert's voice. Removed rather than kept alongside,
> because a transcript is evidence and evidence that is not the expert's does not
> belong in it. Anything that cited it is retracted; see the note in
> `20-extracted.yaml`.

**Q3:** Is the peel angle about 45°, or steeper?

**A3:** camera estimate is a bit off. The angle should be around 45 degrees each
time for the peel to come off. The same person was doing the process each time
in our videos

**Q4:** How do you know it worked, before you look at the wells?

**A4:** you know this process succeeded if the mat comes off the deep well plate
slowly enough to avoid transfering any liquid droplets between wells. Also the
deep well plate must not move around or be distrubed such that the contents are
not moving around significantly. Mat does need to detach so process also
succeeds when the mat comes off of the deep well plate.

**Q5:** In V7 the mat stayed sealed and nothing spilled. Do you retry,
reposition, or start over? How many times before you stop?

**A5:** yes if the mat stays on and nothing is spilled and the deep well plate
hasn't moved, you retry

retry just once because we don't have ways to validate the position of the deep
well plate hasn't changed

**Q6:** What changes with a full plate versus a half-full one? Cold from the
fridge versus room temperature?

**A6:** let's assume we are unaware of the temperature of the plate or its
contents. The temperature should always be room temperature. The contents don't
affect the peeling process or the pushing on the deep well plate.
