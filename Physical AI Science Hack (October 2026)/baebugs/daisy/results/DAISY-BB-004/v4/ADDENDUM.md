# DAISY-BB-004 v4: addendum to DECISION.md

DECISION.md is not edited; this adds three facts it leaves out. Verdicts are unchanged.

1. **Hemiptera test F1 0.0 rests on 2 crops.** ORDER test counts: Lepidoptera 118, Hymenoptera 87, Coleoptera 18, other 6, Hemiptera 2 (`daisy/taxon_crops_report.json`). The 0.0 is real but says almost nothing about Hemiptera transfer.
2. **The test split has no Diptera at all**, at order level as well as family level. ORDER's test macro-F1 (0.700) is therefore the mean over 5 classes, not 6; Diptera is scored only on val (F1 0.948). FAMILY_Diptera has an empty test split, so no verdict is possible under the frozen rule.
3. **Values gate.** Each run trained 15 epochs and all 15 `values_epoch` events pass (finite loss). Each run also logs a 16th `values_epoch` after the final validation with an empty loss list, recorded `finite: false, pass: false`. It comes after training ends and changes no weights; it is noted here rather than hidden.

## Resolvability check (re-run 2026-10-25)
`baebugs.resolve` over repo + `/Volumes/magicBLACKbox/baebugs/daisy`:

| run | weights sha256 | resolves to |
|---|---|---|
| ORDER | `8a9dcb7a…8f02` | `daisy/local/004_v4/ORDER_best.pt` |
| FAMILY_Hymenoptera | `002cc26e…5047` | `daisy/local/004_v4/FAMILY_Hymenoptera_best.pt` |
| FAMILY_Diptera | `cf0500dd…3243` | `daisy/local/004_v4/FAMILY_Diptera_best.pt` |

No 004 hash dangles: custody INTACT. Repo-wide 8 hashes dangle (001b v6 x6, 002a v2 x2); all 8 are already recorded `custody_break` events in `daisy/impact_mmr.jsonl`.
`events.jsonl` (sha256 `d284d477…d474`, 104 events, every `prev` links the previous `leaf`) and `results.json` (`41beb0f2…19f8`) in this folder are byte-identical to the drive copies.
