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

| Command | Description |
|---------|-------------|
| `paperclip config` | Settings and connection diagnostics |

Text processing: `sed`, `awk`, `sort`, `cut`, `tr`, `jq` - standard tools, pipes via `bash '...'`.

## Search

**The `-s` flag is required.** Every search must specify a source with `-s` or a virtual directory path.

| Scope | Command |
|-------|---------|
| All papers (PMC + bioRxiv + medRxiv + arXiv) | `search -s papers "CRISPR delivery"` |
| Specific paper corpora | `search -s pmc,biorxiv,medrxiv,arxiv "CRISPR delivery"` |
| PMC (full-text papers) | `search -s pmc "CRISPR delivery"` |
| bioRxiv preprints | `search -s biorxiv "protein design"` |
| medRxiv preprints | `search -s medrxiv "long COVID"` |
| arXiv preprints | `search -s arxiv "diffusion models"` |
| Abstracts only (broader) | `search -s abstracts "drug discovery"` |
| FDA (all regions) | `search -s fda "pembrolizumab"` |
| FDA (specific region) | `search "pembrolizumab" /fda/us` |
| Trials (all) | `search -s trials "breast cancer HER2"` |
| Trials (specific) | `search "breast cancer" /trials/us` |
| Proteins (UniProt/PDB/ChEMBL) | `search -s proteins "kinase inhibitor"` |
| Patents | `search -s patents "kinase inhibitor"` |
| SEC EDGAR filings | `search -s sec "Moderna"` Â· `grep "term" /sec/` Â· `cat /sec/{ACCESSION}/content.lines` |

**Source selection rule:** When the user specifies a domain (e.g. "trials", "regulatory", "FDA", "patents", "SEC"), use the corresponding `-s` flag or virtual directory path. For general biomedical literature, use `-s pmc`. If a query mentions proteins, compounds, drugs, structures, UniProt, PDB, or ChEMBL, ask the user whether they want structured database data (`-s proteins`) or published papers about the topic (`-s pmc`). For patent filings, SureChEMBL chemistry, or claims/description text, use `-s patents` / `/patents/`. Run parallel targeted searches when multiple sources are needed.

**MUST: Before deep patent work (reading claims/description, SureChEMBL compounds, or patent SQL assumptions), run `paperclip skills show patents` and read it.** Do not invent legacy paths like `claims/` or `family/members.tsv`.

Key options: `-n/--limit`, `-s/--source`, `--ranking [hybrid|bm25|vector|analogical]`, relevance floors, `--year[-min|-max]`, `--journal`, `--article-type`, repeatable `--exclude-*` metadata flags, `--has-full-text`, `--has-block-type`, `--without-block-type`, `--has-section`, `--without-section`, `--full-text`, and `--bool`.

Boolean paper search uses quoted, analyzed phrases with case-insensitive `NOT > AND > OR` precedence and parentheses. It requires an explicit `--ranking bm25`; unlike `grep`, operands are OpenSearch phrases, not regexes. It supports PMC, bioRxiv, medRxiv, arXiv, and abstract-only search plus normal source/date/journal/article-type/year/sort/limit/ID-scope filters. Match full paper content with `--full-text` (not available for abstract-only sources). Boolean mode cannot be combined with `-m`, `-e`, `-r`, `-a`, or `-t`.

Example: `paperclip search -s pmc --bool --ranking bm25 '"CRISPR" AND ("base editing" OR "prime editing") AND NOT "review"'`

For deterministic cohort refinement, use `refine --from s_ID` with the same quality flags. Use `grep --bool --from s_ID --block-type table --section results EXPR` to constrain text predicates to structural content. Use `merge`, `intersect`, and `subtract` for saved-set algebra.

Add `--save-as NAME` to any result-producing command to create a readable session-scoped alias. Aliases can replace generated `s_` IDs in `--from`, `merge`, `intersect`, and `subtract`, e.g. `search --save-as pk_candidates "pharmacokinetics"` then `refine --from pk_candidates --has-block-type table --save-as pk_tables`.

Run reusable deterministic workflows with `paperclip search --config workflow.yaml`. A workflow uses named steps with `operation: search`, `grep`, `refine`, `merge`, `intersect`, or `subtract`; later steps reference earlier names through `from`. Supply typed parameter overrides with `--set NAME=VALUE`, external result IDs or aliases with `--input NAME=VALUE`, and name a particular run with `--save-as NAME`.

**Analogical search** (`--ranking analogical`): Finds papers that share the same *structural method* across different domains, even when vocabularies are completely different. Use when the user wants cross-domain analogies, methodological parallels, or "what other fields use this technique?" queries.

**How to write the query â this matters a lot:**

The query text gets embedded with a fine-tuned model trained on paper abstracts. Different query formulations produce very different results:

1. **Best: full abstract** â If the user has a specific paper, use its entire abstract as the query. This is what the model was trained on and produces the highest-quality matches. Read the paper first with `cat`, extract the abstract, then search with it.
2. **Good: method/problem description (1-2 sentences)** â Describe the *structural method* or *problem pattern*, not the topic. Focus on what the paper *does*, not what it's *about*. Example: "correcting for systematic under-reporting in training data where the missingness mechanism is unknown" finds cross-domain analogies across biodiversity, epidemiology, and proteomics.
3. **Good: plain-language problem** â Describe the problem without jargon: "my training labels are unreliable because some positives are systematically missed as negatives" finds positive-unlabeled learning papers across NLP, biology, and cosmology.
4. **Bad: topic keywords** â Short keyword queries like "influence functions" or "CRISPR delivery nanoparticle" return topically similar papers, not structural analogies. This defeats the purpose â use standard `--ranking hybrid` for keyword searches.

**Workflow for a known paper:**
```
paperclip cat PMC1234567 | head -30        # read abstract
paperclip search -s arxiv --ranking analogical "<paste full abstract here>" -n 10
paperclip search -s biorxiv --ranking analogical "<paste full abstract here>" -n 10
```

**Workflow for a described problem:**
```
paperclip search -s arxiv --ranking analogical "I need to approximate an expensive leave-one-out computation cheaply by exploiting low-rank structure in my parameter space" -n 10
```

**Tip:** Run analogical search across multiple sources (`-s arxiv`, `-s biorxiv`, `-s pmc`) separately to find analogies in different scientific communities. The most valuable matches are often in the source you'd least expect.

### Filter

Use `filter` after `search` to remove irrelevant results via LLM evaluation before passing to `map`:

```
paperclip search -s fda "semaglutide" -n 50
paperclip filter --from s_abc123 "semaglutide cardiovascular outcomes"
paperclip map --from s_abc123 "What were the primary endpoints and results?"
```

`filter` overwrites the result set in place. If `--require N` fails, re-run search with broader terms to get a fresh result ID.

### Lookup

Find by metadata field: `doi`, `author`, `title`, `pmc`, `pmid`, `arxiv`, `journal`, `year`.

```
lookup doi 10.1101/2024.01.15.575613
lookup pmc PMC7194329
lookup author "James Zou" -n 10
```

### SQL

```
sql "SELECT pub_year, COUNT(*) FROM documents WHERE title ILIKE '%CRISPR%' GROUP BY pub_year ORDER BY pub_year"
```

Columns: `id`, `title`, `doi`, `authors`, `source`, `abstract_text`, `pub_date`, `journal_title`, `article_type`, `pmid`, `keywords`, `categories`, `pub_year`.

Only `SELECT` on the `documents` table. 15s timeout, 200-row limit.

**SQL is for metadata + aggregation only â it is NOT full-text search.** It sees only titles/abstracts (`abstract_text`), not paper bodies, and `ILIKE '%term%'` does a slow unindexed scan. To find papers that *contain* a term, use `grep "term" /papers/` (exact, full text, corpus-wide) or `search "..."` (semantic) â a body-text mention (Methods, Data Availability, references) will be missed by `abstract_text ILIKE` but found by `grep`. Use SQL for counts, date/journal/author filters, and grouping â not to locate papers by content.

### Proteins SQL (`-s proteins`)

```
paperclip sql -s proteins "SELECT COUNT(*) FROM uniprot_v.proteins"
paperclip sql -s proteins "SELECT * FROM pdb_v.structures_by_accession WHERE accession='P00533' LIMIT 10"
paperclip grep "TP53" /proteins/
paperclip cat /proteins/P04637/meta.json
```

Key views: `uniprot_v.proteins`, `uniprot_v.features`, `pdb_v.structures_by_accession`, `chembl_v.bioactivities_by_accession`, `chembl_v.drugs_by_accession`. Join key: UniProt accession.

**MUST: Before writing ANY protein SQL (or protein grep/cat/search), you MUST run `paperclip skills show proteins` and read it.** Do not guess column names, enum values, join keys, or query patterns from memory. Skipping this step produces wrong queries.

### Patents (`-s patents`)

```
paperclip search -s patents "CDK4 inhibitor"
paperclip cat /patents/US-9585906-B2/meta.json
paperclip cat /patents/US-9585906-B2/content.lines
paperclip cat /patents/US-9585906-B2/surechembl/compounds.tsv
```

Doc id = `publication_number`. Claims live in `content_blocks` (`section=claims`), not a separate folder. SureChEMBL compounds join at read time on publication number.

**MUST: Before deep patent work, run `paperclip skills show patents` and read it.**

### SEC EDGAR filings (`-s sec` / `/sec/`)

**Catalog for companies; corpus `grep` for body topics.** Paths:

```
/sec/{ACCESSION}/meta.json
/sec/{ACCESSION}/content.lines          # L numbers are 1-indexed (#L1 is first)
/sec/{ACCESSION}/items/{code}.lines
/sec/{ACCESSION}/exhibits/
/sec/{ACCESSION}/{SEQUENCE}/content.lines
```

XBRL facts are not a VFS path â use `sql -s sec` on `xbrl_facts` (see `paperclip skills show sec`).

```
paperclip search -s sec "Moderna"                   # catalog (prefer over sql ILIKE)
paperclip search -s sec --since 1y "MRNA"
paperclip grep "GLP-1" /sec/                        # corpus body (slab)
paperclip head -40 /sec/{ACCESSION}/content.lines
paperclip grep "myocarditis" /sec/{ACCESSION}/content.lines
paperclip head -40 /sec/{ACCESSION}/{SEQUENCE}/content.lines   # exhibits
```

- Catalog: use **`search -s sec`** for company/ticker/form/date â do not hand-roll
  `sql â¦ company_name ILIKE` for that. Reserve `sql` for counts/joins/`documents`.
  Never `search "GLP-1"` (topics aren't in the catalog).
- Body: `grep "term" /sec/` for topics; scoped grep/head on known accessions.
  Never `sql â¦ content_blocks ILIKE`.
- **Cite:** printed `L<n>` only. Primary â `https://paperclip.gxl.ai/citations/sec/{ACCESSION}#L<n>`. If you read
  `/{SEQUENCE}/`, **must** cite `https://paperclip.gxl.ai/citations/sec/{ACCESSION}:{SEQUENCE}#L<n>` or the viewer
  shows "Line not found". Do not narrate indexing in the answer.

**MUST: Before writing ANY SEC SQL, run `paperclip skills show sec` and read it.**
Do not invent columns.

## Map & Reduce

`map` runs a lightweight LLM reader on each paper. `reduce` synthesizes map results.

```
search -s pmc "protein design" -n 10
map --from s_xxx "What methods were used for protein design?"
reduce --from m_xxx --strategy table "Compare methods and results"
```

Reduce strategies: `summarize`, `table`, `themes`, `consensus`, `bullet_points`, `extract`.

**Tips:**
- Be specific. Bad: "Summarize this paper." Good: "What delivery vector was used, what cell type was targeted, and what transfection efficiency was reported?"
- Enumerate every field you want extracted.
- Specify which section to focus on (e.g. "From the Methods section, extract...").
- Keep to **3-10 papers** (`-n 5` or `-n 10`).
- After map, respond directly - don't follow up by reading individual papers.

## Paper Repositories

**Opt-in only.** Repos are not part of the default workflow â do not create or use them unless the user explicitly asks to build a repo, track a collection, or verify claims. By default, cite directly from the text. The rest of this section applies only once the user has asked for a repo.

### How `add` works

- `repo add <id> "claim"` - appends a verifiable claim to the paper. Optional: `--lines L45-L52` (faster verification).
- `repo add <id> --json '{"type":"custom",...}' --lines L45-L52` stores a
  caller-defined structured claim without making the repo domain-specific.
- **Each `repo add` with a claim creates a new entry.** A paper can have multiple claims - call `repo add` multiple times with the same ID and different claims.
- To replace a wrong claim: `repo remove <id>`, then `repo add <id> "corrected claim"`.
- `repo add <id>` - collection only, never verified.

### How `commit` works

- `repo commit -m "message"` runs verification on all unchecked claims in
  parallel, then creates the metadata snapshot. Unresolved verifier errors block
  the snapshot so the same command can safely retry them.
- Verification produces [OK] (supported) or [X] (not supported) per claim.
- For a generic repo, [X] is a conclusive advisory verdict and does not block
  the metadata snapshot. Fix it by re-adding a corrected claim, then commit
  again. For a data-curation or meta-analysis workflow, the specialized Phase-6
  compiler requires zero active [X] claims; correct or remove/log every [X]
  before compilation.
- Previously verified claims are not re-checked. Use `--no-verify` to skip verification entirely.

### How `checkout` works

- `repo checkout <name>` - tries to switch **branch** first (within current repo), then falls back to switching **repo**.
- `repo checkout -` - deactivates the repo entirely.
- **If the active repo is unrelated to the current request, start a new one (`repo init <topic>`) or deactivate it (`repo checkout -`) before adding papers - never append unrelated papers to an existing repo.**

**When you are using a repo (the user asked for one), run `repo status` before writing your final response** to confirm which claims are verified. Only cite [OK] papers. For [X] claims: revise the claim, find a different source, or drop it. (If you're not using a repo, skip this.)

### Full workflow example

```
# 1. Create repo
paperclip repo init my-review

# 2. Search and read (-s is required)
paperclip search -s pmc "topic A" -n 10
paperclip map --from s_xxx "What was the main finding and sample size?"

# 3. Add papers with the claims you'll cite
paperclip repo add PMC123 "Key finding X" --lines L45-L52
paperclip repo add bio_456 "Key finding Y"

# 4. Commit - verifies each claim against full text
paperclip repo commit -m "Initial citations"

# 5. Check results - fix any [X] claims
paperclip repo status
#   [OK] PMC123  claim: Key finding X
#   [X] bio_456 claim: Key finding Y - paper says Z instead

# 6. Fix: remove bad claim, re-add corrected, re-commit
paperclip repo remove bio_456
paperclip repo add bio_456 "Key finding Z" --lines L80
paperclip repo commit -m "Fix bio_456 claim"

# 7. Final check - all [OK], write response
paperclip repo status
```

### Branches

Repos start on `main`. Use branches to explore parallel lines of evidence:

```
paperclip repo branch safety-concerns
paperclip repo add PMC789 "Drug X causes hepatotoxicity in 12%" --lines L200-L210
paperclip repo commit -m "safety claims"

paperclip repo checkout main
# main branch is unaffected; merge when ready:
paperclip repo merge safety-concerns
```

## Sandbox Environment

Commands run in a sandboxed virtual shell (vsh).

**Allowed**: `cd`, `ls`, `cat`, `head`, `tail`, `grep`, `sed`, `awk`, `sort`, `cut`, `tr`, `jq`, `search`, `scan`, and more.
**Blocked**: `rm`, `curl`, `wget`, `ssh`, `sudo`, etc.
**Not supported**: Shell loops (`for`/`while`) and `xargs` - use pipes or multiple tool calls.

### Files and scratch

- `/.gxl/` is writable scratch: `grep "IC50" /papers/<id>/content.lines > /.gxl/hits.txt`
- Save any file locally with `cat > filename`: `cat /papers/PMC123/figures/fig1.jpg > fig1.jpg`
- Supplementary data: `ls /papers/<id>/supplements/` then `head`/`awk`/`cat >`.

## Tips

- Prefer `head -N`, section files, or `grep`/`scan` - avoid `cat` on full `content.lines`.
- Use `bash '...'` for pipes or redirection to `/.gxl/`.
- `map` runs an LLM reader per paper - limit with `-n 5` on search.
- Always check `repo status` before writing your final response.
- Only cite papers marked [OK].