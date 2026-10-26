# DAISY-BB-004 amendment 2: Apple GPU (MPS) instead of CPU (filed before any result)

- **Why:** the CPU run (amendment 1) measured 9.5 s per batch, about 6 minutes per epoch, so 3 runs x 15 epochs would take roughly 4.5 hours and miss the 14:30 submission. It was stopped during epoch 1 of the first run; no epoch finished, no weights were saved, no metric was seen. Its events stay on the drive (`daisy/local/004_v1/events.jsonl`) as an aborted attempt.
- **Change:** the same kernel code runs with `device=mps` (Apple GPU on magicstudio), passed through `DAISY_DEVICE`; the environment gate records the device. Unset on Kaggle, so the frozen Kaggle notebook behaves as before.
- **Unchanged:** protocol file and sha256 (`31b1b0a6…`), data root, init weights pin, runs, epochs, imgsz, batch, seed, gates, decision rule. The protocol already says `deterministic=false`; the weights tensor sha remains the identity of each realization.
