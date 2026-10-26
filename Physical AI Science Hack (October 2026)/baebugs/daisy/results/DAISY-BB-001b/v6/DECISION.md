# DAISY-BB-001b v6: executed, custody BROKEN (weights not stored)

- All six runs (A_synth, B_synth_pseudo, C_all, LODO_synth, LODO_pseudo, LODO_multires) trained and evaluated on Kaggle; data custody gates passed (roots match the frozen protocol).
- Status `OBSERVED_EXPLORATORY` for every run: the numbers are recorded, but they **cannot be used as evidence**, because the trained weights they came from were not exported (the kernel was pushed before the FINISH fix; it saved weights only for `EXECUTED`). Their sha256 values are in `results.json`, but no bytes exist anywhere.
- The resolvability invariant turned this into six explicit `custody_break` events in `daisy/impact_mmr.jsonl` (one per missing weights hash). The chain is broken for these six realizations, as it should be.
- Fix already in place for every later kernel: weights hashed every epoch, best.pt copied and re-verified right after training, fail-closed custody check before `results.json` is written.

Observed (exploratory, A_synth, mask mAP50-95): synth_seg 0.92, synth 1-30 mm 0.74–0.76, real pseudo-labelled specimens 0.25–0.26 at all three resolutions, teacher_check 0.002 (the same anomaly seen in 002a; not interpreted).

Next: rerun as v7 with the fixed kernel if the result is needed as evidence.
