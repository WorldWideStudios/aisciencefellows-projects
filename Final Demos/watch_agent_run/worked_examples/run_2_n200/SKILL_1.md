---
name: paperclip
description: Search and read full-text biomedical papers, regulatory documents, clinical trials, and protein databases using the paperclip CLI.
---

# Paperclip

A virtual filesystem of full-text biomedical papers, regulatory documents, clinical trials, and protein databases.

## Filesystem

```
/papers/          3.4M+ papers (PMC, bioRxiv, medRxiv, arXiv)
/fda/             Regulatory documents
  us/             US FDA (200k+ docs)
  jp/             Japan PMDA (38k+ docs)
  eu/             EU EPAR (8k+ docs)
/trials/          Clinical trial registries (alias: /clinicaltrials/)
  us/             ClinicalTrials.gov (580k+ trials)
  cn/             ChiCTR (116k+ trials)
  jp/             UMIN + JRCT (100k+ trials)
  eu/             EudraCT + CTIS + ISRCTN (85k+ trials)
  intl/           All registries combined + WHO ICTRP (1.08M+ trials)
/proteins/        UniProt + PDB + ChEMBL (574K+ proteins; search: -s proteins)
  {ACCESSION}/    Per-protein VFS (meta.json, content.lines)
/patents/         Patent publications (SQL VFS; search: -s patents)
  {PUB}/          e.g. US-9585906-B2 â meta.json, abstract.txt, content.lines,
                  sections/, surechembl/compounds.tsv, sequences.tsv
/sec/             SEC EDGAR life-sciences filings (ls/cat/sql: -s sec)
  {ACCESSION}/    Filing VFS (meta.json, content.lines, items/, exhibits/)
/clipboard/       User's personal clipboard (uploaded PDFs + corpus links)
/peer_reviews/    Nature transparent reviews + OpenReview reports
  {REVIEW_ID}/    Direct review access (meta.json, content.lines)
```

All document types share the same layout: `meta.json`, `content.lines` (full text, line-numbered), `sections/`, `figures/`, `supplements/`.
Papers with linked reviews also expose `peer_review/`, grouped by source and review ID:

```
/papers/<paper-id>/peer_review/open_review/<openreview-id>/
/papers/<paper-id>/peer_review/nature/<nature-review-id>/
```

Search peer reviews across both sources with `paperclip search -s peer_reviews "query"`.
This source is opt-in and is not included in the default paper search.

**Mandatory peer-review intent routing:** When the user asks for peer reviews,
reviewer comments, referee reports, author rebuttals, review concerns, or what
reviewers criticized, search `-s peer_reviews` first. Do not rely on a default
paper search or claim that reviews are unavailable until this source has been
searched explicitly. Ordinary papers and published commentaries may supplement
the review evidence, but must not silently replace it.

Each result prints a direct `Review:` path that can always be opened, plus a
`Reviewed paper:` path when an evidence-backed paper link exists:

```
paperclip ls /peer_reviews/<review-id>/
paperclip cat /peer_reviews/<review-id>/meta.json
paperclip cat /peer_reviews/<review-id>/content.lines
```

Use `meta.json` to inspect `linked_papers`, `linked_paper_path`, match method,
and confidence. OpenReview paper links come from accepted stored link records;
Nature links require an exact DOI match. If no reviewed-paper path is present,
do not infer one from title similarityâthe direct review path remains valid.
Patents follow that shell with patent-specific `abstract.txt`, `surechembl/`, and `sequences.tsv` (see `paperclip skills show patents`).

IDs: `PMC` (PubMed Central), `bio_` (bioRxiv), `med_` (medRxiv), `arx_` (arXiv), `fda_` (FDA), `tri_` (trials), patent publication numbers (`US-â¦-B2`, `EP-â¦`, `WO-â¦`).

Documents can be accessed without a region prefix: `/trials/NCT03928938/` works the same as `/trials/us/NCT03928938/`.

`/.gxl/` is writable scratch space. All other paths are read-only.

## Workflow

1. **Find by topic**: `search -s pmc "topic"` -> present results
2. **Find by exact text (across the whole corpus)**: `grep "term" /papers/` â full-text regex over every paper's body, not just abstracts. Use this (not `sql ... ILIKE`) to locate papers that mention a name/dataset/gene/accession.
3. **One paper**: `head`/`grep`/`scan` on `/papers/<id>/`
4. **Many papers**: `search -n 10` -> `map --from ID "q"` -> `reduce` -> synthesize
5. **Cite**: cite directly with line numbers from the text you read (see Citations)
6. **Stats/metadata**: `sql "SELECT ..."` (counts, dates, journals â not full-text)

**Repos are OFF by default.** Do not create, add to, or commit repos on your own initiative â cite directly instead. Only use the repo/verification workflow when the user explicitly asks for it (see Paper Repositories). If a command shows a leftover `[repo: <name>]` from an earlier task, ignore it â don't add papers to it unless the user asked to use that repo.

## Citations & Verification

Cite directly from the text you've read, using line numbers â this is the default for **every** query, whether a simple lookup or a multi-paper synthesis. Read the relevant lines and cite them; don't paraphrase beyond what the text supports.

Claim verification via repos is **opt-in**: only run it when the user explicitly asks to verify claims or build a cited repo (see Paper Repositories). Do not start repos or run `repo commit` verification on your own.

### Citation format

Cite **[1]**, **[2]** inline. End with:

```
--------
REFERENCES
[1] Authors. "Title." *Journal* vol, pages (year). doi:XX
    https://paperclip.gxl.ai/citations/papers/<doc_id>#L<n>
```

Note that the ONLY valid inline format is `[N]` â e.g. `[1]`, `[2]`. Don't use variants like `[1, L151]`, `[1, line 45]`, `[ref 1]`, `(L45)`, `(L45-L52)`, `(L45, L120)`, or any other modification. The `L<n>` format is only valid inside REFERENCES URLs and CLI flags â never inline in prose text. Every direct quote and blockquote (">") must be followed by a citation.

URLs associated with citations should be in the following format: `https://paperclip.gxl.ai/citations/{papers|fda|trials|patents|sec}/<doc_id>#L<n>`

- Line numbers from `L<n>` prefixes in `content.lines`.
- Single: `#L45` - range: `#L45-L52` - multiple: `#L45,L120,L210`.
- Nature style for journals. "bioRxiv/medRxiv (year)" for preprints.
- Get author names, title, DOI from `meta.json`.
- Never expose doc_id in prose. Number references in order of first appearance.

## Commands

Run `<cmd> --help` for full usage on any command.

### Search & Discovery

| Command | Description |
|---------|-------------|
| `paperclip search QUERY` | Semantic + keyword search. Key opts: `-n`, `-s SOURCE`, `-e`, `--since`, `--sort`, `--author`, `--journal`, `--year`, `--corpus` (search full corpus even with a repo active - use during discovery) |
| `paperclip grep PATTERN PATH` | Regex search across corpus or within a paper. Use `--bool '"A" AND NOT "B"' /papers/` for whole-document boolean regex (`NOT > AND > OR`); pure NOT requires `--from` or `search | grep`. Corpus-wide grep is time-bounded by default; add `--exhaustive` for a full-timeout scan when a rare pattern returns nothing. |
| `paperclip lookup FIELD VALUE` | Find by metadata: doi, author, title, pmc, pmid, journal |
| `paperclip sql "SELECT ..."` | SQL on `documents` table (200-row limit) |
| `paperclip filter --from ID QUERY` | LLM-based relevance filter on search results |
| `paperclip refine --from ID FLAGS` | Deterministic metadata/structure filtering; saves a new result set |
| `paperclip merge/intersect/subtract IDs...` | Union, intersection, or subtraction of saved paper sets |

### Reading & Analysis

| Command | Description |
|---------|-------------|
| `paperclip cat`, `head`, `tail`, `ls` | Read files, list directories |
| `paperclip scan FILE "p1" "p2"` | Multi-pattern search in a file |
| `paperclip ask-image PATH "q"` | Analyze figure with vision. `--fn describe` / `--fn extract-data` |
| `paperclip map --from ID "q"` | LLM reader across search results - answers per paper |
| `paperclip reduce --from ID "q"` | Synthesize map results. Strategies: summarize, table, themes |
| `paperclip results [ID]` | View saved search/map results. `--list` to see all |

### Paper Repositories - Core (opt-in)

**Only use these when the user explicitly asks to build a repo or verify claims â never by default.** `paperclip git` (= `paperclip repo`) tracks a named collection of papers + verifiable *claims*, independent of the clipboard. It snapshots and verifies claims against full text; it does **NOT** store arbitrary generated files or copy papers into `/clipboard/`. To persist a file you created (e.g. `analysis.json`, `index.html`, a report), use **`paperclip upload <file> --into <folder>`** (see Clipboard below) â **never** `git commit`/`repo commit`, which only records claim metadata.

Repos are deliberately domain-agnostic: claims may be free text or
caller-defined JSON. For a systematic review or quantitative meta-analysis,
load `paperclip skills show paperclip-meta-analysis` before creating the repo.
That workflow requires structured, line-pinned JSON claims and deterministic
compile/QA scripts; ordinary free-text claims remain valid for general repos
but are not poolable meta-analysis effects.

| Command | Description |
|---------|-------------|
| `paperclip git init <name>` | Enable git tracking for a named repo |
| `paperclip git add <id> "claim"` | Add paper + verifiable claim to the repo |
| `paperclip git add <id>` | Add paper without claim (collection only, not verified) |
| `paperclip git commit -m "message"` | Snapshot + verify all claims against full text in parallel |
| `paperclip git status` | Show current repo: papers, claims, [OK]/[X] marks from last commit |
| `paperclip git log` | Show commit history |

**Requires an active repo.** Run `paperclip git init <name>` first.

### Clipboard

The `/clipboard/` filesystem is the user's personal document space.

| Command | Description |
|---------|-------------|
| `paperclip upload <file> --into <folder>` | **Save a generated FILE (JSON/HTML/CSV/MD) into a clipboard folder.** This is how you persist analysis artifacts/reports â `git`/`repo commit` does NOT do this. |
| `paperclip cp /papers/<id> /clipboard/<folder>/` | Save a paper to your clipboard (zero-copy corpus link) |
| `paperclip cp ~/local/path /clipboard/` | Copy local PDFs to clipboard |
| `paperclip mkdir /clipboard/<folder>` | Create a clipboard folder |
| `paperclip rm /clipboard/<folder> -R` | Soft-delete a folder |
| `paperclip rm /clipboard/<folder>/<id>` | Remove a single document/link |
| `paperclip import refs.bib --into /clipboard/<folder>` | Import .bib as corpus links into a folder |
| `paperclip ls /clipboard/` | List clipboard folders |
| `paperclip ls /clipboard/<folder>` | List documents in a folder |
| `paperclip head /clipboard/<folder>/<id>/content.lines` | Read content of a clipboard document |
| `paperclip search "query" -s clipboard` | Search only within your clipboard |

To save a paper you found via search to your clipboard, use `cp /papers/<id> /clipboard/<folder>/`.
Do NOT use `paperclip import <id>` for this â that imports the paper's references, not the paper itself.

Corpus links (`cp /papers/...`) are symbolic references â they don't duplicate content.
Reading `content.lines` on a linked paper proxies to the original corpus.

### Paper Repositories - Advanced (legacy `repo` commands)

| Command | Description |
|---------|-------------|
| `paperclip repo checkout <name>` | Switch branch or repo. Tries branch first, then repo. Use `-` to deactivate. |
| `paperclip repo branch <name>` | Create + switch to a new branch (forks current papers) |
| `paperclip repo merge <branch>` | Merge a branch into the current one (union of papers) |
| `paperclip repo` | List all repos |
| `paperclip repo history` | Command audit trail (searches, maps, etc. - not commits) |
| `paperclip repo citations` | Citation counts + graph via Semantic Scholar |
| `paperclip repo export bibtex\|ris\|csv\|markdown` | Export repo as bibliography or data |
| `paperclip import` | Import references: from .bib/.ris files, or fetch a paper's bibliography via Semantic Scholar (does NOT add the paper itself) |
| `paperclip library` | Personal paper library |

### Other