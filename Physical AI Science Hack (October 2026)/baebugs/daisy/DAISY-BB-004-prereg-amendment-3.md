# DAISY-BB-004 amendment 3: values-gate defect stopped training after epoch 1 (attempt v2 invalid)

- **What happened (attempt `004_v2`, MPS):** the per-epoch values gate read the training loss in `on_fit_epoch_end`, after Ultralytics had already reset it for the classification trainer. It saw no loss, judged the epoch "not finite", and stopped training, as a failed gate should. Every run therefore trained for about one epoch instead of the frozen 15.
- **Status of v2:** protocol deviation, **not a result**. Its weights were saved and verified (custody intact), and its events stay on the drive (`daisy/local/004_v2/`) as evidence of the defect, but its numbers are not interpreted and do not inform anything below.
- **Fix:** capture the loss in `on_train_epoch_end` (before validation) and have the gate read that value. Nothing else in the kernel changed.
- **Unchanged:** protocol file and sha256 (`31b1b0a6…`), data root, init pin, runs, epochs (15), imgsz, batch, seed, gates, decision rule. The next attempt is `004_v3` on MPS.
- **Lesson kept:** a gate that cannot read its input must fail closed (it did); the defect was in the reading, not the rule.
