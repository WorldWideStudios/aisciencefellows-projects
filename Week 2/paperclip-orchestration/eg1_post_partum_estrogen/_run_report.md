# pp_estrogen_v2 — Run Report

**Run window:** 2026-05-16 18:30 → 20:20 local (≈110 min wall-clock; well within 180-min stop condition)
**Deliverables produced:**
- `pp_estrogen_v2_filled.md` (digest)
- `pp_estrogen_research_digest_scaffold.md` (preserved unchanged)
- `_anchor_candidates.md` (Phase 0 output)
- `_progress.md` (timestamped step log)
- `_run_report.md` (this file)

## Totals

- **Sub-questions answered:** 5 of 5
- **Papers cited in the final digest:** 35 unique (counting Gregoire 1996 and Bloch 2000 as bibliography entries even though they are captured second-hand)
- **Anchor candidates identified in Phase 0:** 11
- **Anchor candidates that appear in the final digest:** 10 of 11
- **Filter retries triggered by v2 Rule C (broaden the filter, do not just lower --require):** 3 — SQ1 (initial filter dropped all 15 evaluated; retried with broader query and recovered 9), SQ3 (initial filter dropped to 0 after cache saturation; ran fresh tag), SQ4 (cache saturation across initial+secondary tag, ran fresh tag with broader filter).

## Missing anchors

| Anchor | Where it should have appeared | Why excluded |
|---|---|---|
| PMC7231991 (Meltzer-Brody & Kanes 2020, *Allopregnanolone in PPD: role in pathophysiology and treatment*) | SQ4 (neurosteroid SoC context) | Subsumed by Patterson/Balan/Morrow/Meltzer-Brody 2023 (PMC10700474), Walton & Maguire 2019 (PMC6838978) — same mechanism story, more recent and more clinically oriented. Including PMC7231991 separately would have duplicated content without adding evidence. Justified exclusion. |

All other 10 anchor candidates are cited in the final digest:

- PMC8719185 (Høgh 2021 MAMA) — SQ1, SQ2, SQ5
- PMC11882533 (Mu/Chiu/Kulkarni 2025) — SQ1, SQ2
- PMC6296393 (Rubinow & Schmidt 2018) — SQ1, SQ2
- PMC3181677 (Freeman 2002) — SQ1, SQ2
- PMC3181972 (Meltzer-Brody 2011) — SQ1
- PMC8801644 (Kaufman/Carlini/Deligiannidis 2022) — SQ4
- PMC12197409 (Wilson 2025 Cochrane) — SQ4
- PMC10831895 (Jin 2023) — SQ3
- PMC11121006 (Eleftheriou 2024) — SQ4, SQ5
- PMC12550661 (Nakić Radoš 2025) — SQ5

## Sub-questions where evidence was thin

- **SQ2 (dose/timing/duration).** Only one regimen — 200 µg/day transdermal — has been tested in human postpartum mood (Gregoire 1996 for 6 months treatment; Høgh/MAMA 2021 for 3 weeks prevention). No dose-response, no oral-vs-transdermal head-to-head, no formal taper. The thinness is the answer, not a search failure.
- **SQ3 (lactation safety).** No direct quantitative milk-transfer study of transdermal 17β-estradiol in the Paperclip corpus. Closest is Segev 2025 for ethinylestradiol on CHC (n=14, LOQ 3.5 ng/mL, undetectable). The team's working assumption is biologically plausible but not directly evidenced.
- **SQ4 / prevention slot.** No pharmacologic agent has Cochrane-level evidence for *prevention* of PPD; the slot transdermal E2 would compete for is essentially empty.

## Where map fallback was used

- **SQ4 and parts of SQ5.** Multiple `paperclip map` calls against filtered result IDs returned cross-contaminated paper sets (e.g., antibiotics-for-pneumonia papers showed up when mapping a filtered PPD set). This appeared to be a Paperclip v0.3.0 cache/result-ID issue rather than a query issue. I fell back to direct `paperclip cat /papers/<PMC>/meta.json` and `paperclip grep /papers/<PMC>/content.lines` on each known-anchor PMC ID to extract abstracts and line-anchored quotes, and used the abstracts where slab access was unavailable (medRxiv preprints have a slab-grep limitation in this version). This is noted in the verification-anchors block where applicable.

## Filter retries (Rule C)

- **SQ1**: initial filter query was a long multi-clause sentence ("transdermal estradiol or estrogen-class therapy for prevention or treatment of postpartum (perinatal/postnatal) depression or anxiety, including mechanistic studies of estrogen withdrawal in postpartum mood, in human or human-relevant models"). Dropped all 15 evaluated. **Retry with broader query** ("estrogen or estradiol for postpartum or perinatal mood") under fresh tag `sq1b` recovered 9 keepers including Høgh 2021 MAMA, Freeman 2002, Duan 2025, Foster 2022, Zorzini 2025, Li 2019, plus mechanism papers.
- **SQ3**: initial cached filter on s_10a0cc18 dropped to 0 new. Retried under fresh tag `sq3b` with broader query — recovered 2 papers. Direct lookups of known anchors (Segev, Jin, Borgert, Bernbaum) under `sq3c` brought in the rest.
- **SQ4**: cache-saturated initial filter on s_796b8111 returned 0 new. Fresh tag `sq4b` plus broader filter recovered 8 papers; anchor-recovery `sq4c` added 4 more.

## Three to five unexpected findings worth attention on return

1. **Larsen 2024 contradicts the naive "more estrogen → better mood" framing.** Postpartum *combined hormonal contraceptive* initiation is associated with a 49% increased depression risk, with the association stronger the earlier in postpartum it begins. Reconcilable with the transdermal-E2 prevention hypothesis only by stipulating that the relevant variable is *attenuation of physiologic withdrawal in the immediate postpartum*, not steady-state exposure later. This is the strongest single signal worth probing further on return.
2. **Real-world transdermal-E2 patches produce highly variable serum E2** (Glynne 2025: ~25% subtherapeutic at the highest licensed dose). Any clinical use of the MAMA-style 200 µg/d patch would need a plan for the substantial fraction of patients in whom the patch under-delivers — likely serum E2 monitoring, which is not part of MAMA.
3. **The most recent comprehensive guideline (Nakić Radoš 2025, BJP, GRADE/AGREE-II, 44 recommendations from 145 systematic reviews) does not include estrogen-class therapy at all.** Grep of the full text returned no matches for "estrogen" or "estradiol." This is not silence by oversight; it is an active no-recommendation. Any clinical use today is off-guideline.
4. **The Clapp 2024 PPD-at-discharge risk-stratification model** (AUC 0.721, NPV 92%) is well-suited to identify a prevention-pathway candidate pool — meaning the technical infrastructure exists to deliver a prevention intervention to the right people; what is missing is the agent. If MAMA reads out positive, the operational pipeline is already there.
5. **Mechanistic convergence is strikingly tight** across rodent estrogen-withdrawal models — Foster 2022 (NAc-core ΔFosB), Duan 2025 (LHb ER-β), Foster lab 2020 (PVH/DRN OT) — all describe distinct neural pathways activated by the same postpartum-pattern hormone drop. The translatability gap to humans remains real, but the cross-model agreement is unusual and worth flagging.

## Honest self-assessment

- **Strongest sub-questions:**
  - **SQ4** (positioning vs SoC) — well-evidenced by multiple Cochrane and consensus papers; the conclusion (SSRI-first for treatment, empty prevention slot) is robust.
  - **SQ5** (protocol) — well-grounded in the Nakić Radoš + Durrani + Eleftheriou + Clapp papers; the synthesis (off-guideline prevention-only with risk-stratification overlay) is defensible.
- **Weakest sub-questions:**
  - **SQ3** (lactation safety) — the central question (does transdermal E2 transfer into milk and affect supply?) has no direct in-corpus answer. The brief leans on Segev 2025 (EE not E2; small N), Jin 2023 (mechanism + animal data + single human correlational study), and the absence of a direct study. This is the largest evidence gap and the clearest place where the brief should hedge.
  - **SQ2** (dose/timing/duration) — only the single 200 µg/d patch regimen has been tested. Anything the brief says about alternative doses is extrapolation from non-postpartum HRT pharmacokinetics.
- **Cross-cutting weakness:** Gregoire 1996 is the central piece of human treatment evidence and is captured only second-hand through two reviews. Some of the precise design parameters (exact N, EPDS/HAM-D outcome magnitudes, breastfeeding subgroup analysis) cannot be verified from the Paperclip corpus alone — the Lancet PDF would need to be retrieved through another channel before clinical roll-out of any protocol.

## Workflow execution notes

- **Paperclip v0.3.0 limitations encountered:**
  - `reduce` not available — handled by manual table assembly from `map --output_schema` JSON outputs.
  - `add`/`commit`/repo commands not available — keepers tracked inline in each SQ's "Search and filter notes" section per the v2 fallback in the prompt.
  - `annotate` not available — verification anchors written manually using `paperclip cat -n` and `paperclip grep -n` outputs.
  - `export bib` not available — bibliography assembled manually from `paperclip lookup` results.
  - **Map cross-contamination on filtered result IDs** — multiple map runs on freshly-filtered sets returned papers from unrelated topics (antibiotic / pneumonia papers appearing in a PPD-filtered set). Worked around by fetching anchor PMC IDs directly via `lookup` and `cat`. This was not anticipated by the prompt's "known flakiness" note (which only mentioned 500 errors); reporting here for v2 prompt update consideration.
  - **medRxiv slab unavailability for grep / cat on `content.lines`** of some preprints (Larsen 2024, Clapp 2024). Falls back to abstract from `meta.json`.
- **None of the configured stop conditions were hit.** No >5 consecutive 500 errors; no zero-keeper sub-question without recovery; well under 180-minute budget; no sandbox violations.
