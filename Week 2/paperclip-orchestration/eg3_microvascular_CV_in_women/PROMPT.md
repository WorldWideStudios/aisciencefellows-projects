# Claude Code Prompt: cv_microvascular Research Digest

## CRITICAL: Filesystem sandbox

**This run is operating with `--dangerously-skip-permissions`. You will not be prompted to confirm any action. Strict filesystem discipline is required.**

**Working directory:** `~/paperclip-test/cv_microvascular/`

**You may read from:**
- `~/paperclip-test/cv_microvascular/` (working directory — read and write)
- `~/paperclip-test/Paperclip_documentation` (read-only reference)
- The Paperclip virtual filesystem at `/papers/` (read-only, via Paperclip commands)

**You may write to:**
- `~/paperclip-test/cv_microvascular/` only

**You may NOT, under any circumstances:**
- Read, write, modify, or delete any file outside `~/paperclip-test/cv_microvascular/` except the Paperclip documentation file
- Run `rm`, `mv`, or any destructive operation outside the working directory
- Modify files in `~/paperclip-test/` at the directory root or in any sibling directory
- Modify or delete the scaffold file (`cv_microvascular_research_digest_scaffold.md`) — treat it as a read-only template
- Use `cd` to navigate outside the working directory for any reason other than reading the Paperclip documentation file
- Install software, modify environment, change shell configuration
- Make any network call other than Paperclip tool invocations

**If any step would require violating these rules, do not improvise. Log the conflict in `_progress.md`, skip the step, and continue with the rest of the workflow.**

## Goal

Fill out the research digest scaffold at `~/paperclip-test/cv_microvascular/cv_microvascular_research_digest_scaffold.md` for a clinician-facing Era brief on microvascular disease as the predominant axis of female cardiovascular pathology, with attention to detection modalities, the perimenopause-to-menopause transition and hormone therapy positioning, risk-enriched subpopulations, and intervention evidence.

The overarching question, sub-questions, scope constraints, and table structures are defined in the scaffold. Do not redefine them.

**Save the filled version as `cv_microvascular_filled.md` in the working directory. Preserve the original scaffold as a template.**

Run end-to-end. Do not pause for input.

## Reference materials

- **Scaffold to fill in:** `~/paperclip-test/cv_microvascular/cv_microvascular_research_digest_scaffold.md`
- **Paperclip documentation (read-only reference):** `~/paperclip-test/Paperclip_documentation`

## Known limitations in Paperclip v0.3.0

**Working:** `search`, `searches` (with `--tag`), `filter` (with `--require`), `map` (with `--output_schema`), `lookup`, `cat`, `grep`, `sql`, SQL `export`.

**Not in v0.3.0:**
- `reduce` (all strategies return "command not found")
- Paper repo commands: `init`, `checkout`, `add`, `remove`, `import`, `annotate`, `commit`, `log`, `diff`, `branch`, `merge`
- `export bib` / `export ris` / `export md`

**Known flakiness:** `map` has returned 500 Internal Server Errors. Retry up to twice with a small delay. If a third attempt fails, fall back to manual extraction from `paperclip cat /papers/<id>/content.lines` plus `grep`.

**Workarounds:**
- **No `reduce`:** assemble tables manually from `map --output_schema` JSON output.
- **No repo commands:** record keeper papers inline in each sub-question's "Search and filter notes" subsection as `paper_id | one-line relevance note`.
- **No `annotate`:** record verification anchors inline using the format `paper_id : L<line> : <quoted phrase>`. Use `paperclip cat -n` and `grep` to locate.
- **No `export bib`:** generate bibliography manually via `paperclip lookup`.

## State tracking

- **Maintain a progress log** at `~/paperclip-test/cv_microvascular/_progress.md`. Update at the start of each major step. Format: `[HH:MM] <phase>: <status>`.
- **Refer back to PROMPT.md as the source of truth** for what to do next. Do not improvise the workflow from memory.
- **Checkpoint after each completed sub-question.** Save the partial filled scaffold to `cv_microvascular_filled.md` after each sub-question completes. Do not wait until the end.

## Stop conditions

Halt and write final status to `_progress.md` and `_run_report.md` if:

- More than 5 consecutive `paperclip map` calls fail with 500 errors
- A sub-question returns zero filtered papers and no recovery search produces any either
- Workflow exceeds 180 minutes wall-clock from start
- Any filesystem sandbox violation is encountered

---

## PHASE 0: Scoping pass

Before starting per-sub-question work, run a scoping pass on the overarching question to identify candidate **anchor papers** — the papers a competent expert would expect this digest to engage with regardless of how the sub-questions are framed.

**Steps:**

1. **Broad scoping searches.** Run 3-4 broad parallel searches on the overarching question — not the sub-questions, the *overall question*. Example query directions (use your own phrasing):
   - "coronary microvascular dysfunction women sex differences review"
   - "INOCA MINOCA female cardiovascular disease pathophysiology"
   - "microvascular angina women autonomic estrogen mechanism"
   - "ischemia non-obstructive coronary arteries women screening"

2. **Identify anchor candidates** from the scoping results using multiple signals:
   - **Most-cited recent reviews** in the topic area (last 5 years preferred)
   - **Papers by authors who appear repeatedly across the result set**
   - **Papers whose Paperclip auto-summary directly addresses the overarching question** rather than a narrow slice of it
   - **Papers that span multiple sub-questions** — these are exactly the integrative papers most likely to be missed by sub-question-specific filters

3. **Reviewer-targeted secondary searches.** Once you have 2-3 names of authors who appear repeatedly, run a second pass:
   - `paperclip lookup author "<name>"` for each candidate canonical reviewer
   - Note their most-cited and most-recent papers in the topic area

4. **Write `_anchor_candidates.md`** to the working directory. Format:
   ```
   # Anchor candidates for cv_microvascular
   
   Generated: [timestamp]
   Method: scoping pass + reviewer-targeted search
   
   ## Anchor papers (must be addressed in digest or excluded with justification)
   
   - paper_id | author year | one-line characterization | which SQ(s) it should appear in
   - paper_id | author year | ...
   
   ## Canonical reviewers identified
   
   - Author name | most-cited paper in topic area | other relevant work
   
   ## Method notes
   
   - Searches run, result IDs, signals that drove inclusion
   ```

**Anchor candidate rules:**
- Aim for 5-10 anchor candidates. Fewer is fine if the topic is narrow.
- A candidate enters the list if it meets at least two of the four signals above.
- Do not include a paper solely because it appears in many search results — citation count and topical breadth must combine.

---

## PHASE 1: Per-sub-question workflow

For each sub-question, run the following loop. Reference the anchor candidates list throughout.

**1. Design and run parallel searches.** Draft 4-8 natural-language queries tailored to the sub-question. Run via `paperclip searches --tag <subq_tag>`.

**2. Filter for relevance.** Apply filter discipline rules (see below). Aim for 5-12 papers per sub-question.

**3. Extract structured data.** Use `paperclip map --output_schema` matched to the scaffold's table columns. Retry once on 500 errors; fall back to manual extraction via `cat` + `grep` if persistent.

**4. Populate the table** manually from map output. DOI/PMID required for every row.

**5. Record keeper papers** inline in the "Search and filter notes" subsection.

**6. Write paragraph answer, synthesis bullets, confidence read.**

**7. Checkpoint:** save updated `cv_microvascular_filled.md` to disk before moving to the next sub-question.

### Filter discipline rules

**Rule A: Filter query language must mirror the sub-question's scoping language, not narrow it further.**
- For SQ2, the scope explicitly includes both the named candidate modalities (retinal vascular imaging, HRV, coronary flow reserve, CTA vs. CAC) AND modalities outside this list. The filter must allow both. Do not introduce constraining vocabulary like "established screening tool" or restrict to the named modalities — the unknown-unknowns space is part of the intended scope.

**Rule B: Use fresh tags for each filter pass.** Do not overwrite the candidate pool in place.

**Rule C: If `--require N` is not met after filter, inspect what got cut before retrying.**
- Run `paperclip cat` or check the filter output to see which papers were dropped
- Look especially for papers whose auto-summary indicates on-topic content but unconventional framing
- If a dropped paper appears to be on-topic by its auto-summary, broaden the filter language before retrying

**Rule D: For each sub-question, check the keeper set against the anchor candidates list before moving to step 3 (map).**
- If an anchor candidate that should appear in this sub-question is NOT in the keeper set, attempt one targeted recovery search
- If the recovery search doesn't surface it either, note this in the sub-question's "Excluded and why" field with a brief justification

---

## PHASE 2: Post-sub-question work

**10. Anchor reconciliation.** For each anchor candidate from Phase 0, check whether it appears in the final keeper set. Either confirm its inclusion or justify exclusion. **Write a "Missing anchors" section to `_run_report.md`** listing any anchor candidates that did not appear in the final digest, with justification for each.

**11. Identify load-bearing claims and add verification anchors.** Review the full assembled digest. Identify 8-15 claims most likely to matter in downstream use. Record as `paper_id : L<line> : <quoted phrase>` in the scaffold's Verification Anchors section.

**12. Generate bibliography manually** via `paperclip lookup`. Alphabetical by first author.

**13. Cross-cutting observations.** Add anything that emerged across sub-questions, conflicts, notable absences.

**14. Final report.** Write to `~/paperclip-test/cv_microvascular/_run_report.md`:
- Wall-clock time and total papers cited
- Anchor candidates identified in Phase 0 and how many made it into the final digest, with missing anchors list
- Sub-questions where evidence was thin or map fallback was used
- Any filter retries triggered by Rule C
- Three to five unexpected findings worth attention on return
- Honest self-assessment of which sub-questions came out best and which are weakest

## Constraints (in addition to sandbox)

- **Distinguish direct evidence from extrapolated.** Especially for SQ2 (diagnostic modalities) — modality validation studies in mixed-sex populations, in men, or in symptomatic INOCA/MINOCA cohorts are not the same as validation for asymptomatic detection in women. Where extrapolation is being applied, name it.
- **Distinguish human from animal-model evidence.** Especially for SQ1 (mechanism) — rodent models of estrogen-autonomic-microvascular signaling are well-developed but human inference is largely indirect (functional testing, imaging, post-hoc cohort analysis). Surface the distinction in the table and synthesis.
- **SQ1 has a scope ceiling.** Working reference, not textbook. If the mechanism section grows past ~600 words, cut. Focus on the hormonal–autonomic–microvascular axis specifically; broader CV physiology is out of scope.
- **SQ3, SQ4, and SQ5 must reference prior sub-questions' outputs.** The mechanistic framing from SQ1 and the modality landscape from SQ2 are the organizing structure for downstream sub-questions. Do not search these sub-questions' literature in a vacuum.
- **Microvascular versus macrovascular endpoint distinction.** Throughout, name whether a study's outcome is a microvascular-specific endpoint (coronary flow reserve, index of microcirculatory resistance, retinal vascular caliber, etc.) or a composite MACE/macrovascular endpoint. The brief depends on this distinction for the screening and HT-positioning questions.
- **Thin evidence is signal, not a search failure.** Especially likely for SQ5 (intervention evidence for detected microvascular dysfunction) — do not pad with general cardiovascular intervention literature treated as if it were direct evidence.
- **DOI or PMID required for every row** in every table.
- **Do not draft a brief or review article.** Structured findings only.

## Deliverables

- `~/paperclip-test/cv_microvascular/cv_microvascular_filled.md` — filled-in digest
- `~/paperclip-test/cv_microvascular/cv_microvascular_research_digest_scaffold.md` — preserved as template
- `~/paperclip-test/cv_microvascular/_anchor_candidates.md` — Phase 0 output
- `~/paperclip-test/cv_microvascular/_progress.md` — timestamped step log
- `~/paperclip-test/cv_microvascular/_run_report.md` — final summary report, including missing anchors section

## Pause points

**None.** Run end-to-end.
