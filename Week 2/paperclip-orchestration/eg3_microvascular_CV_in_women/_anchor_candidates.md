# Anchor candidates for cv_microvascular

Generated: 2026-05-18 16:08
Method: scoping pass (4 broad parallel searches, 49 unique papers in s_2bfefbfe) + reviewer-targeted lookups (Bairey Merz, Janet Wei, Pepine). Candidates entered the list if they met ≥2 of the four signals (recent review, repeated author appearance, auto-summary directly addresses overarching question, spans multiple SQs).

## Anchor papers (must be addressed in digest or excluded with justification)

- PMC12429603 | Agarwal et al. 2025 | Review: CMD in women with INOCA — bridging diagnosis-treatment divide; spans mechanism, diagnostics, intervention | SQ1, SQ2, SQ5
- PMC12162733 | O'Hara, Roy, Patel et al. 2025 | Review: disproportionate burden of microvascular disease in women, with pregnancy complications as early markers | SQ1, SQ4
- PMC7010630 | Groepenhoff, Bots, Kessler et al. 2019 | Review: sex-specific aspects of coronary macro- and microvascular disease pathophysiology and imaging | SQ1, SQ2
- PMC10412671 | Marano, Wei, Bairey Merz 2023 | Canonical review: CMD — what clinicians and investigators should know (WISE program lineage) | SQ1, SQ2, SQ5
- PMC12078779 | Scarica, Rinaldi, Animati, Manzato, Montone 2025 | Recent comprehensive CMD pathophysiology/diagnosis/therapeutics review | SQ1, SQ5
- PMC4351318 | Park, Park, Choi 2015 | Microvascular angina: angina that predominantly affects women — foundational positioning | SQ1
- PMC7307673 | Patel, Aggarwal, Rao et al. 2020 | Microvascular disease as nexus across multiple women's diseases — integrative framing | SQ1, SQ4
- PMC11760542 | Gurgoglione, Benatti, Denegri et al. 2025 | CMD: prognosis and future perspectives | SQ1, SQ5
- PMC12386650 | Gurgoglione, Benatti, Denegri et al. 2025 | INOCA: sex-based differences in pathophysiology, presentation, prognosis | SQ1
- PMC8551605 | Jansen, Elias-Smale, van den Oord et al. 2021 | Sex differences in coronary function test results — direct empirical data on female-pattern CMD | SQ1, SQ2
- PMC11847120 | Shiromani, AlBadri, Lindeke-Myers et al. 2025 | Retinal microvascular density in women with CMD — direct evidence for retinal-coronary microvascular linkage | SQ2
- med_161506e17846 | Honigberg, Economy, Pabón et al. 2024 | Coronary microvascular function following severe preeclampsia (PET, postpartum) — adverse reproductive history → CMD | SQ4
- med_a8c53de070a1 | Borle, Liu, Kote et al. 2024 | Sympathetic nerve activity and ischemia in Takotsubo + stable ischemic heart disease — autonomic axis | SQ1
- bio_3f53d9987514 | Huo, Montano, Tumurkhuu et al. 2024 | Cytosolic RNA sensing gene alterations linked to coronary microvascular disease in SLE — autoimmune→CMD | SQ4

## Canonical reviewers identified

- **C. Noel Bairey Merz** (Cedars-Sinai, WISE / WISE-CVD program lead) — most prolific voice on female CMD/INOCA. Appears in PMC10412671 (Marano 2023) and ties to the WISE longitudinal cohort literature surfaced in scoping searches.
- **Janet Wei** (Cedars-Sinai, WISE collaborator) — appears in Marano/Wei/Bairey Merz 2023 (PMC10412671); SLE-CMD work (bio_3f53d9987514).
- **Rocco Montone / Vincenzo Scarica** (Catholic University Rome) — recent CMD reviews including PMC12078779.
- **Filippo Luca Gurgoglione** (Parma) — multiple sex-difference and CMD prognosis reviews (PMC12386650, PMC11760542).
- **Carl J. Pepine** (University of Florida, WISE founding investigator) — WISE legacy author; surfaced in scoping but full-text catalog hits noisy in this corpus.
- **Hena Patel / Meaghan O'Hara** (Rush) — author cluster behind PMC12162733 and PMC7307673 (microvascular disease as integrative female pathology).

## Method notes

- Broad searches: 4 queries on overarching question dimensions. Accumulated to s_2bfefbfe (49 unique papers).
- Saved per-query result text to `_scope_s{1,2,3,4}.txt` for traceability.
- Two-pass reviewer lookups via `paperclip lookup author "..."` for Bairey Merz, Wei, Pepine. Author lookup tends to surface tangential coauthorships, so anchor inclusion was driven primarily by topical alignment in the broad search results, with reviewer lookups confirming author centrality.
- Coverage gaps to watch in Phase 1: (a) USPSTF/AHA/ACOG/NAMS guideline documents on HT may not appear via standard scientific search ranking and will require targeted searches in SQ3; (b) intervention RCTs for CMD (e.g., WARRIOR trial, CorMicA, Zibotentan) need named-trial queries in SQ5.
