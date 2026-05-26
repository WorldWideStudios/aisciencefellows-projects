# paperclip-orchestration

A workflow for turning a research question into a structured, citation-anchored evidence digest — using [Paperclip](https://paperclip.gxl.ai/) (an agent-first CLI over 11M+ full-text papers, clinical trials, and regulatory documents) and Claude Code.

You ask a question. A Claude skill converts it into a run scaffold and an instruction file. Claude Code executes the run end-to-end against Paperclip. You get back a filled digest: evidence tables, synthesis, confidence reads, and line-level verification anchors.

This was built for my own literature work: clinical evidence briefs and topic deep-dives. The skill's framing reflects that origin. It generalizes fine to any set of related research questions; just read past the occasional first-person phrasing. 

This repo contains no application code. The executable pieces are Paperclip (GXL's CLI) and Claude Code (the agent); what's here is the orchestration layer that directs them — a Claude skill, a prompt scaffold, and the filter-and-phase discipline that shapes a run. The contribution is the structure, not new software. (The v2 verification step described below is where deterministic code enters the pipeline.)

See the `eg1_*`, `eg2_*`, and `eg3_*` folders for three complete runs (question in, digest out) — and read the note on what those examples are and are not, below.

---

## Status: v1.0 — a working note

**This is published to be read, not yet run.**

A citation audit of the example runs (see the `eg*` folders) found that the digest-assembly step can occasionally emit a citation identifier — a DOI or PMID — from the model's memory instead of verifying it against the bibliography Paperclip actually retrieved. In the audited run, the underlying papers were identified correctly and the retrieved bibliography was correct; the wrong identifiers were introduced downstream, where the agent assembled the final digest.

The lesson generalizes past this one bug: a step with a single correct answer — resolving a citation to its identifier is a lookup, not a judgment — should be handled by deterministic code, not left to a language model that will sometimes generate a plausible wrong answer. The v2 priority is a verification step that checks every citation in the digest against the retrieved bibliography before the digest is finalized.

Until that ships, treat this repo as a **documented method, not a turnkey tool**. The workflow, the skill, and the example runs are all here to read and learn from. If you do run it, verify every citation by hand against the bibliography — which the rest of this README will show you how to produce.

---

## What's in this repo

- `paperclip-shell-skill.skill` — the Claude skill that turns a question set into run inputs. Load it into Claude (Claude Code, or claude.ai).
- `eg1_post_partum_estrogen/`, `eg2_antibiotic_choice_immunomodulation/`, `eg3_microvascular_CV_in_women/` — three finished runs (transdermal estrogen for postpartum mood; macrophage signaling and antibiotic mechanism; microvascular disease in women). Each shows the scaffold, the instruction file, and the filled digest.
- `runs/` — where your own runs go. One subfolder per question set. Empty on clone except for a `.gitkeep`.
- `.gitignore` — excludes OS and editor files (`.DS_Store`, `.venv/`, and the like).

A note on `Paperclip_documentation.md`: a snapshot of Paperclip's documentation as of the v1.0 run dates (early May 2026) is included for reproducibility, so the example runs are auditable against the exact docs they used. Paperclip is GXL's product; see [paperclip.gxl.ai](https://paperclip.gxl.ai/) for the current version. It is the version you copy in setup, not this snapshot, that is the source of truth for your own runs.

---

## Prerequisites

You need, in this order:

**1. Clone this repo.**

```
git clone https://github.com/drjlgross/paperclip-orchestration.git
cd paperclip-orchestration
```

Everything below happens from the repo root.

**2. Install Paperclip.**

```
curl -fsSL https://paperclip.gxl.ai/install.sh | bash
```

Paperclip is a third-party CLI from GXL — not part of this repo. Installation, data sources, and command reference are at [paperclip.gxl.ai/docs](https://paperclip.gxl.ai/docs).

**3. Authenticate Paperclip — this is required, do not skip it.**

```
paperclip login
```

This opens a browser sign-in once and caches credentials on your machine. Confirm it worked:

```
paperclip config
```

You should see your account next to `Auth: ✓`.

This step is easy to forget because it's a one-time action — but a run launched without it **fails partway through with no prompt**, because the run is non-interactive. If you have ever run `paperclip login` on this machine, you are fine. If you are not sure, run it again; it is harmless to repeat.

**4. Supply the Paperclip documentation file.**

The run reads a local copy of Paperclip's docs as a reference. You provide it — that way it is always the current version, and nothing version-specific is committed to this repo.

Open [paperclip.gxl.ai/docs](https://paperclip.gxl.ai/docs) and click **Copy as Markdown** (top right). The docs are now on your clipboard. From the repo root, write them to a file:

```
# macOS
pbpaste > Paperclip_documentation.md

# Linux (X11)
xclip -o -selection clipboard > Paperclip_documentation.md

# Linux (Wayland)
wl-paste > Paperclip_documentation.md
```

You do not need a text editor for this — the terminal turns the clipboard into the file.

**5. Claude Code.**

You need [Claude Code](https://docs.claude.com/en/docs/claude-code) installed, with the `paperclip-shell` skill loaded (see next section).

---

## Running a digest

Before running, read the **Status** section above — v1.0 has a known citation-verification gap, and any run's output must be hand-checked against its bibliography.

**Load the skill.** Add `paperclip-shell-skill.skill` to Claude. The skill triggers on phrasings like "make a paperclip shell for [question]" or pasting a research question with sub-questions.

**Give it your question.** A question set works best as: one overarching question, plus 3–6 sub-questions. The skill will ask you for a short topic slug (e.g. `eg1_post_partum_estrogen`) and an audience, then infer table columns and topic-specific constraints for each sub-question.

**Collect the two files it produces.** The skill outputs a scaffold (`{slug}_research_digest_scaffold.md`) and an instruction file (`PROMPT.md`). Put both into a new run folder:

```
mkdir -p ./runs/{slug}/
# move the two downloaded files into ./runs/{slug}/
```

**Read the skill's "before you launch" note.** It flags anything you should sanity-check in the generated files — usually inferred table columns or constraints. This is the moment to correct them; once the run starts it does not pause.

**Launch the run.** From the repo root:

```
claude --dangerously-skip-permissions "Read ./runs/{slug}/PROMPT.md and follow the workflow it describes."
```

The run executes end-to-end against Paperclip — scoping pass, per-sub-question search/filter/extract, verification anchoring, final report. It writes a filled digest (`{slug}_filled.md`), a progress log, and a run report into `./runs/{slug}/`.

### About `--dangerously-skip-permissions`

This flag tells Claude Code not to prompt for confirmation on each action, which is what lets the run go end-to-end unattended. It is also a real trust decision: you are letting an agent run a long sequence of commands without checkpoints. Two things make that defensible here:

- The `PROMPT.md` opens with a strict filesystem sandbox — the run may only write inside its own `./runs/{slug}/` folder, and is instructed not to install software, change configuration, or make network calls other than Paperclip commands.
- The run is doing literature retrieval and synthesis, not anything destructive.

Read the sandbox section of any generated `PROMPT.md` before you launch. If you are not comfortable with the flag, you can run without it and approve actions as they come — the run just becomes interactive.

---

## How the workflow is structured

The run is not a single prompt — it has a deliberate shape, and `PROMPT.md` encodes it:

- **Phase 0 — scoping pass.** Before any sub-question work, the run does broad searches on the *overarching* question to identify anchor papers: the papers a domain expert would expect the digest to engage with regardless of how sub-questions are framed. This guards against sub-question-specific searches missing integrative work.
- **Phase 1 — per-sub-question loop.** For each sub-question: parallel searches, relevance filtering under explicit filter-discipline rules, structured extraction via `paperclip map --output_schema`, manual table assembly, and a checkpoint write.
- **Phase 2 — reconciliation and anchoring.** Anchor papers from Phase 0 are reconciled against what actually made the digest. Load-bearing claims get line-level verification anchors. A run report records wall-clock time, thin-evidence sub-questions, and an honest self-assessment.

Tables are assembled by the agent from `map` output rather than by a single command — this is the intended Paperclip workflow, not a limitation. Verification anchors are recorded inline as `paper_id : L<line> : <quoted phrase>`. The citation-verification gap noted in the Status section lives in this assembly step.

---

## About the examples

The repo contains three complete runs at its root:

- `eg1_post_partum_estrogen` — low-dose transdermal estrogen for postpartum mood stabilization.
- `eg2_antibiotic_choice_immunomodulation` — macrophage signaling, antibiotic mechanism of action, and immune-modulatory effects.
- `eg3_microvascular_CV_in_women` — microvascular disease as the axis of female cardiovascular pathology.

Each folder shows the full arc: the scaffold the skill produced, the `PROMPT.md` instruction file, and the filled digest the run generated. The `eg3_microvascular_CV_in_women` run is also the subject of the citation audit referenced in the Status section.

A disclosure on `eg2`: this topic overlaps my own PhD research, and the citation corpus for that run includes a paper of mine that I structured the query set trying to surface. That overlap is useful — it let me check the digest's claims quickly against my own expertise — but it is also a bias. I want to flag it: I'm not unbiased on whether my own paper belongs in this corpus!

**These are demonstrations of a literature-synthesis workflow — not clinical guidance, not recommendations, and not a substitute for primary sources or professional judgment.** The digests name specific interventions, doses, and populations because that is what the underlying literature describes; they are not endorsements of any of it. Each digest is a snapshot of one automated run against the literature available at the time, and each is explicit about where evidence is thin, extrapolated, or contested. Read them as examples of the *format and method*, and go to the cited papers for anything you would act on.

---

## A note on Paperclip versions

This workflow is built on Paperclip's current command set. Paperclip's paper-repository commands are in beta and not yet generally available; until they ship, the workflow records keeper papers and verification anchors inline and builds bibliographies manually. `map` can occasionally return a server-load error — the run retries and falls back to manual extraction. None of this is pinned to a version number, so the workflow degrades gracefully as Paperclip evolves.

If Paperclip's behavior and this workflow's instructions ever diverge, the `Paperclip_documentation.md` you supplied in setup is the source of truth — it is whatever version you copied.

---

## License

MIT
