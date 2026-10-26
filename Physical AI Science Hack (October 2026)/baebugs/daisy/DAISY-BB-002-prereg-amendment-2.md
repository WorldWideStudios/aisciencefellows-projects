# DAISY-BB-002 — preregistration amendment 2 → protocol DAISY-BB-002a

DAISY-BB-002 was frozen (commit 15941d3) but NEVER RAN: its Kaggle push loop was still waiting for a GPU
slot and was stopped by the agent at 2026-10-25 ~08:00 UTC; Kaggle shows no bb-002 kernel. DAISY-BB-002.json,
the preregistration and amendment 1 stay unchanged. This amendment is committed before the rebuilt data.

## Evidence
domain_split (amendment 1) left 428 r3 photos unresolved: no byte-identical file in any source.
work/unresolved_diag.json: every one of them has a file with the SAME GBIF media id in exactly one source
(CA 372, OR 52, NV 2, AZ 2), with identical pixel dimensions and about half the bytes — the r3 copies were
re-encoded, so byte identity was too strict a test of "same photo". Effect of the 002 rule: 372 CA photos
dropped from training and 56 out-of-state photos dropped from the holdouts (holdout_or 80 instead of ~132).

## Amended identity rule (002a)
An r3 photo belongs to source s if (a) a byte-identical file exists in s, or else (b) a file with the same
GBIF media id exists in s with identical width x height and mean absolute pixel difference <= 4 grey levels
(of 255) after decoding both. Rule (b) matches are recorded per photo (media id, state, mean abs diff).
Photos matching neither, or matching more than one state, stay excluded and are counted.

## Everything else unchanged from amendment 1
Runs CA_only and Synth_only, measures, decision rule, settings, gates, variance, per-run leakage gate
(byte level on staged files, plus media-id level across train vs val members, which must also be zero).
