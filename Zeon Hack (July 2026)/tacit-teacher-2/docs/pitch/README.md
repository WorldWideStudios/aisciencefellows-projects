# Pitch

**The argument, in the order it lands:**

1. A protocol says "pick up the pipette." The robot code says
   `set_gripper(0.05) → 0.035 → 0.012`, `speed=50` then `30`, `sleep(0.5)`,
   retract 5 cm. Nobody derived those numbers — someone learned them by watching
   it fail.
2. That knowledge is tacit. Today it reaches robots by accident, as magic numbers
   and comments left by whoever debugged it last.
3. tacit-teacher makes the transfer deliberate: interview the person who knows,
   ask only what changes robot behaviour, write it out as a skill — and keep the
   transcript separate from the interpretation so failures are diagnosable.
4. Show the robot failing. Show the interview. Show it succeeding.

Open `skills/epipette_grab/robotic_code.py` on screen for point 1 — it makes the
case better than a slide. Note it comes from the Zeon seed, so it is on your disk
after `zeon clone` but is not in the public GitHub repo; the README quotes the
relevant lines if you only have the repo.
