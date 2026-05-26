# Claude Code Prompt: abx_test_v2 Research Digest

## CRITICAL: Filesystem sandbox

**This run is operating with `--dangerously-skip-permissions`. You will not be prompted to confirm any action. Strict filesystem discipline is required.**

**Working directory:** `~/paperclip-test/abx_test_v2/`

**You may read from:**
- `~/paperclip-test/abx_test_v2/` (working directory — read and write)
- `~/paperclip-test/Paperclip_documentation` (read-only reference)
- The Paperclip virtual filesystem at `/papers/` (read-only, via Paperclip commands)

**You may write to:**
- `~/paperclip-test/abx_test_v2/` only

**You may NOT, under any circumstances:**
- Read, write, modify, or delete any file outside `~/paperclip-test/abx_test_v2/` except the Paperclip documentation file
- Run `rm`, `mv`, or any destructive operation outside the working directory
- Modify files in `~/paperclip-test/` at the directory root or in any sibling directory (`abx_test`, `heart_health`, `pp_estrogen`, etc.)
- Modify or delete the scaffold file (`abx_test_scaffold.md`) — treat it as a read-only template
- Use `cd` to navigate outside the working directory for any reason other than reading the Paperclip documentation file
- Install software, modify environment, change shell configuration
- Make any network call other than Paperclip tool invocations

**If any step would require violating these rules, do not improvise. Log the conflict in `_progress.md`, skip the step, and continue with the rest of the workflow.**

## Goal

Fill out the research digest scaffold at `~/paperclip-test/abx_test_v2/abx_test_scaffold.md` for a working clinician-scientist reference on macrophage signaling, antibiotic mechanism of action, and immune-modulatory effects in bacterial infection.

The overarching question, four sub-questions, scope constraints, and table structures are defined in the scaffold. Do not redefine them.

**Save the filled version as `abx_test_v2_filled.md` in the working directory. Preserve the original scaffold as a template.**

Run end-to-end. Do not pause for input.

## Reference materials

- **Scaffold to fill in:** `~/paperclip-test/abx_test_v2/abx_test_scaffold.md`
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

- **Maintain a progress log** at `~/paperclip-test/abx_test_v2/_progress.md`. Update at the start of each major step. Format: `[HH:MM] <phase>: <status>`.
- **Refer back to PROMPT.md as the source of truth** for what to do next. Do not improvise the workflow from memory.
- **Checkpoint after each completed sub-question.** Save the partial filled scaffold to `abx_test_v2_filled.md` after SQ1 completes, after SQ2 completes, etc. Do not wait until the end.

## Stop conditions

Halt and write final status to `_progress.md` and `_run_report.md` if:

- More than 5 consecutive `paperclip map` calls fail with 500 errors
- A sub-question returns zero filtered papers and no recovery search produces any either
- Workflow exceeds 180 minutes wall-clock from start
- Any filesystem sandbox violation is encountered

---

## PHASE 0: Scoping pass (NEW in v2)

Before starting per-sub-question work, run a scoping pass on the overarching question to identify candidate **anchor papers** — the papers a competent expert would expect this digest to engage with regardless of how the sub-questions are framed.

**Steps:**

1. **Broad scoping searches.** Run 3-4 broad parallel searches on the overarching question — not the sub-questions, the *overall question* of macrophage-antibiotic-immune-interaction. Example query directions (use your own phrasing):
   - "macrophage innate immune response to bacterial infection antibiotic treatment"
   - "antibiotic class effect on host immune response review"
   - "bactericidal bacteriostatic antibiotic immunomodulation"
   - "pattern recognition receptor antibiotic-induced bacterial PAMP release"

2. **Identify anchor candidates** from the scoping results using multiple signals:
   - **Most-cited recent reviews** in the topic area (last 5 years preferred; use `paperclip sql` to query by recency/source if helpful)
   - **Papers by authors who appear repeatedly across the result set** (likely canonical reviewers in the subfield)
   - **Papers whose Paperclip auto-summary directly addresses the overarching question** rather than a narrow slice of it
   - **Papers that span multiple sub-questions** (e.g., engage both mechanism class AND immune response) — these are exactly the integrative papers most likely to be missed by sub-question-specific filters

3. **Reviewer-targeted secondary searches.** Once you have 2-3 names of authors who appear repeatedly, run a second pass of searches targeting their work specifically:
   - `paperclip lookup author "<name>"` for each candidate canonical reviewer
   - Note their most-cited and most-recent papers in the topic area

4. **Write `_anchor_candidates.md`** to the working directory. Format:
   ```
   # Anchor candidates for abx_test_v2
   
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
- Aim for 5-10 anchor candidates. Fewer is fine if the topic is narrow; more than 15 is over-inclusive.
- A candidate enters the list if it meets at least two of the four signals above.
- Do not include a paper as an anchor candidate solely because it appears in many search results — citation count and topical breadth need to combine.

---

## PHASE 1: Per-sub-question workflow

For each sub-question, run the following loop. Reference the anchor candidates list throughout.

**1. Design and run parallel searches.** Draft 4-8 natural-language queries tailored to the sub-question. Run via `paperclip searches --tag <subq_tag>`. For SQ3 and SQ4, use prior sub-questions' outputs to scope queries.

**2. Filter for relevance.** Apply filter discipline rules (see below). Aim for 5-12 papers per sub-question.

**3. Extract structured data.** Use `paperclip map --output_schema` matched to the scaffold's table columns. Retry once on 500 errors; fall back to manual extraction via `cat` + `grep` if persistent.

**4. Populate the table** manually from map output. DOI/PMID required for every row.

**5. Record keeper papers** inline in the "Search and filter notes" subsection.

**6. Write paragraph answer, synthesis bullets, confidence read.**

**7. Checkpoint:** save updated `abx_test_v2_filled.md` to disk before moving to the next sub-question.

### Filter discipline rules (NEW in v2)

**Rule A: Filter query language must mirror the sub-question's scoping language, not narrow it further.** Do not introduce new constraining vocabulary in the filter query that wasn't in the scope constraint. Specifically:
- If the sub-question scope includes both general and specific framings (e.g., "antibiotic class effect" AND "mechanism-class-spanning effects"), the filter must allow both.
- Avoid phrases like "class-specific" or "drug-specific" in filter queries unless the sub-question scope explicitly excludes mechanism-spanning findings.

**Rule B: Use fresh tags for each filter pass.** Do not overwrite the candidate pool in place. If you need to re-filter, run the new filter against the original search result ID, not against the previous filter's output.

**Rule C: If `--require N` is not met after filter, inspect what got cut before retrying.** Specifically:
- Run `paperclip cat` or check the filter output to see which papers were dropped
- Look especially for papers whose auto-summary indicates on-topic content but unconventional framing
- If a dropped paper appears to be on-topic by its auto-summary, the filter rubric is probably too narrow — broaden the filter language before retrying, do not just adjust `--require N` down

**Rule D: For each sub-question, check the keeper set against the anchor candidates list before moving to step 3 (map).**
- If an anchor candidate that should appear in this sub-question is NOT in the keeper set, attempt one targeted recovery search to bring it in.
- If the recovery search doesn't surface it either, note this in the sub-question's "Excluded and why" field with a brief justification.
- If it surfaced in search but was filtered out, that means the filter dropped a flagged anchor — that's a signal to broaden the filter, not to skip the anchor.

---

## PHASE 2: Post-sub-question work

**10. Anchor reconciliation.** For each anchor candidate from Phase 0:
- Check whether it appears in the final keeper set of at least one sub-question.
- If yes, note which sub-question(s) and confirm it's cited in the relevant table.
- If no, either (a) explicitly justify why it was excluded after consideration, or (b) inject it manually into the appropriate sub-question's keeper set and re-run the map extraction for that paper specifically.

**Write a "Missing anchors" section to `_run_report.md`** listing any anchor candidates that did not appear in the final digest, with the justification for each exclusion. An empty list is the ideal outcome.

**11. Identify load-bearing claims and add verification anchors.** Review the full assembled digest. Identify 8-15 claims most likely to matter in downstream use. Use `paperclip cat -n` and `grep` to locate supporting passages. Record as `paper_id : L<line> : <quoted phrase>` in the scaffold's Verification Anchors section.

**12. Generate bibliography manually** via `paperclip lookup`. Alphabetical by first author.

**13. Cross-cutting observations.** Add anything that emerged across sub-questions, conflicts, notable absences.

**14. Final report.** Write to `~/paperclip-test/abx_test_v2/_run_report.md`:
- Wall-clock time and total papers cited
- Anchor candidates: how many identified in Phase 0, how many made it into the final digest, missing anchors list with justifications
- Sub-questions where evidence was thin or where map fallback was used
- Any filter retries triggered by Rule C (broadened filter language) and what the recovered papers were
- Three to five unexpected findings worth attention on return
- Honest self-assessment of which sub-questions came out best and which are weakest

## Constraints (in addition to sandbox)

- **Mechanism class is the unit of analysis in SQ2, not drug.** One row for β-lactams, not 17.
- **SQ1 has a scope ceiling.** Working reference, not textbook. If a section grows past ~600 words, cut.
- **SQ3 and SQ4 must reference prior sub-questions' outputs.** The conceptual scaffold from SQ1 and SQ2 is the organizing structure.
- **Thin evidence is signal.** Do not broaden searches to pad tables.
- **Distinguish in vitro from clinical evidence carefully** throughout SQ3 and SQ4.
- **DOI or PMID required for every row.**
- **Do not draft a brief or review article.** Structured findings only.

## Deliverables

- `~/paperclip-test/abx_test_v2/abx_test_v2_filled.md` — filled-in digest
- `~/paperclip-test/abx_test_v2/abx_test_scaffold.md` — preserved as template (do not modify)
- `~/paperclip-test/abx_test_v2/_anchor_candidates.md` — Phase 0 output
- `~/paperclip-test/abx_test_v2/_progress.md` — timestamped step log
- `~/paperclip-test/abx_test_v2/_run_report.md` — final summary report, including missing anchors section

## Pause points

**None.** Run end-to-end.
