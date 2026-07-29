# peel_seal — brief

**Expert:** (operator in V1–V9, name pending)
**Interviewer:** pending — interview not yet conducted
**Date:** 2026-07-25 (footage captured; interview outstanding)
**Object:** deep-well plate, 1 mL wells, with rubber sealing mat
**Target skill id:** `peel_seal`

## The task in one sentence

Remove the rubber sealing mat from a deep-well plate without disturbing the
liquid in the wells.

## Why it is hard for a robot

The mat is a **deformable body under tension**, and the whole technique is about
managing how that tension releases. Three things make it dexterity rather than
motion:

- **It is a two-handed task, and one hand is invisible in the protocol.** The
  operator states it outright in V4: *"Two forces, one from the side, one against
  the table."* A protocol says "remove the mat"; it does not say that a second
  hand is holding the plate down the entire time. Take that away and the plate
  lifts with the mat (V8, where the plate flips out entirely).
- **The controlling parameter is a force nobody can state.** Too little and the
  mat stays sealed (V7). Too much, too fast, and the wells aerosolise (V5, V6).
  The operator's own words are *"sufficient enough force"* and *"not too tight"* —
  which is exactly the knowledge this project exists to extract.
- **Failure is chemical, not mechanical.** Nothing breaks. Liquid moves between
  wells, and the run is dead. A sim cannot show this at all — a deformable mat
  peeling is not modelled, and snapping asserts poses rather than measuring them.

## What "done" looks like

Two independent observable conditions, and **both are required** — this is the
finding that came out of the footage rather than out of reasoning:

1. **The mat is off.** V7 is a failure in which nothing spills, nothing is
   contaminated, and the wells are pristine — the mat simply never detached.
   *"The mat stays sealed. Task is incomplete."*
2. **Nothing moved between wells.** V5, V6, V8 and V9 all end with visible blue
   dye outside the wells, on the mat underside, on the plate rim, or on the bench.

A check for only the second condition **passes V7**. A check for only the first
passes V6. The skill needs both.

## Status

Footage captured and processed ([`15-observed.md`](15-observed.md)), and the
interview conducted ([`10-transcript.md`](10-transcript.md), Q1–Q6). Both kinds
of evidence are in; `20-extracted.yaml` cites both and reports which is which.

Two things the interview changed that watching never would have:

- **The peel angle the camera reported was wrong.** The video pass estimated
  45–90° across four clips and flagged the spread as disputed. Q3: *"camera
  estimate is a bit off … around 45 degrees each time … the same person was
  doing the process each time."* The disagreement was the camera, not the
  technique. The superseded estimate is kept in the file.
- **Grip force has no upper bound.** Q2: *"as hard as humanly possible, because
  the mat will not break and gripping it strongly gives control to the user."*
  Most force parameters are a window you must stay inside. This one is bounded
  below only — the failure to design against is a slip, and crushing the mat is
  not a risk. That is unusual enough to be worth knowing, and no amount of video
  would have shown it.

## One retraction, and why it is in the record

A2 was originally answered with gripper positions on a UFactory arm and a claim
that the arm needs a two-stage pull. **The expert has no access to that robot.**
That answer was somebody's implementation notes recorded in the expert's voice —
an interpretation wearing the costume of knowledge, which is precisely what this
session structure exists to prevent, arriving through the front door.

It is corrected in `10-transcript.md` rather than quietly overwritten, and
everything that cited it is retracted: the gripper unit conversion (which never
happened — the units could not be resolved) and the two-stage-pull requirement
in `20-extracted.yaml`. Whether the arm needs two pulls is now an open
*engineering* question, not a piece of expert knowledge, and the skill draft has
it off by default.

Worth sitting with: **the validator did not catch this.** It checks that a source
exists, not that the source is the person named above.

Still open: no force figure exists in newtons anywhere, and **there is no way to
verify the plate has not moved** — the stated reason the retry limit is 1 rather
than higher.
