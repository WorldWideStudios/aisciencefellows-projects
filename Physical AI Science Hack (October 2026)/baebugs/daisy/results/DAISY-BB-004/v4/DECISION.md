# DAISY-BB-004 v4: per-taxon preprocessors (MPS, amendments 1–4)

All gates passed (G1 data root `4d5f2831…`, G2 init pin, G3a environment, values finite every epoch, 15 epochs per run). Weights for all three runs are stored on magicBLACKbox (`daisy/local/004_v4/*_best.pt`) and re-verified: custody **INTACT**.

Decision rule (frozen): USEFUL if test macro-F1 minus majority-class macro-F1 > 0.10. Test = AZ/NV/OR holdouts (outside California).

| run | classes | val macro-F1 | test macro-F1 | majority | verdict |
|---|---|---|---|---|---|
| ORDER | 6 | 0.919 | **0.700** | 0.135 | **USEFUL** (+0.565) |
| FAMILY_Hymenoptera | 7 | 0.883 | 0.167 | 0.068 | NULL (+0.099, under the 0.10 margin) |
| FAMILY_Diptera | 4 | 0.967 | — | — | no test crops; undecided |

Read honestly:
- The order router transfers outside California (test top-1 0.95). Its weak class is Hemiptera (test F1 0.0, few test crops).
- The Hymenoptera family model does not transfer: 0.88 in-state, 0.17 out of state. Treat it as California-only until it is retrained with out-of-state data; in an escalation ladder it should hand off, not decide.
- FAMILY_Diptera cannot be judged: no Diptera family crops in the holdouts.

Attempts v1 (CPU, stopped), v2 and v3 (values-gate defect, one epoch) are invalid and kept on the drive as evidence (amendments 1–4).
