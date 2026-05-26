# Anchor candidates for pp_estrogen_v2

Generated: 2026-05-16 18:40 local
Method: scoping pass (4 broad parallel searches on overarching question) + reviewer-targeted second pass; signals weighted = topical breadth × recency × repeat authorship × Paperclip auto-summary engagement with overarching question rather than a narrow slice.

## Anchor papers (must be addressed in digest or excluded with justification)

- PMC8719185 | Høgh et al. 2021 (BMJ Open) | MAMA trial PROTOCOL: short-term transdermal estradiol for PPD prevention in high-risk women — the *only* directly-on-target trial in the corpus | SQ1, SQ2, SQ5
- PMC11882533 | Mu, Chiu, Kulkarni 2025 (Front Pharmacol) | Review of estrogen + progesterone for PMDD, postnatal depression, menopausal depression — Kulkarni group, integrative across SQs | SQ1, SQ4
- PMC6296393 | Rubinow & Schmidt 2018 | Reproductive steroids in affective disorders — canonical mechanistic framework for hormone-withdrawal model of PPD | SQ1
- PMC3181677 | Freeman 2002 | Depression of the menstrual cycle, PPD, and perimenopause — older but the most-cited integrative treatment review covering all three hormone-sensitive depressions | SQ1, SQ4
- PMC3181972 | Meltzer-Brody 2011 | Perinatal depression: pathogenesis and treatment during pregnancy and postpartum — canonical reviewer | SQ1, SQ4
- PMC8801644 | Kaufman, Carlini, Deligiannidis 2022 | Structured review of standard-of-care antidepressants and novel neuroactive steroids for PPD — anchor for SQ4 positioning | SQ4
- PMC12197409 | Wilson et al. 2025 (Cochrane) | Brexanolone, zuranolone, and related neurosteroid GABA-A PAMs for postnatal depression — most recent systematic review of the rapid-acting SoC comparator | SQ4
- PMC10831895 | Jin, Perrella, Lai, Taylor, Geddes 2023 | Causes of low milk supply: roles of estrogens, progesterone, external factors — the central mechanistic review on the milk-supply concern | SQ3
- PMC11121006 | Eleftheriou et al. 2024 | Consensus panel recommendations for pharmacological management of breastfeeding women with PPD — clinical-guideline anchor | SQ4, SQ5
- PMC12550661 | Nakić Radoš et al. 2025 | Evidence-based clinical practice guidelines for prevention, screening, treatment of peripartum depression — the most recent comprehensive guideline | SQ5
- PMC7231991 | Meltzer-Brody & Kanes 2020 | Allopregnanolone in PPD: pathophysiology and treatment — central mechanism review tying estrogen withdrawal to allopregnanolone dynamics | SQ1, SQ4

## Canonical reviewers identified

- Samantha Meltzer-Brody (UNC) — most-cited postpartum-depression reviewer in the corpus. Relevant: PMC3181972 (2011 perinatal review), PMC10700474 (2023 neurosteroids), PMC7231991 (2020 allopregnanolone) [[anchor-meltzer-brody]]
- Jayashri Kulkarni (Monash) — hormonal therapy / women's mood. Relevant: PMC11882533 (2025 estrogen/progesterone review), PMC9355926 (2022 hormonal agents for menopausal depression)
- Kristina M. Deligiannidis — PPD pharmacotherapy. Relevant: PMC8801644 (2022 structured review)
- Graziano Pinna — allopregnanolone mechanism. Relevant: PMC9088875 (2022 allopregnanolone in PPD), PMC7231972 (2020 historical perspective)

## Known absences (informs the digest)

- **Gregoire 1996 (Lancet)** — the original RCT of transdermal estradiol for postnatal depression is **not** in the Paperclip corpus (search and `lookup author "Gregoire"` returned nothing matching). Will be cited only if a secondary source carries the data; otherwise the brief must lean on the MAMA-protocol paper as the canonical RCT artifact in-corpus.
- **Ahokas et al. sublingual estradiol PPD case series** — also not surfaced. Same handling.

## Method notes

- Initial parallel scoping search ID: s_de38b264 (tag scoping_anchors2) and s_d7761ce1 (tag scoping_anchors). 4 queries × ~30 results merged to 29 unique papers.
- Topic-specific follow-ups:
  - SQ1 / overarching: s_1038e820 ("transdermal estradiol postpartum depression"), s_e28e0a0b ("estrogen postpartum depression prevention high-risk"), s_585387c2 ("Gregoire transdermal estradiol postnatal depression severe")
  - SQ3 (lactation): s_78795de9 ("estradiol breast milk transfer lactation infant exposure")
  - SQ4 (SoC): s_8371e182 ("sertraline postpartum depression breastfeeding lactation"), s_2150282b ("brexanolone zuranolone postpartum depression")
  - Mechanism: s_282c4fe8 ("Bloch sex steroids postpartum depression gonadal hormone withdrawal"), s_7829ab9b ("estradiol postpartum mood mechanism allopregnanolone estrogen withdrawal")
  - SQ5 (guidelines): s_f73bb7b1 ("postpartum depression prevention clinical guideline")
- Reviewer-targeted lookup `paperclip lookup author "Kulkarni"` returned too many unrelated matches (40+) — Kulkarni anchor papers were already captured via topical search, so author-lookup did not add candidates.
- All candidates above meet ≥2 of: most-cited recent reviews; repeat authorship; auto-summary engages overarching question; spans multiple SQs.
