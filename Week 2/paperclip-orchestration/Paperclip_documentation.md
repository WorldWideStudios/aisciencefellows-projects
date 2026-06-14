Note: this is a snapshot of Paperclip's documentation as of my pipeline's v1.0 run dates (early May 2026), reproduced here so the example runs are auditable against the exact docs they used. Paperclip is GXL's product; see paperclip.gxl.ai for current version and docs.



# Paperclip

Search, read, and analyze 11M+ biomedical papers and 150M+ abstracts via CLI, Python SDK, or MCP

## Overview

Paperclip exposes the same corpus through a **command-line interface**, an optional **Python SDK** (`gxl_paperclip`), and **MCP**, allowing for the best tool to fit the task. Terminals and shell pipelines use the CLI; scripts, notebooks, and services often use the SDK; coding agents can use either, depending on environment. Every paper is a directory with full text, sections, figures, and supplements on a virtual filesystem at `/papers/`.

- Search with natural language or regex across 11M+ papers and 150M+ abstracts
- Run subagents to read papers in parallel and return answers to queries
- Pipe results through standard Unix tools (grep, awk, sed, jq, etc.)
- Ask questions over figures
- Query the database directly with SQL

**11M+**Full-text papers**150M+**Abstracts**5 sources**bioRxiv · medRxiv · arXiv · PMC · Abstracts## Installation

Choose the installation method that works best for your setup.

### 1One-line installer recommended

```
curl -fsSL https://paperclip.gxl.ai/install.sh | bash
```

Handles everything: installs to `~/.paperclip/`, signs you in, and installs agent skills.### Verify your setup

```
paperclip config
# Server:  https://paperclip.gxl.ai
# Auth:    ✓ you@example.com
# Config:  ~/.paperclip
```

### Alternative: MCP server

Use Paperclip as an MCP server directly — no local install needed.

When using the MCP server, native CLI commands using `paperclip` are not available.Claude Code1Add the MCP server:

```
claude mcp add --transport http paperclip https://paperclip.gxl.ai/mcp
```

2Start `claude`, enter `/mcp`, and select **Authenticate** under the paperclip server.

Cursor1Add to `~/.cursor/mcp.json` (or `.cursor/mcp.json` in your project):

```
{
  "mcpServers": {
    "paperclip": {
      "url": "https://paperclip.gxl.ai/mcp",
      "type": "http"
    }
  }
}
```

2`Cmd/Ctrl + Shift + P` → **Tools & MCPs**, enable the `paperclip` server, and authenticate.

## Quick Start

```
# Search for papers
paperclip search "CRISPR base editing efficiency"

# Read a paper's metadata
paperclip cat /papers/bio_4f78753a6feb/meta.json

# Preview the first 50 lines
paperclip head -50 /papers/bio_4f78753a6feb/content.lines

# Grep within a single paper
paperclip grep -i "binding affinity" /papers/bio_4f78753a6feb/content.lines

# Grep across the entire corpus
paperclip grep -i "alphamissense" /papers/

# Map over search results with an AI reader
paperclip map --from s_abc123 "What methods were used?"

# Save results to a local file
paperclip search "CRISPR" -n 5 > results.txt
```

Any command works directly as a subcommand. Use `paperclip bash '...'` for pipes and chains:

```
paperclip bash 'search "protein folding" | grep "deep learning"'
```

SearchHybrid search across 11M+ papersMapParallel AI analysis across papersGrepRegex search within or across papersSQLDirect database queriesPaper ReposCurate, annotate, and export collectionsResultsView, export, and manage saved results## Using with Agents

Once installed (via CLI skill or MCP), invoke Paperclip from Claude Code by mentioning `/paperclip` in your prompt. Claude loads the skill automatically and runs commands on your behalf.

```
❯ Using /paperclip, find the relative frequency of methods which use Boltz
vs. Chai models in papers

● Skill(paperclip)
  ⎿  Successfully loaded skill

● I'll search for papers using both Boltz and Chai as structure prediction
  models, then dig into the methods sections.

● Bash(paperclip search "Boltz structure prediction" -n 50 --all 2>&1 | head -60)
  ⎿  Found 29 papers  [s_1cbc742e]

● Bash(paperclip search "Chai-1 structure prediction" -n 50 --all 2>&1 | head -60)
  ⎿  Found 20 papers  [s_0ef54807]
```

You can also run Paperclip commands directly from the terminal alongside Claude:

```
# In your terminal (while Claude Code is running)
paperclip search "GLP-1 receptor agonist efficacy" -n 5
paperclip map --from s_abc123 "What were the primary endpoints?"
paperclip grep -i "hazard ratio" /papers/med_84637b0c77f5/content.lines
```

Claude Code will automatically use `search → map → synthesize` workflows when you ask research questions. The skill teaches it the full command set.## Data sources

Paperclip searches and reads across five sources: the full bioRxiv and medRxiv preprint archives, PubMed Central (PMC) for open-access peer-reviewed literature, arXiv for CS/ML/physics/math preprints, and OpenAlex abstracts for broad scientific coverage. Full-text sources support `search`, `grep`, `cat`, and `sql`. Abstract-only sources support `search` and `sql`.

| Source               | Type           | # Documents | Years        | Updated | Notes                                                        |
| -------------------- | -------------- | ----------- | ------------ | ------- | ------------------------------------------------------------ |
| bioRxiv              | Full text      | ~400K       | 2013–present | Monthly | Preprint server for the biological sciences, operated by Cold Spring Harbor Laboratory. |
| medRxiv              | Full text      | ~100K       | 2019–present | Monthly | Preprint server for the health and clinical sciences.        |
| PubMed Central (PMC) | Full text      | ~7.5M       | All years    | Monthly | Open-access papers only. Includes top journals such as Nature, Science, Cell, NEJM, The Lancet, and more. |
| arXiv                | Full text      | ~3.0M       | 1991–present | Monthly | All arXiv categories. PDFs parsed with state-of-the-art OCR. Use -s arxiv. |
| OpenAlex Abstracts   | Abstracts only | ~50M        | All years    | —       | Title + abstract search only (no full text). Use -s abstracts_only. Useful for broad literature surveys. |

More data sources are coming soon. If you have suggestions for what we should index next, reach out to sy@gxl.ai.

Search and discovery commands use dedicated backends — search indexes, parallel document processing, vision models, and SQL engines. They look and feel like regular shell commands, but each one is powered by specialized infrastructure.

## paperclip search

Search across all sources using hybrid search (Elasticsearch BM25 + vector similarity).```
paperclip search "protein structure prediction" -n 20
paperclip search -e "genome-wide association study"
paperclip search "cancer" --year 2024 --sort date
paperclip search --ranking vector "mechanisms of immune evasion in solid tumors"
paperclip search --ranking bm25 "TP53 R175H mutation"
paperclip search pmc --since 1y "gene therapy"
paperclip search --source biorxiv,pmc "gene therapy"
paperclip search -a "David Baker" -n 20
paperclip search -r "CRISPR.*Cas9"
paperclip search -c "CRISPR"
```

| Parameter | Type | Description |
| --- | --- | --- |
| QUERYrequired | string | Natural language search query (or regex with -r) |
| -n | int= 100 | Number of results (max: 1000) |
| --source | string= all | Filter by source: biorxiv, medrxiv, pmc, arxiv, abstracts_only. Comma-separated for multiple. Also accepted as positional keyword before query. |
| -e, --exact | flag | Exact phrase matching (sets mode to phrase) |
| -m | string= any | Match mode: any, all, 50%, 75%, phrase |
| -r, --regex | flag | Treat query as a regex pattern (uses trigram grep internally) |
| -a, --author | string | Search by author name |
| -t, --title | string | Search by title |
| -c, --count | flag | Count mode — return only the match count, no results |
| -M, --metadata | flag | Search metadata only (not full text) |
| --sort | string= relevance | Sort order: relevance or date |
| --ranking | string= hybrid | Ranking strategy: hybrid, bm25, vector |
| --since | string | Time filter: 30d, 7d, 6m, 1y, etc. |
| --recent | flag | Shorthand for last year |
| --year | string | Filter by publication year (e.g. 2024) |
| --category | string | Filter by subject category (e.g. Neuroscience) |
| --journal | string | Filter by journal name |
| --article-type | string | Filter by article type (e.g. review-article, research-article). PMC only. |
| -T, --type | string | Filter by document type (e.g. youtube, meeting) |
| --tag | string | Tag for result accumulation — multiple searches with the same tag merge results |
| --all | flag | Search full corpus (slower, removes index optimizations) |
| --quiet | flag | Minimal output |
| --json | flag | Return results as JSON |

Every search returns a **results ID** (e.g. `s_1907a2d0`) that can be passed to `map`, `filter`, `reduce`, or `grep --from`.

## paperclip searches

Run multiple search queries in parallel and merge results.```
# Run three searches in parallel
paperclip searches "CRISPR delivery" "gene editing cancer" "viral vectors"

# Tag results for accumulation across calls
paperclip searches --quiet --tag crispr "CRISPR delivery" "gene editing cancer"

# All results accumulated into: s_abc123  [tag: crispr]  (58 unique papers)
```

| Parameter       | Type     | Description                                               |
| --------------- | -------- | --------------------------------------------------------- |
| QUERIESrequired | string[] | One or more search queries (quoted strings)               |
| -n              | int= 50  | Limit per search (max: 1000)                              |
| -m              | string   | Match mode: any, all, 50%, 75%, phrase                    |
| -e, --exact     | flag     | Exact phrase matching                                     |
| --recent        | flag     | Limit to recent papers                                    |
| --quiet         | flag     | Minimal output — only the accumulated count and result ID |
| --tag           | string   | Tag for result accumulation                               |

## paperclip lookup

Look up papers by a specific metadata field.```
paperclip lookup doi 10.1101/2024.01.15.575556
paperclip lookup author "David Baker" -n 10
paperclip lookup title "CRISPR base editing"
paperclip lookup pmc PMC7194329
paperclip lookup pmid 32943797
paperclip lookup arxiv 2403.03507
paperclip lookup journal "Nature Medicine"
paperclip lookup keywords "CRISPR"
paperclip lookup year 2024
paperclip lookup type review-article
```

| Parameter | Type | Description |
| --- | --- | --- |
| FIELDrequired | string | Field to search (see below) |
| VALUErequired | string | Value to look up |
| -n | int= 25 | Max results |

### Available fields

| Parameter | Type | Description |
| --- | --- | --- |
| doi | TEXT | Digital Object Identifier |
| title | TEXT | Paper title |
| author | TEXT | Author name |
| abstract | TEXT | Abstract text |
| source | TEXT | biorxiv, medrxiv, pmc, arxiv, or openalex |
| month_year, date | TEXT | Publication date (bioRxiv/medRxiv) |
| pmc | TEXT | PMC ID (e.g. PMC7194329). PMC only. |
| pmid | TEXT | PubMed ID. PMC only. |
| journal | TEXT | Journal name. PMC only. |
| publisher | TEXT | Publisher name. PMC only. |
| type | TEXT | Article type (e.g. review-article). PMC only. |
| keywords | TEXT | Keywords. PMC only. |
| category | TEXT | Subject categories. PMC only. |
| license | TEXT | License type. PMC only. |
| year | TEXT | Publication year. PMC only. |
| volume, issue, issn | TEXT | Journal volume, issue, ISSN. PMC only. |

## paperclip grep

Regex search within a paper or across the entire corpus. Corpus-wide grep uses a trigram index — sub-second across 11M+ documents.```
# Corpus-wide regex search
paperclip grep -i "crispr\|cas9" /papers/

# Within a single paper
paperclip grep -i "binding" /papers/bio_4f78753a6feb/content.lines

# Show context lines
paperclip grep -i -C 2 "p53 mutation" /papers/bio_4f78753a6feb/content.lines

# Within a search result set
paperclip grep --from s_abc123 "kinase"

# Multiple patterns (OR'd together)
paperclip grep -e "CRISPR" -e "Cas9" /papers/bio_4f78753a6feb/content.lines
```

| Parameter       | Type   | Description                                                  |
| --------------- | ------ | ------------------------------------------------------------ |
| PATTERNrequired | string | Regex pattern (or use -e for multiple)                       |
| PATH            | string | /papers/ for corpus-wide, or /papers/<id>/file.lines for single paper |
| -i              | flag   | Case-insensitive matching                                    |
| -n              | flag   | Show line numbers                                            |
| -c              | flag   | Count matches only                                           |
| -v              | flag   | Invert match (show non-matching lines)                       |
| -o              | flag   | Print only the matching part of lines                        |
| -w              | flag   | Match whole words only                                       |
| -l              | flag   | List only filenames with matches                             |
| -h              | flag   | Suppress filename prefix                                     |
| -F              | flag   | Fixed strings (literal match, no regex)                      |
| -e PATTERN      | string | Explicit pattern (repeatable for multi-pattern OR)           |
| -m NUM          | int    | Stop after NUM matches                                       |
| -A NUM          | int    | Show NUM lines after each match                              |
| -B NUM          | int    | Show NUM lines before each match                             |
| -C NUM          | int    | Show NUM lines of context (before and after)                 |
| --from          | string | Grep within a search result set (e.g. --from s_abc123)       |

## paperclip scan

Multi-pattern grep — search for several keywords in a single pass, results grouped by pattern.```
paperclip scan /papers/bio_4f78753a6feb/content.lines "AAV" "efficiency" "in vivo"
paperclip scan -i -C 3 /papers/bio_4f78753a6feb/content.lines "p53" "MDM2"
```

| Parameter | Type | Description |
| --- | --- | --- |
| FILErequired | string | Path to the file to scan |
| PATTERNSrequired | string[] | One or more patterns (quoted strings) |
| -i | flag | Case-insensitive matching |
| -C NUM | int= 5 | Lines of context per match |

`scan` is faster than running multiple `grep` calls — it reads the file once and matches all patterns in a single pass.## paperclip sql

Run read-only SQL queries against the unified papers database.```
# Count papers by source
paperclip sql "SELECT source, COUNT(*) FROM documents GROUP BY source"

# Find papers by author
paperclip sql "SELECT title, doi, source FROM documents WHERE authors ILIKE '%Doudna%' LIMIT 5"

# Top journals (PMC papers)
paperclip sql "SELECT journal_title, COUNT(*) c FROM documents WHERE source = 'pmc' GROUP BY 1 ORDER BY c DESC LIMIT 10"

# Recent papers about a topic
paperclip sql "SELECT title, doi, pub_date FROM documents WHERE abstract_text ILIKE '%CRISPR%' ORDER BY pub_date DESC LIMIT 10"
```

| Parameter     | Type        | Description                                                  |
| ------------- | ----------- | ------------------------------------------------------------ |
| QUERYrequired | string      | SQL SELECT statement                                         |
| --source, -s  | string= all | Filter by source: biorxiv, medrxiv, pmc, arxiv, abstracts_only |

Only `SELECT` on the `documents` table is allowed. 15-second timeout, 200-row limit.

### Schema: documents

| Parameter     | Type      | Description                                         |
| ------------- | --------- | --------------------------------------------------- |
| id            | TEXT      | Paper identifier                                    |
| title         | TEXT      | Paper title                                         |
| doi           | TEXT      | Digital Object Identifier                           |
| authors       | TEXT      | Comma-separated author list                         |
| source        | TEXT      | 'biorxiv', 'medrxiv', 'pmc', 'arxiv', or 'openalex' |
| abstract_text | TEXT      | Paper abstract                                      |
| pub_date      | TEXT      | Publication date (text)                             |
| journal_title | TEXT      | Journal name. PMC only.                             |
| article_type  | TEXT      | e.g. research-article, review-article. PMC only.    |
| pmid          | TEXT      | PubMed ID. PMC only.                                |
| keywords      | JSONB     | Array of keywords. PMC only.                        |
| categories    | JSONB     | Array of subject categories. PMC only.              |
| pub_year      | INT       | Publication year. PMC only.                         |
| created_at    | TIMESTAMP | When the record was indexed                         |

PMC-only columns are NULL for bioRxiv/medRxiv papers. Use `WHERE source = 'pmc'` when querying these fields.## paperclip export

Export SQL query results to CSV and a table artifact (up to 1,000 rows).```
paperclip export "SELECT title, doi, authors FROM documents WHERE source = 'biorxiv' ORDER BY created_at DESC LIMIT 100"

paperclip export --desc "CRISPR papers 2024" "SELECT DISTINCT d.title, d.doi FROM documents d JOIN content_blocks cb ON d.document_id = cb.document_id WHERE cb.content ILIKE '%CRISPR%' AND d.month_year >= '2024-01'"
```

| Parameter | Type | Description |
| --- | --- | --- |
| QUERYrequired | string | SQL SELECT or WITH statement |
| --desc | string | Description for the export |

The `export` command has access to additional tables beyond `documents`: `content_blocks` (id, document_id, line_number, content, section, block_type) and `figures` (document_id, graphic, source_path). Up to 1,000 rows.

## paperclip map

Run parallel AI reader tasks over multiple papers from a search result.Each paper gets read in full by an LLM that extracts the information you ask for. Results are returned with per-paper answers.

Typical workflow: `search` → `map` → synthesize from results.

Step 1 — Searchbash```
# Step 1: search for papers
$ paperclip search "AAV gene therapy delivery" -n 3

Found 3 papers  [s_1907a2d0]

  1. Covalently linked adenovirus-AAV complexes as a novel
     platform technology for gene therapy
     Logan Thrasher Collins, Wandy Beatty, et al.
     bio_f402e4cf6e4a · bioRxiv · 2024-08-21

  2. Myocardial infarction creates a critical time window
     for AAV gene therapy
     Gonglie Chen, Yueyang Zhang, et al.
     bio_f2997a136fe7 · bioRxiv · 2024-06-10

  3. A facile chemical strategy to synthesize precise
     AAV-protein conjugates for targeted gene delivery
     Quan Pham, Jake Glicksman, et al.
     bio_ea44a956784e · bioRxiv · 2024-07-20

[197ms, saved to s_1907a2d0]
```

Step 2 — Mapbash```
# Step 2: map over those results
$ paperclip map --from s_1907a2d0 \
    "What delivery vector was used and what transduction efficiency was reported?"

Map complete: 3/3 papers

  ✓ Covalently linked adenovirus-AAV complexes as a novel platform...
    The study used covalently linked adenovirus-AAV (Ad-AAV) complexes.
    In vitro, approximately 80% transduction in HEK293 cells.

  ✓ Myocardial infarction creates a critical time window for AAV...
    The study utilized AAV9. Transduction efficiency: 32.4 ± 4.5% at
    1 day post-MI vs 16.2 ± 3.1% in sham controls.

  ✓ A facile chemical strategy to synthesize precise AAV-protein...
    AAV2-HER2 conjugates for targeted delivery to HER2+ cancer cells.
    Explicit transduction efficiency percentages were not provided.
```

| Parameter | Type | Description |
| --- | --- | --- |
| QUERYrequired | string | Question applied to every paper |
| --from | string | Results ID from a previous search (s_xxx). If omitted, uses the last search result. |
| --output_schema | string | JSON schema for structured output per paper |
| --limit | int | Max number of papers to process |
| --offset | int | Skip first N papers in the result set |

Keep search results to 3–10 papers for fast map execution. Use `-n 5` on your search to limit the set. The map command shows a live progress bar during execution.## paperclip reduce

Synthesize results from a map operation into a structured summary.```
# Summarize map results
paperclip reduce --from m_a83650c0 --strategy summarize "What delivery methods are most common?"

# Generate a table
paperclip reduce --from m_a83650c0 --strategy table --columns "Paper,Vector,Efficiency"

# Extract themes
paperclip reduce --from m_a83650c0 --strategy themes
```

| Parameter      | Type              | Description                                                  |
| -------------- | ----------------- | ------------------------------------------------------------ |
| --fromrequired | string            | Map results ID (m_xxx)                                       |
| --strategy     | string= summarize | Synthesis strategy: summarize, table, themes, consensus, bullet_points, extract |
| QUESTION       | string            | Optional guiding question for the synthesis                  |
| --columns      | string            | Comma-separated column names (for table strategy)            |
| --fields       | string            | Comma-separated field names to extract                       |
| --limit, --max | int               | Max items to include                                         |

## paperclip filter

Filter search results for relevance to a specific query, removing off-topic papers.```
# Filter results — removes irrelevant papers
paperclip filter --from s_abc123 "AAV delivery to the lung"

# Require at least N papers to pass (exit code 1 if fewer survive)
paperclip filter --from s_abc123 --require 5 "AAV delivery to the lung"
```

| Parameter | Type | Description |
| --- | --- | --- |
| --fromrequired | string | Results ID to filter (s_xxx) |
| QUERYrequired | string | The user's original query (used to judge relevance) |
| --require N | int | Fail (exit code 1) if fewer than N papers survive. Filtered results are still saved. |

Previously-evaluated papers are cached — re-running filter after adding new search results only evaluates new papers.

## paperclip ask-image

Analyze figures from papers using vision AI. Requires a paper directory context.```
# List available figures for a paper
paperclip bash 'cd /papers/bio_4f78753a6feb/ && ask_image --list'

# Describe a figure (default question)
paperclip bash 'cd /papers/bio_4f78753a6feb/ && ask_image fig1.tif'

# Ask a specific question about a figure
paperclip bash 'cd /papers/bio_4f78753a6feb/ && ask_image fig1.tif "What does this figure show?"'

# Analyze multiple figures
paperclip bash 'cd /papers/bio_4f78753a6feb/ && ask_image fig1.tif fig2.tif "Compare these"'

# First, list figures to see what's available
paperclip ls /papers/bio_4f78753a6feb/figures/
```

| Parameter         | Type                                      | Description                                        |
| ----------------- | ----------------------------------------- | -------------------------------------------------- |
| FIGURE_IDrequired | string                                    | Figure filename (e.g. fig1.tif, 657517v1_fig1.tif) |
| QUESTION          | string= "Describe this figure in detail." | Question about the image                           |
| --list            | flag                                      | List available figures for the current paper       |

`ask-image` requires being inside a paper directory. From the CLI, wrap with `paperclip bash 'cd /papers/ID/ && ask_image ...'`. When used via MCP, the agent's session maintains the working directory automatically.## paperclip cat

Read file contents from the paper filesystem. Large files are automatically truncated with a section index.```
# Read metadata
paperclip cat /papers/bio_4f78753a6feb/meta.json

# Read full text (first 100 lines by default)
paperclip cat /papers/bio_4f78753a6feb/content.lines

# Read with line numbers
paperclip cat -n /papers/bio_4f78753a6feb/content.lines

# Read first N lines
paperclip cat --lines 50 /papers/bio_4f78753a6feb/content.lines

# Read a specific line range
paperclip cat --lines 100-200 /papers/bio_4f78753a6feb/content.lines

# Read a specific section
paperclip cat /papers/bio_4f78753a6feb/sections/Methods.lines
```

| Parameter | Type | Description |
| --- | --- | --- |
| FILErequired | string | Path to the file to read |
| -n | flag | Show line numbers |
| --lines N | int | Show first N lines (overrides the 100-line default) |
| --lines N-M | range | Show lines N through M |

For large files, `cat` automatically shows the first 100 lines plus a section index. Use `head`, `grep`, or `scan` for more targeted reads.

## paperclip head / tail

Display the first or last lines of a file.```
paperclip head -50 /papers/bio_4f78753a6feb/content.lines
paperclip tail -20 /papers/bio_4f78753a6feb/content.lines

# Short form (equivalent)
paperclip head -n 50 /papers/bio_4f78753a6feb/content.lines
```

| Parameter    | Type    | Description             |
| ------------ | ------- | ----------------------- |
| FILErequired | string  | Path to the file        |
| -n N or -N   | int= 10 | Number of lines to show |

## paperclip ls

List directory contents in the paper filesystem.```
paperclip ls /papers/bio_4f78753a6feb/
# meta.json  content.lines  sections/  figures/  supplements/

paperclip ls /papers/bio_4f78753a6feb/sections/
# Introduction.lines  Methods.lines  Results.lines  Discussion.lines

# Long format with token estimates
paperclip ls -l /papers/bio_4f78753a6feb/
```

| Parameter | Type | Description |
| --- | --- | --- |
| PATH | string= current directory | Directory to list |
| -l | flag | Long format (shows permissions, token estimates, titles) |
| -a | flag | Show all entries (including hidden) |

## paperclip tree

Display a directory tree.```
paperclip tree /papers/bio_4f78753a6feb/
paperclip tree -L 2 /papers/bio_4f78753a6feb/
```

| Parameter   | Type                      | Description          |
| ----------- | ------------------------- | -------------------- |
| PATH        | string= current directory | Directory to display |
| -L, --depth | int= 3                    | Maximum depth        |

## paperclip wc

Count lines, words, or characters in paper files.```
paperclip wc -l /papers/bio_4f78753a6feb/content.lines
#      847 /papers/bio_4f78753a6feb/content.lines

paperclip wc -w /papers/bio_4f78753a6feb/content.lines
```

| Parameter | Type | Description |
| --- | --- | --- |
| FILErequired | string | File to count |
| -l | flag | Count lines |
| -w | flag | Count words |
| -c, -m | flag | Count characters |

With no flags, all three counts are shown.

## paperclip cd / pwd

Navigate the virtual filesystem within `bash` chains. Entering a paper directory shows a summary with title and token count.```
# cd + command chain (cd only persists within the bash call)
paperclip bash 'cd /papers/bio_4f78753a6feb/ && ls'
paperclip bash 'cd /papers/bio_4f78753a6feb/ && ask_image --list'
paperclip bash 'cd /papers/bio_4f78753a6feb/ && grep -i "kinase" content.lines'
```

`~` expands to `/papers`. From the CLI, `cd` is useful inside `paperclip bash '...'` chains to set context for commands that need a paper directory (like `ask_image`). When Paperclip is used as an MCP server, the agent's session maintains directory state across calls automatically.

## paperclip sort / uniq / cut / tr

Standard text processing utilities, available as subcommands or in pipes.```
# Sort, reverse, numeric, unique
paperclip bash 'grep "kinase" /papers/bio_abc123/content.lines | sort -u'

# Cut specific fields
paperclip bash 'grep "gene" /papers/bio_abc123/content.lines | cut -d: -f2'

# Translate characters
paperclip bash 'head -10 /papers/bio_abc123/content.lines | tr A-Z a-z'
```

| Parameter | Type | Description |
| --- | --- | --- |
| sort | cmd | -r reverse, -n numeric, -u unique |
| uniq | cmd | -c count occurrences, -d only duplicates, -u only unique |
| cut | cmd | -d delimiter, -f field numbers |
| tr | cmd | -d delete chars, -s squeeze repeats, or two charsets for translate |

## paperclip sed

Stream editor (limited subset). Supports address ranges, substitution, and line deletion.```
# Extract lines 50-100
paperclip sed -n '50,100p' /papers/bio_4f78753a6feb/content.lines

# Substitution
paperclip bash 'head -20 /papers/bio_abc123/content.lines | sed "s/CRISPR/crispr/g"'

# Delete matching lines
paperclip bash 'cat /papers/bio_abc123/content.lines | sed "/^$/d"'
```

| Parameter          | Type   | Description                                          |
| ------------------ | ------ | ---------------------------------------------------- |
| EXPRESSIONrequired | string | sed expression (s///, N,Mp, /pattern/d, /pattern/!d) |
| FILE               | string | Input file (or pipe via stdin)                       |
| -n                 | flag   | Suppress default output (print only with p)          |

## paperclip awk

Pattern processing (limited subset).```
# Print Nth field
paperclip bash 'grep "kinase" /papers/bio_abc123/content.lines | awk "{print \$2}"'

# Custom delimiter
paperclip bash 'grep "kinase" /papers/bio_abc123/content.lines | awk -F: "{print \$1}"'

# Print matching lines (like grep)
paperclip bash 'cat /papers/bio_abc123/content.lines | awk "/kinase/"'

# Line range
paperclip bash 'cat /papers/bio_abc123/content.lines | awk "NR>=5 && NR<=10"'
```

| Parameter | Type | Description |
| --- | --- | --- |
| PROGRAMrequired | string | Supported: /pattern/, /start/,/end/, {print $N}, NR>=N && NR<=M, {print NR, $0} |
| -F | string= whitespace | Field delimiter |

## paperclip jq

Minimal JSON query tool. Supports dot-path access, keys, and length.```
paperclip bash 'cat /papers/bio_4f78753a6feb/meta.json | jq .title'
paperclip bash 'cat /papers/bio_4f78753a6feb/meta.json | jq keys'
```

| Parameter      | Type   | Description                                   |
| -------------- | ------ | --------------------------------------------- |
| FILTERrequired | string | jq filter: ., .key, .key.subkey, keys, length |

## Pipes & bash

For compound expressions (pipes, `&&`, chains), wrap in `paperclip bash '...'`. Single commands don't need this wrapper.```
# Count grep matches
paperclip bash 'grep -ic "p53" /papers/bio_4f78753a6feb/content.lines'

# Chain search → grep
paperclip bash 'search "CRISPR delivery" -n 10 | grep "AAV"'

# Write results to scratch space
paperclip bash 'grep -i "kinase" /papers/ > /.gxl/kinase_hits.txt'

# Multi-step pipeline
paperclip bash 'head -100 /papers/bio_abc123/content.lines | grep -i "method" | wc -l'
```

Inside `bash`, you can use any allowlisted command without the `paperclip` prefix. Pipes (`|`) and chains (`&&`) work as expected.

Python is also available via `paperclip python "print(2+2)"` or `paperclip python3 script.py`, executed in a sandboxed environment.## paperclip results

View, browse, and export saved search and map results.Every `search`, `lookup`, and `map` command saves its output with a result ID. Use `results` to access them later.

```
# Interactive picker (arrow keys to navigate, enter to save)
paperclip results

# View a specific result
paperclip results s_4a2b61f6

# View a map result
paperclip results m_ec2c9cc9

# Non-interactive list
paperclip results --list

# Export to CSV
paperclip results s_4a2b61f6 --save results.csv

# Export to plain text
paperclip results s_4a2b61f6 --save results.txt
```

| Parameter | Type | Description |
| --- | --- | --- |
| RESULT_ID | string | Specific result to view (s_xxx for search, m_xxx for map) |
| --list | flag | Non-interactive list of all saved results |
| --save PATH | string | Export to file. .csv exports structured data; other extensions export plain text. |

With no arguments, `paperclip results` opens an interactive TUI picker where you can navigate with arrow keys, paginate with n/p, and press enter to select and save.## Redirection

Append `>` to any Paperclip command to save its output to a local file.Standard shell redirection captures command output to your local filesystem.

```
# Save search results locally
paperclip search "CRISPR delivery" -n 10 > crispr_results.txt

# Save a paper's metadata
paperclip cat /papers/bio_4f78753a6feb/meta.json > meta.json

# Save SQL query output
paperclip sql "SELECT title, doi FROM documents WHERE authors ILIKE '%Doudna%' LIMIT 20" > doudna_papers.txt

# Append to an existing file
paperclip search "protein folding" >> research_log.txt

# Download a figure
paperclip cat /papers/bio_abc123/figures/fig1.tif > fig1.tif
```

When `cat` encounters a binary file (image/figure), Paperclip generates a short-lived signed URL and streams the bytes directly — no intermediate text encoding.

Paper repositories add git-like version control for curated literature collections. Build annotated, exportable bibliographies with branching, diffing, and a full audit trail.

## Paper Repos

Paper repos let you build versioned, annotated collections of papers. Each repo tracks which papers you've added, your annotations and research notes, and a full commit history — like git for literature review.

- Curate papers into named collections with add and remove
- Seed from a paper's bibliography with import
- Annotate papers with inline notes
- Commit snapshots with reasoning messages
- Branch for sub-topics, merge when ready
- Export to BibTeX, RIS, Markdown, or CSV
- Review with diff, log, and status

**Git-like**Commits, branches, diffs**Annotated**Per-paper & repo-level notes**Exportable**BibTeX · RIS · Markdown · CSV## paperclip init / checkout

Create, list, and switch between paper repositories.```
# Create a new repository
paperclip init kras-resistance "KRAS G12C resistance mechanisms"

# List all repositories
paperclip checkout

# Switch to a repository (all subsequent commands are scoped to it)
paperclip checkout kras-resistance

# Deactivate the current repo (back to global context)
paperclip checkout -
```

| Parameter         | Type   | Description                                              |
| ----------------- | ------ | -------------------------------------------------------- |
| init NAMErequired | string | Create a new repo with the given name                    |
| init DESCRIPTION  | string | Optional description for the repo                        |
| checkout          | cmd    | List all repositories with descriptions and paper counts |
| checkout NAME     | string | Switch to a repo or branch                               |
| checkout -        | flag   | Deactivate the current repo                              |

Always check `paperclip checkout` before creating a new repo — if one already covers your topic, reuse it or branch from it.## paperclip add / remove / import

Add papers to a repo manually, remove them, or seed from a bibliography.```
# Add specific papers by ID
paperclip add PMC123 bio_456

# Add with an inline annotation
paperclip add PMC123 --note "Key review on bypass mechanisms"

# Remove a paper
paperclip remove PMC789
```

| Parameter | Type | Description |
| --- | --- | --- |
| add ID [ID...]required | string | One or more paper IDs to add |
| --note | string | Annotation to attach when adding |
| remove ID | string | Remove a paper from the repo |

### Seed from a paper's references

Use `import` to bootstrap a repo from any paper's reference list. It fetches references via Semantic Scholar, matches them against the 11M+ corpus, and adds the matches.

```
# Import all matchable references
paperclip import PMC11271413

# Only highly-cited references
paperclip import PMC11271413 --min-cites 50

# Preview without adding
paperclip import PMC11271413 --dry-run

# Provide the DOI explicitly (speeds up lookup)
paperclip import PMC11271413 --doi 10.1038/s41591-024-03015-5
```

| Parameter | Type | Description |
| --- | --- | --- |
| PAPER_IDrequired | string | Paperclip ID of the source paper (e.g. PMC11271413) |
| --doi | string | Explicit DOI for the paper (skips DOI resolution) |
| --min-cites | int | Only import references with at least N citations |
| --limit | int | Max number of references to import |
| --dry-run | flag | Show matches without adding to the repo |

Use `import` on a review article to quickly bootstrap a repo. Review articles typically cite 50-100+ papers, many of which will match in the corpus.## paperclip annotate

Pin notes to specific papers in the repo.```
# Annotate a paper (appends — doesn't overwrite)
paperclip annotate PMC123 "Key RCT, only spleen-targeting LNP data"

# Pin an annotation to specific lines in content.lines
paperclip annotate PMC123 "IL-9→STAT3→CPT1A pathway described here" -L L412
paperclip annotate PMC123 "SHP2 IC50 data table" -L L100-L150
```

| Parameter        | Type   | Description                                                |
| ---------------- | ------ | ---------------------------------------------------------- |
| PAPER_IDrequired | string | Paper to annotate                                          |
| TEXTrequired     | string | Annotation text                                            |
| -L               | string | Pin to a line (L412) or range (L100-L150) in content.lines |

## paperclip commit / repo / log

Snapshot the repo state with commit messages, view repo overview, and browse history.```
# Commit with a reasoning message
paperclip commit -m "Seed: core papers on KRAS G12C resistance"
paperclip commit -m "Added combination therapy data; still missing phase-3"

# List all repos
paperclip repo

# Repo overview: papers, branches, annotations
paperclip repo <name>

# Commit history
paperclip log
paperclip log -n 5    # last 5 commits
```

| Parameter | Type | Description |
| --- | --- | --- |
| commit -m MSGrequired | string | Commit message explaining what changed and why |
| status | cmd | Show repo state: papers, branches, annotations, and recent searches |
| log | cmd | Show commit history |
| log -n N | int | Show only the last N commits |

The `status` command shows the active repo's working state: paper count, branch info, annotations, and recent search activity. Use `config` for connection diagnostics.

## paperclip diff

Compare snapshots across commits or branches.```
# Compare two commits
paperclip diff 9a6d1e13..559a31ba

# Compare branches
paperclip diff main..parkinsons
```

| Parameter        | Type   | Description                                       |
| ---------------- | ------ | ------------------------------------------------- |
| REF..REFrequired | string | Two commit hashes or branch names separated by .. |

Diff shows papers added and removed between the two references. Use `log` to view commit history with messages.

## paperclip export (repo)

Export your curated repo to BibTeX, RIS, Markdown, or CSV. Annotations are included.```
# BibTeX — annotations appear in the note field
paperclip export bib -o references.bib

# RIS — importable by Zotero, Paperpile, Mendeley, EndNote
paperclip export ris -o references.ris

# Structured Markdown report
paperclip export md -o review.md

# CSV — tabular data for spreadsheets
paperclip export csv -o papers.csv
```

| Parameter | Type | Description |
| --- | --- | --- |
| FORMATrequired | string | Export format: bib, ris, md, csv |
| -o FILE | string | Output file path. If omitted, prints to stdout. |

BibTeX and RIS exports include your annotations in each entry's note field, so your research notes travel with the references into any reference manager.## paperclip branch / merge

Branch for sub-topics, merge when ready. Each branch has its own paper set and annotations.```
# Create and switch to a new branch
paperclip checkout -b clinical-data

# List branches
paperclip branch

# Work on the branch
paperclip search "KRAS clinical trial" -n 10
paperclip add PMC789
paperclip commit -m "Added CodeBreaK and KRYSTAL phase-2 trial data"

# Switch back to main and merge
paperclip checkout main
paperclip merge clinical-data
```

| Parameter        | Type   | Description                            |
| ---------------- | ------ | -------------------------------------- |
| checkout -b NAME | string | Create and switch to a new branch      |
| branch           | cmd    | List branches in the current repo      |
| merge BRANCH     | string | Merge a branch into the current branch |

Use branches for tangents and sub-topics. Keep `main` clean. Each branch can be exported independently with `export bib`.## Authentication

Paperclip can authenticate with **OAuth** (browser sign-in) or an **API key** for non-interactive use. OAuth credentials live at `~/.paperclip/credentials.json` and refresh automatically. API keys are never written to disk by the CLI; pass them per run or via an environment variable (see API keys).

```
paperclip login     # opens browser for sign-in (OAuth)
paperclip config    # check server URL + OAuth status (do not pass --api-key)
paperclip logout    # clear OAuth credentials and local config
```

For servers, CI, or any environment without a browser, set `PAPERCLIP_API_KEY` or use the global `--api-key` flag before the subcommand:

```
export PAPERCLIP_API_KEY='gxl_...'
paperclip search "CRISPR delivery" -n 5

# Equivalent one-off:
paperclip --api-key 'gxl_...' search "CRISPR delivery" -n 5
```

The `login` and `config` commands only apply to OAuth and local settings; do not pass `--api-key` to them.## API keys

Create, rotate, and revoke keys from the Paperclip web app: API keys. The CLI sends the key on every request as the `X-API-Key` header.

### Ways to provide the key

- Environment variable — PAPERCLIP_API_KEY (recommended for scripts and CI).
- Global flag — paperclip --api-key KEY ... or paperclip --api-key=KEY ... before the subcommand.
- For passthrough filesystem commands (e.g. grep, cat), --api-key may also appear after the subcommand; the CLI strips it before running the remote command.

```
# CI / production job
export PAPERCLIP_API_KEY="$SECRET"
paperclip search "gene therapy" -n 20

# Ad-hoc (avoid shell history: prefer env or a secret store)
paperclip --api-key "$PAPERCLIP_API_KEY" grep -i "AAV" /papers/
```

If neither OAuth credentials nor an API key is available and stdin is not a TTY, the CLI exits with an error — set `PAPERCLIP_API_KEY` or run `paperclip login` on a machine with a browser.### MCP server with API key

To authenticate the MCP server in Cursor (or any MCP client that supports headers), add an `X-API-Key` header to your `mcp.json`:

```
{
  "mcpServers": {
    "paperclip": {
      "url": "https://paperclip.gxl.ai/mcp",
      "type": "http",
      "headers": {
        "X-API-Key": "gxl_your_api_key_here"
      }
    }
  }
}
```

## Config

Configuration is stored in `~/.paperclip/config.json`.

```
paperclip config                              # show current config
paperclip config --url http://localhost:8002   # set server URL (local dev)
```

| Parameter            | Type              | Description                                                  |
| -------------------- | ----------------- | ------------------------------------------------------------ |
| --url                | string            | Set the server base URL                                      |
| --show               | flag              | Show current configuration (default when no flags)           |
| PAPERCLIP_BASE_URL   | env               | Env var to override the server base URL                      |
| PAPERCLIP_API_KEY    | env               | API key for non-interactive auth (same as global --api-key); not stored locally by the CLI |
| PAPERCLIP_CONFIG_DIR | env= ~/.paperclip | Env var to override the config directory                     |

## Skill Install

Install the Paperclip skill so your coding agent (Claude Code, Codex, Cursor) knows how to use Paperclip automatically.

```
# Via the CLI (interactive agent picker)
paperclip install

# Install to a specific project directory
paperclip install --dir /path/to/project

# Via npm/npx (no Python required)
npx gxl-paperclip
npx gxl-paperclip --all      # skip interactive prompt
npx gxl-paperclip --cursor   # Cursor only
```

The skill file is fetched from the server and stays up to date. It also auto-refreshes on `paperclip login`.## Update

Update Paperclip to the latest version. The CLI also performs silent background update checks (every 4 hours).

```
paperclip update
# Current version: 0.3.0
# Checking for updates...
# ✓ Already up to date (v0.3.0)
```

If an update is available, `paperclip` (with no arguments) will show a hint in the dashboard.

## Filesystem Layout

Each paper lives at `/papers/<id>/` with the following structure:

```
meta.json        — title, authors, doi, date, abstract, journal (JSON)
content.lines    — full text, line-numbered: L<n>: <text>
sections/        — named section files (Introduction.lines, Methods.lines, …)
figures/         — figure files (PMC papers)
supplements/     — supplementary files (PMC papers)
```

Paper IDs use prefixes by source:

- bio_ — bioRxiv papers
- med_ — medRxiv papers
- PMC — PubMed Central papers (e.g. PMC12345678)

**Scratch space:** `/.gxl/` is a writable directory for session files, map outputs, and temporary data.

`content.lines` files can be very long. Always use `head -N` to paginate rather than `cat` for large papers.## Python SDK · Overview

The `gxl-paperclip` package ships a Python SDK alongside the CLI. Installing it gives you both the `paperclip` command and the `gxl_paperclip` module.

Use the SDK when you want typed Python APIs, structured return values, and programmatic control flow (scripts, tests, notebooks, backend jobs). Use the CLI when you want interactive exploration, shell composition, or the same invocations you would run in a terminal. Neither is “for humans” or “for agents” exclusively — choose by task.

The SDK is a thin, typed wrapper around the same endpoints the CLI uses. Typed methods take Pythonic keyword arguments and return structured result objects instead of printing raw strings.

## Install & authenticate

The SDK authenticates with **API keys**. Mint one from the dashboard and expose it as an env var:

```
export PAPERCLIP_API_KEY="pk_..."
```

```
from gxl_paperclip import PaperclipClient, APIKeyAuth

client = PaperclipClient.from_env()              # reads PAPERCLIP_API_KEY
# — or pass an explicit strategy —
client = PaperclipClient(auth=APIKeyAuth("pk_..."))
```

`PaperclipClient.from_env()` falls back to the credentials saved by `paperclip login` (`~/.paperclip/credentials.json`) when no API key env var is set — handy on a workstation where you've already signed in. OAuth is CLI-focused; programmatic users should use an API key.## Python SDK · Quick start

```
from gxl_paperclip import PaperclipClient

client = PaperclipClient.from_env()

result = client.search("CRISPR lipid nanoparticle", limit=5, source="pmc")
print(result.output)        # same formatted text the CLI prints
print(result.result_id)     # e.g. "s_14bebc10" — pass to map_()

for event in client.map_("What delivery methods were used?", from_results=result.result_id):
    if event.type == "progress":
        print(f"{event.completed}/{event.total} papers done")
    else:
        print(event.output)
```

Every optional kwarg defaults to `None` (or `False` for boolean flags). Leaving it unset means the flag is omitted and the *server-side default* applies. The tables below list each server-side default.## client.search()

```
client.search(
    query: str,
    *,
    limit: int | None = None,
    source: str | None = None,
    exact: bool = False,
    since: str | None = None,
    sort: str | None = None,
    author: str | None = None,
    journal: str | None = None,
    year: int | str | None = None,
    type: str | None = None,
    category: str | None = None,
    mode: str | None = None,
    all: bool = False,
    timeout: float | None = None,
) -> ExecuteResult
```

| Parameter     | Type                   | Description                                                  |
| ------------- | ---------------------- | ------------------------------------------------------------ |
| queryrequired | str                    | Natural-language search query.                               |
| limit         | int= 100 (max 1000)    | Max results returned by the server.                          |
| source        | str= all sources       | Filter by source: "pmc", "biorxiv", "medrxiv", or a comma-separated list. |
| exact         | bool= False            | When True, the server switches search mode to phrase matching. |
| since         | str= no recency filter | Recency window like "7d", "30d", "6m", "1y".                 |
| sort          | str= "relevance"       | Pass "date" for newest-first ordering.                       |
| author        | str= no filter         | Author name substring match.                                 |
| journal       | str= no filter         | Journal name (PMC only).                                     |
| year          | int                    | str= no filter                                               |
| type          | str= no filter         | PMC article type, e.g. "review-article".                     |
| category      | str= no filter         | bioRxiv category, e.g. "Neuroscience".                       |
| mode          | str= "any"             | Term match mode: "any", "all", "50%", "75%".                 |
| all           | bool= False            | When True, searches the full corpus instead of the recency-weighted slice. |
| timeout       | float= 120 s           | Client timeout in seconds.                                   |

## client.lookup()

```
client.lookup(
    field: str,
    value: str,
    *,
    limit: int | None = None,
    timeout: float | None = None,
) -> ExecuteResult
```

Look up papers by a metadata field — `doi`, `pmc`, `pmid`, `author`, `title`, `journal`, `year`, `keywords`, and more. Match is partial and case-insensitive.

| Parameter     | Type         | Description                |
| ------------- | ------------ | -------------------------- |
| fieldrequired | str          | Metadata field to search.  |
| valuerequired | str          | Value to match.            |
| limit         | int= 25      | Max results.               |
| timeout       | float= 120 s | Client timeout in seconds. |

## client.sql()

```
client.sql(
    query: str,
    *,
    source: str | None = None,
    timeout: float | None = None,
) -> ExecuteResult
```

Read-only SQL against the `documents` table. Server-side: 15s query timeout, 200-row cap, `SELECT` only.

| Parameter     | Type         | Description                                                  |
| ------------- | ------------ | ------------------------------------------------------------ |
| queryrequired | str          | SELECT statement on the documents table.                     |
| source        | str= "all"   | Pass "pmc" or "biorxiv" to restrict the query to one source. |
| timeout       | float= 120 s | Client timeout in seconds.                                   |

## client.map_()

```
client.map_(
    question: str,
    *,
    from_results: str,
    timeout: float | None = None,
) -> Iterator[MapEvent]
```

Run an AI reader across every paper in a prior search/lookup result set. Yields `MapProgressEvent` updates during the run (OAuth streaming path) followed by a single `MapResultEvent`.

| Parameter            | Type         | Description                                              |
| -------------------- | ------------ | -------------------------------------------------------- |
| questionrequired     | str          | Prompt asked against each paper.                         |
| from_resultsrequired | str          | Result ID from a prior search/lookup, e.g. "s_14bebc10". |
| timeout              | float= 300 s | Map uses the slow-command default.                       |

## client.pull()

```
client.pull(
    target: str,
    dest: str | None = None,
    *,
    timeout: float | None = None,
) -> ExecuteResult
```

Download a paper or single file from the virtual filesystem. The `ExecuteResult` contains `download_url` / `download_filename` for binary payloads.

| Parameter      | Type                   | Description                                                  |
| -------------- | ---------------------- | ------------------------------------------------------------ |
| targetrequired | str                    | Paper or file, e.g. "PMC10791696" or "PMC10791696/figures/fig1.jpg". |
| dest           | str= current directory | Destination directory on the server side of the command.     |
| timeout        | float= 120 s           | Client timeout in seconds.                                   |

## client.ask_image()

```
client.ask_image(
    path: str,
    question: str | None = None,
    *,
    fn: str | None = None,
    timeout: float | None = None,
) -> ExecuteResult
```

| Parameter    | Type                                   | Description                                      |
| ------------ | -------------------------------------- | ------------------------------------------------ |
| pathrequired | str                                    | Figure path, e.g. "PMC11576387/figures/fx1.jpg". |
| question     | str= "Describe this figure in detail." | Free-form question about the figure.             |
| fn           | str= free-form prompt                  | Canned flows: "describe" or "extract-data".      |
| timeout      | float= 300 s                           | ask-image uses the slow-command default.         |

## client.bash()

```
client.bash(
    script: str,
    *,
    timeout: float | None = None,
) -> ExecuteResult
```

Run an arbitrary server-side pipeline, exactly like `paperclip bash '…'`.

```
result = client.bash('search "protein folding" | grep -i "deep learning"')
```

| Parameter      | Type         | Description                          |
| -------------- | ------------ | ------------------------------------ |
| scriptrequired | str          | A single shell-style command string. |
| timeout        | float= 120 s | Client timeout in seconds.           |

## client.results

```
client.results.list(*, limit: int | None = None) -> list[ResultRow]
client.results.get(result_id: str) -> ResultData
```

`results.list()` returns recently saved results for the authenticated user. `results.get()` fetches the raw saved output for a specific ID (e.g. `"s_14bebc10"`, `"m_ec2c9cc9"`).

| Parameter         | Type                     | Description                          |
| ----------------- | ------------------------ | ------------------------------------ |
| limit             | int= 20 (server default) | Max rows returned by results.list(). |
| result_idrequired | str                      | Result ID passed to results.get().   |

## client.papers.*

Typed wrappers over the virtual-filesystem commands. Each method returns an `ExecuteResult`.

```
client.papers.cat(path)
client.papers.head(path, *, lines=None)      # default 10 lines (server default)
client.papers.tail(path, *, lines=None)      # default 10 lines (server default)
client.papers.ls(path)
client.papers.grep(pattern, path, *, ignore_case=False, extended=False)
client.papers.scan(path, patterns)           # list of patterns OR'd together
```

When a flag like `lines`, `ignore_case`, or `extended` is left unset, the SDK omits it from the command and the server's shell-style default applies.## Escape hatches: execute() & stream()

```
client.execute(command: str, args: Sequence[str] | None = None, *, timeout=None) -> ExecuteResult
client.stream(command: str, args: Sequence[str] | None = None, *, timeout=None) -> Iterator[MapEvent]
```

For commands without a typed wrapper — `sed`, `awk`, `sort`, `cut`, `tr`, `jq`, or any future server command — pass the argv tokens as a list and the SDK shell-quotes them for you.

```
result = client.execute(
    "awk",
    ["-F", "\t", "{print $1}", "/papers/PMC1/content.lines"],
)
```

`stream()` is a streaming equivalent; today only `"map"` streams (other commands raise `ValueError`).

## Errors & result types

All HTTP and network failures raise a subclass of `PaperclipError`:

```
from gxl_paperclip import (
    AuthError, RateLimitError, NotFoundError, ServerError,
    RequestTimeoutError, NetworkError,
)

try:
    client.search("AlphaFold")
except AuthError:
    ...  # invalid API key or expired credentials
except RateLimitError:
    ...  # HTTP 429
except RequestTimeoutError:
    ...  # client-side timeout
except ServerError as exc:
    print(exc.status_code, exc.body)
```

Result dataclasses you'll encounter:

- ExecuteResult — output, exit_code, elapsed_ms, result_id, download_url, download_filename, cwd, raw
- MapProgressEvent — total, completed, failed, elapsed_s
- MapResultEvent — output, result_id, elapsed_ms, exit_code
- ResultRow — result_id, command, raw_input, latency_ms, created_at, raw
- ResultData — result_id, output, command, raw_input, latency_ms, created_at, raw
- HealthStatus — reachable, output, exit_code, elapsed_ms