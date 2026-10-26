# DAISY-BB-004 amendment 4: correct cause of the values-gate defect (attempt v3 invalid too)

Amendment 3 is not edited; this corrects it.

- **Real cause:** Ultralytics 8.4.188 keeps the running training loss `tloss` as a **dict** `{name: tensor}`, not a tensor. The gate's converter did not handle a dict, returned no values, judged the epoch not finite and stopped training. Moving the read to `on_train_epoch_end` (amendment 3) did not touch the cause, so attempt **`004_v3` also stopped after one epoch** and is invalid in the same way (kept on the drive as evidence, numbers not interpreted).
- **Fix:** a `loss_values()` helper that accepts a dict, a tensor, a list of tensors or None, and returns floats (or nothing, which still fails closed). Checked against stand-in values before the next attempt.
- **Unchanged:** protocol file and sha256 (`31b1b0a6…`), data root, init pin, runs, 15 epochs, imgsz, batch, seed, gates, decision rule. Next attempt: `004_v4` on MPS.
