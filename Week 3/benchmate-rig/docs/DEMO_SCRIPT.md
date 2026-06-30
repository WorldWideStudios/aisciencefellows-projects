# 2-minute demo video — script & shot list

Goal: show it working, explain why it matters, say what's next. Keep it under 2 min.
Have `pump_and_watch_color.py` ready to Run in Thonny, and the build deck open for the
components slide. Bump the Thonny font up (`Cmd +`) so the numbers are readable.

---

**[0:00–0:15] Hook — what it is** *(on camera, or over a wide shot of the rig)*
> "This is a DIY cell-viability reader I built at home for about $60, for my AI
> co-scientist, Benchmate. It reads the color change of alamarBlue — the standard
> way to measure whether cells are alive — and it can dose liquid on its own."

**[0:15–0:45] Components** *(point at each part, or show the deck's components slide)*
> "Four cheap parts: a Raspberry Pi Pico runs everything over USB; an RGB color
> sensor reads the well; a peristaltic pump adds reagent; and a MOSFET lets the
> tiny Pico switch the 12-volt pump. That's it."

**[0:45–1:20] Live demo** *(screen + the well on the sensor)*
> "Here's a well of alamarBlue — blue right now. I hit Run…"
> *(Run `pump_and_watch_color.py`. It reads the blue baseline, the pump kicks in,
> you swirl the well.)*
> "…the pump adds the reductant — standing in for what live cells do — and watch
> the red-to-blue number climb as it turns pink. Blue to pink, measured automatically."

**[1:20–1:45] Why it matters**
> "That blue-to-pink shift is a viability readout. So this little rig is the
> wet-lab half of Benchmate: today Benchmate just *proposes* hypotheses about what
> kills or rescues cells — now it can actually *test* one and get a real number back."

**[1:45–2:00] What's next**
> "Next I'm scaling it to a 6-well plate for full dose-response curves, and wiring
> the results straight into Benchmate. But step one works: it senses, it doses, it
> reads. Thanks for watching."

---

### Tips
- Record the live demo run **once beforehand** so you know it triggers cleanly.
- If the live blue→pink is slow on camera, pre-mix a pink "after" well and cut to it,
  or speed up that section in editing.
- A 15-second version = just the live demo (0:45–1:20) plus the first line of "why it matters."
