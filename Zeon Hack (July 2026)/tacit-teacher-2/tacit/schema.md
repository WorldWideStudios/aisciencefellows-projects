# The extracted-knowledge schema

What one interview turns into. This is the interface between the person who knows
the technique and the Python that runs on the arm — the agent fills it in, a
human checks it, and a skill is generated from it.

Every field carries a `source` pointing at the transcript. **A parameter with no
source is a guess**, and guesses are exactly what this project exists to
eliminate. The validator (`tacit/validate.py`) fails on any parameter without one.

## `20-extracted.yaml`

```yaml
task: uncap_cryovial            # matches the skill id we will author
object: cryovial_2ml            # object model this applies to
expert: A. Rivera               # who we learned it from
captured: 2026-07-25

geometry:
  approach_from: above          # above | side | angled
  prepose:
    offset_m: [0.0, 0.0, 0.04]  # where you go before the real pose
    source: Q4                  # ← the answer that justifies this
  retract:
    direction: [0.0, 0.0, 1.0]
    distance_m: 0.05
    source: Q11

force:
  grip:
    - stage: open               # open → contact → clamp, as in epipette_grab
      width_m: 0.05
      source: Q6
    - stage: contact
      width_m: 0.035
      source: Q6
    - stage: clamp
      width_m: 0.012
      source: Q7
  notes: "Deforms above ~15 N. Slips below contact width 0.04."

timing:
  - after: contact
    settle_s: 0.5
    reason: "let the cap stop swinging before torque"
    source: Q8

verification:                   # how you know it worked — Track C's other half
  - check: cap_free
    signal: "resistance drops to zero as it lifts"
    method: force_threshold
    threshold_n: 1.0
    on_pass: continue
    on_fail: retry
    source: Q13

failure_modes:                  # the part that never gets written down
  - name: cross_threaded
    symptom: "resistance rises instead of falling"
    recovery: "back off a quarter turn, retry once"
    max_retries: 1
    then: stop_and_ask
    source: Q17
  - name: slipped
    symptom: "gripper closes past clamp width"
    recovery: regrasp
    max_retries: 2
    then: stop_and_ask
    source: Q18

variation:
  - condition: "vial is cold from the freezer"
    effect: "cap is tighter; needs more torque"
    source: Q21

unknowns:                       # what we asked and did not get
  - "Torque limit — expert said 'you just feel it', no number available."
```

## Rules

**`source` is mandatory on every parameter.** It names a question id in
`10-transcript.md`. This is the whole provenance chain: a number in the robot code
traces to a sentence a human said.

**`unknowns` is not optional.** An empty `unknowns` list on a real interview means
nobody pushed hard enough. Recording what you failed to extract is as useful as
what you got — it tells the next session where to dig.

**Units are in the field name** (`_m`, `_s`, `_n`, `_pct`). No bare numbers. The
Track A postmortem on this team included a bug where seconds and minutes were
interchangeable and every downstream number stayed plausible — name the unit.

**`verification` before `failure_modes`.** You cannot recover from a failure you
cannot detect. If a failure mode has no matching verification check, that is a
gap, not a design choice.
