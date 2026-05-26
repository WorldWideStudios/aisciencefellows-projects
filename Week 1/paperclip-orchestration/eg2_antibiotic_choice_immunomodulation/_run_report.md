# abx_test_v2 run report

**Run window:** 2026-05-16 17:10 → 17:39 (wall-clock: ~29 minutes)
**Working directory:** `/Users/julia/paperclip-test/abx_test_v2/`

## Top-level summary

| Phase | Status | Notes |
|---|---|---|
| Phase 0 (scoping + anchors) | Completed | 7 scoping searches; 12 anchor candidates identified |
| SQ1 (PRRs) | Completed | 10 keepers; 13-row PRR pathway table |
| SQ2 (mechanism classes) | Completed | 12 keepers + Kapoor 2017 backbone + Ishak 2025 anchor; 17-row mechanism table |
| SQ3 (mechanism × immune) | Completed | 13 keepers; 13-row intersection table; **Rule C invoked** (see below) |
| SQ4 (clinical evidence) | Completed | 14 keepers; 14-row clinical-evidence table |
| Phase 2 (reconciliation, anchors, bibliography) | Completed | 15 verification anchors; full bibliography; 6 cross-cutting observations; this report |

**Total papers cited in the digest:** ~52 unique papers (counting across all sub-questions; anchor papers cited in multiple SQs counted once).

## Anchor reconciliation

Phase 0 identified 12 anchor candidates that the digest was expected to engage. **All 12 appear in the final digest at least once**:

| Anchor (Phase 0) | Where used | Notes |
|---|---|---|
| PMC4034004 Anderson 2010 — antibiotic × innate immune integrative | SQ3 keepers + multiple table rows | Used as multi-class SQ3 citation |
| PMC11605096 Gross 2024 — bactericidal/TLR9 | SQ1 (TLR9 row) + SQ3 (β-lactam row, mode-of-killing row, paragraph) + verification anchor | Most-cited single anchor |
| PMC7423293 Berti et al 2020 — antibiotics & innate immunity | SQ3 keepers + mode-of-killing-row citation | |
| PMC11117367 Tosi 2024 — sepsis review | SQ3 keepers + multiple table rows | |
| PMC11591424 Snow 2024 — antibiotic immunosuppression | SQ3 keepers + aminoglycoside/oxazolidinone/intracellular rows | |
| PMC3746177 Aminov 2013 — biotic acts of antibiotics | SQ3 keepers + macrolide & tetracycline rows | |
| PMC5859047 Zimmermann 2018 — macrolide systematic review | SQ3 keepers + macrolide row | |
| PMC8563091 Pollock & Chalmers 2021 — macrolide respiratory | SQ3 keepers + SQ4 keepers + macrolide row + verification anchor | Bridges SQ3 and SQ4 |
| PMC9616545 Lagos 2022 — TLR2/4 after 4 antibiotics | SQ3 keepers + fluoroquinolone row + verification anchor | |
| PMC11695898 Ishak 2025 — bactericidal vs static | SQ2 keepers (as anchor) + SQ4 keepers + verification anchor | |
| PMC7666448 Skorup 2020 — porcine sepsis mode of killing | SQ3 keepers + SQ4 keepers + verification anchor | Translational bridge |
| PMC4368383 Weiss & Schaible 2015 — macrophage defense | SQ1 keepers + multiple PRR rows + verification anchor | |

## Missing anchors

**None.** Empty list — all Phase 0 anchor candidates appear in the final digest with at least one citation.

## Sub-questions where evidence was thin or map fallback was used

- **SQ3 thin spot:** Aminoglycoside and rifamycin immune effects in the table rely on review-level summaries (PMC4034004, PMC11591424) rather than primary studies — the primary literature at clinically realistic concentrations is genuinely sparse, and broadening the search did not surface much. This is signal, not gap — these classes are real candidates for the "described in vitro at high dose but unclear at clinical exposure" caveat.
- **SQ2 thin spot:** Folate-pathway (sulfonamides + trimethoprim) and isoniazid mycolic-acid mechanism rows are cited only via the Kapoor 2017 multi-class review (PMC5672523) — dedicated class-specific reviews did not surface. This is acceptable for a clinician-scientist working reference but is a thin-citation spot.
- **No map-fallback to `paperclip cat`+grep was required.** `paperclip map` succeeded on every attempt; one map attempt against an accumulated `paperclip searches` result ID failed with "Results not found" but a brief sleep + retry against the per-search result ID resolved it. This was a minor harness quirk, not a content-extraction failure.

## Filter retries triggered by Rule C

**SQ3 first-pass filter** dropped 21/24 papers, leaving only 3 keepers (well below the `--require 10`). Per Rule C, inspected the dropped set: most were resistance-mechanism papers, AMR math models, and biofilm papers — appropriately filtered, not over-filtered. The right move was therefore **not to broaden the filter language** (which would have re-admitted off-topic papers) but to **supplement the candidate pool with a Phase-0-anchor retrieval pass** that targeted the canonical reviews and class-specific immune-effect studies by name. This recovered the 11-paper keeper set on the second pass, without compromising filter discipline. Documented inline in SQ3 "Search and filter notes."

Other filters (SQ1, SQ2, SQ4) did not require retries.

## Three to five unexpected findings worth attention on return

1. **The bacterial-DNA-via-TLR9 mechanism (Gross 2024) is the cleanest integrative finding in this literature** — it bridges SQ1 (TLR9 sensing), SQ2 (lytic vs non-lytic kill), and SQ3 (PAMP release amplifying inflammation), and the proposed clinical RCT testing it in human sepsis has not been done. This is the strongest "future trial worth designing" hook in the digest.
2. **Macrolide adjunct in non-severe hospitalized CAP appears null in recent large EHR data (PMC11998547, Wei 2025)** despite the older meta-analysis signal in severe CAP (PMC5143302, Lee 2017). The macrolide-immunomodulation signal seems severity-dependent, which is consistent with a mechanism that requires inflammatory burden to manifest — but means the routine practice of "add azithromycin to ceftriaxone" in non-severe inpatients may need re-examination.
3. **Polymyxin B haemoperfusion benefit is biomarker-defined**, not population-level (Iba 2025 narrative review of TIGRIS + EUPHRATES). The mechanism (LPS interception) is real but only translates in the high-endotoxin-activity / high-organ-dysfunction subgroup. This is a model for how SQ3-style mechanism hypotheses can translate clinically only under biomarker-stratified design.
4. **Aminov 2013 "Biotic acts of antibiotics"** (PMC3746177) is genuinely useful as an integrative reference and is under-cited in current discussions — it predates several recent papers but frames the macrolide/tetracycline/β-lactam non-antimicrobial host effects in one place.
5. **Segal 2017 (PMC5329050)** — azithromycin in emphysema selects for *anti-inflammatory bacterial metabolites* that blunt macrophage inflammation. The macrolide benefit may be partly **microbiome-mediated rather than direct host-cell action**. This reframes ~30 years of macrolide-immunomodulation work — the in vitro NF-κB / neutrophil chemotaxis effects may not be the dominant in-vivo mechanism after all.

## Honest self-assessment

**Strongest sub-questions:**
- **SQ3** turned out best. The mechanism-class × innate-immune-axis table is genuinely integrative, draws on the strongest anchor papers, and surfaces the Gross 2024 TLR9 finding as a coherent organising mechanism that ties SQ1 and SQ2 together. The mode-of-killing axis row in particular is the most useful single take-away.
- **SQ4** also came out strong: the macrolide-respiratory evidence base, polymyxin B haemoperfusion subgroup story, and clindamycin-TSS adjunct story are all clearly graded by evidence strength, and the informative-negative entries (Wei 2025 EHR; Simpson 2014) prevent overreach.

**Weakest sub-questions:**
- **SQ1** is the weakest. The pathway table is correct but somewhat textbook — the working-clinician-reference framing in the scope constraint pushed toward broad reviews rather than the bleeding-edge work, so the table reads like a polished canonical map rather than a digest. The R. equi cGAS-STING, NLRP11 cytosolic LPS, and MyD88 trained immunity entries add some novelty. The TLR9 row gains depth from being directly cited to PMC11605096 rather than to a generic PRR review.
- **SQ2** is weaker in citation depth than the others: rifamycin, folate-pathway, isoniazid, and pleuromutilin rows rely heavily on a single multi-class review (Kapoor 2017 / PMC5672523), without dedicated class-specific citations. A clinician using this should know that the SQ2 table is correct but thin in primary support for those classes.

**Other notes:**
- The digest stays disciplined about distinguishing in vitro from animal from human evidence in SQ3 and SQ4 — that distinction matters and was kept consistent.
- Bibliography (~45 entries) and verification anchors (15) provide a reasonable surface area for downstream use without bloat.
- The Paperclip v0.3.0 limitations (no `reduce`, no repo commands, no `export bib`) were worked around as the prompt specified; all keeper papers are recorded inline in each SQ's "Search and filter notes" and the bibliography section was generated manually.
- The bioRxiv slab service was unavailable for two specific preprint papers (bio_e15726726c18, bio_558b70756bfd) during verification-anchor extraction — those papers are cited but do not have line-level verification anchors. Not a digest-quality blocker.

## Files produced

- `abx_test_v2_filled.md` — the filled digest
- `abx_test_scaffold.md` — preserved unchanged as template
- `_anchor_candidates.md` — Phase 0 output
- `_progress.md` — timestamped step log
- `_run_report.md` — this report
- `_scoping_results.csv`, `_scoping_raw.txt`, `_sq2_map.txt`, `_sq3_map.txt` — intermediate paperclip outputs (kept for reproducibility)
