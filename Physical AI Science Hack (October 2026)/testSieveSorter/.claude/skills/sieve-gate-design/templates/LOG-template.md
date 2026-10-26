# Gate design log: <sample name>

- **One file per sample**, at `gate_runs/<sample>/LOG.md` next to `spec.toml`. Newest iteration at the bottom.
- `gatecalc.py ... --log` appends its own sections; write the rest by hand.
- **Tag every number** as one of:
  - **measured**: bench, calipers, scale;
  - **executed**: computed or simulated here, with the command;
  - **cited**: a source link;
  - **assumed**: a placeholder.

## Status (keep this block current; the next agent reads it first)

- Spec: `gate_runs/<sample>/spec.toml`, iteration NN
- Plate and fit rule: e.g. std96_flat, below_rim, leaning accepted
- Gate sequence, nominal, top first: e.g. L1 `gate_w4p5`, L2 `gate_t1p55`, catch
- Printed and measured: which strips exist and their measured openings
- Sim status: e.g. 3 seeds on the pool proxy, firmware 50 mm/s; not yet with spray
- Bench status: e.g. none, or N counted runs
- Open questions:
- Next step:

---

## Iteration NN: YYYY-MM-DD, <goal in one line>

### Spec changes
What changed in `spec.toml` and why. For example: "item dims now measured, 30 per kind (sim/bench/grain_dims.csv)", or "p_roll 0.5 -> 0.3 from sim".

### Plan
`gatecalc plan` / `check` output is appended below. Note the gate sequence you chose and why, and the runners-up you rejected.

### CAD

| part | STRIPS line added | valid / single / watertight / fits_bed | openings, opening_mm | slice min / g |
|---|---|---|---|---|

### Sim
- Design and mapping: e.g. `pool:w4p35,t1p4` = printed w4.5 / t1.55 nominal at 0.15 undersize
- Commands: mix, stroke, duration, seeds, friction, spray, `--out` dirs
- Summary: `gatecalc sim` output appended below
- Verdict against the baseline: recovery and contamination per level beyond seed sd? Jams? Beyond-geometry = 0? Transport-limited?

### Print
- Printer, profile, layer height, filament, parts on the plate, time and grams
- Measured openings (10 per strip, bed side included; rows copied to `sim/bench/openings.csv`)

### Bench
- Protocol: sim/BENCH.md section, mix, stroke as set in firmware, spray, duration, repeats
- Count matrix, kind x level, including `between` (jammed) and `lost`, one table per repeat or mean ± sd
- Damage, snagging, manual interventions
- Roll-only items that passed (observed p_roll)
- Rows written to: `gate_runs/<sample>/bench_counts.csv` (gated tower) and/or `sim/bench/bench_counts.csv` (pool / inserts)

### Decision and next
What we keep, what we change, and the exact next command.
