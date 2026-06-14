# Telegram digest orchestration prompt (v1 pipeline, headless)

You are running headless and unattended (`claude -p`, `--dangerously-skip-permissions`). No one will answer prompts. Run end to end, then stop. Do not ask questions. Do not use present_files (the bot delivers the file).

## Inputs (from the invoking message)
- The research question in `question.txt` in the working directory.
- A `slug`, the working directory path, and a sub-question cap (`MAX_SQS`).
- The paperclip-shell v1 skill, unpacked, at `~/paperclip-test/bot/paperclip-shell-skill/` (SKILL.md plus references/). This is the authoritative workflow. Read it; do not improvise the pipeline from memory.
- Current Paperclip docs at `~/paperclip-test/bot/Paperclip_docs_043` (read-only). Use for exact command syntax.

## What you are doing
Running Julia's v1 Paperclip pipeline on a single texted question, unattended. Normally the paperclip-shell skill scaffolds interactively (asking for slug and audience), then a separate run executes the generated PROMPT.md. Here you do both stages in one pass, non-interactively, using the skill's reference files as the source of truth.

## Stage A: scaffold (non-interactive port of the skill's Steps 3-6)
Follow `paperclip-shell-skill/SKILL.md`, replacing its interactive steps as follows:
1. Question and sub-questions. Treat `question.txt` as the overarching question. The texter gives one question, not a sub-question list, so decompose it yourself into 2 to MAX_SQS load-bearing sub-questions (the decomposition a domain expert would choose). Do not pad to the cap.
2. Slug and audience (skill Step 2, normally asked). Use the provided slug. Default the audience to a deep-dive working reference (post-doc deep dive) unless the question clearly implies a clinician brief. Do not ask.
3. Columns (skill Step 3). Read `references/column_schemas.md` and infer per-sub-question table columns. DOI or PMID is always the last column.
4. Constraints (skill Step 4). Read `references/constraint_patterns.md` and infer 2-4 topic-specific constraints. Always include "thin evidence is signal, not search failure."
5. Scaffold (skill Step 5). Read `references/scaffold_template.md` and write `{slug}_research_digest_scaffold.md` to the working directory.
6. PROMPT.md (skill Step 6). Read `references/prompt_template.md` and write `PROMPT.md` to the working directory, substituting the slug, the audience and topic phrase, 3-4 Phase 0 scoping queries, the Rule A example, and the inferred constraints. Leave the workflow phases, filter discipline, state tracking, and stop conditions verbatim, with two edits: point the Paperclip documentation path to `~/paperclip-test/bot/Paperclip_docs_043`, and set the working directory to the actual working directory passed to you (not `~/paperclip-test/{slug}/`). Do not use present_files; just write the files.

## Stage B: execute
Follow the `PROMPT.md` you just wrote, end to end: Phase 0 scoping pass and `_anchor_candidates.md`; Phase 1 per-sub-question loop with the Rule A-D filter discipline; Phase 2 anchor reconciliation, verification anchors, manual bibliography, and `_run_report.md`. Maintain `_progress.md`. Checkpoint `{slug}_filled.md` after each sub-question. Honor the stop conditions.

## Note on Paperclip version
`prompt_template.md` documents v0.3.0 limitations (no `reduce`, no repo commands) and uses manual workarounds (manual table assembly from `map` output, inline keeper papers, manual bibliography via `lookup`). Run it as written; the workarounds produce correct output. Do not switch to `reduce` or repo commands here even though the installed version supports them. Aligning the pipeline to v0.4.3 is separate work, not part of this run.

## Finish
Ensure `{slug}_filled.md` exists in the working directory, then stop. The bot sends it back.
