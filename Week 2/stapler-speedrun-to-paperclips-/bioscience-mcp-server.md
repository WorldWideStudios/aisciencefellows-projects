# BioScience MCP Server — Project Master Doc

## Overview

A bioscience-focused Model Context Protocol (MCP) server built with FastMCP that exposes multiple research tools to any MCP-compatible AI client (Claude Desktop, Cursor, VS Code). The server wraps public science APIs — PubMed, NCBI, ClinicalTrials.gov — layers a local RAG system over cached papers, and adds a **Living Systematic Review** engine that monitors research topics over time and surfaces newly published papers since the last check.

MCP is the open standard (originally by Anthropic, now Linux Foundation) that lets LLMs discover and invoke external tools. Building a domain-specific MCP server means any MCP-compatible AI client can immediately use your bioscience tools — no custom integration needed per client.

---

## Goals

- Build a working FastMCP server exposing bioscience research tools
- Wrap PubMed, NCBI Gene, and ClinicalTrials.gov APIs as MCP tools
- Add a local RAG layer over cached/downloaded papers using FAISS + sentence-transformers
- Add a Living Systematic Review engine that tracks topics over time and diffs new papers against a local SQLite snapshot
- Wire the server into Claude Desktop for a live demo
- Run entirely free, entirely local, no GPU required

---

## Tech Stack

| Layer | Technology |
|---|---|
| MCP Framework | FastMCP (Python) |
| Language | Python 3.11+ |
| API Clients | Biopython (PubMed/NCBI), requests |
| RAG / Embeddings | sentence-transformers (all-MiniLM-L6-v2), FAISS |
| PDF Parsing | PyMuPDF (fitz) |
| Living Review Storage | SQLite (via Python's built-in `sqlite3`) |
| MCP Client (demo) | Claude Desktop |
| Testing | MCP Inspector (built into FastMCP CLI) |
| Package Manager | uv (recommended) or pip |

---

## Setup

- Create a Python 3.11+ virtual environment
- Install: `fastmcp`, `biopython`, `requests`, `sentence-transformers`, `faiss-cpu`, `pymupdf`, `python-dotenv`
- No extra dependency needed for SQLite — it ships with Python's standard library
- Verify FastMCP is working with `fastmcp version`

### Environment Variables

Create a `.env` file with:
- `NCBI_EMAIL` — required by NCBI/Entrez API (free, no paid key needed, just an identifying email)
- `NCBI_API_KEY` — optional, increases rate limit from 3 to 10 requests/second

Register free at: https://www.ncbi.nlm.nih.gov/account/

---

## Project Structure

```
bioscience-mcp/
├── server.py                    # FastMCP server entry point
├── tools/
│   ├── pubmed.py                # PubMed literature search tool
│   ├── ncbi_gene.py             # NCBI Gene/protein lookup tool
│   ├── clinical_trials.py       # ClinicalTrials.gov search tool
│   ├── rag.py                   # Local RAG tool over cached papers
│   └── living_review.py         # Living Systematic Review tools
├── rag/
│   ├── ingest.py                # PDF ingestion + FAISS index builder
│   ├── index/                   # FAISS index files (gitignored)
│   └── papers/                  # Downloaded PDFs (gitignored)
├── review_db/
│   └── topics.db                # SQLite database for tracked topics (gitignored)
├── .env
├── .gitignore
└── requirements.txt
```

---

## MCP Concepts (Quick Reference)

| Concept | What it is | Analogy |
|---|---|---|
| Tool | A function the LLM can call with side effects | POST endpoint |
| Resource | Read-only data the LLM can read | GET endpoint |
| Prompt | A reusable message template | Slash command |

This project primarily uses **Tools** — functions the AI invokes to search APIs and retrieve data.

---

## Core Server — server.py

- Instantiate a `FastMCP` server with a name and a natural language `instructions` field describing what the server does and how the AI should use it
- Import and register all tools from the `tools/` directory using `mcp.tool()`
- Tools to register: `search_pubmed`, `get_abstract`, `lookup_gene`, `search_trials`, `query_local_papers`, `track_topic`, `check_topic`, `list_tracked_topics`, `untrack_topic`
- Run the server with `mcp.run()` as the entry point

---

## Tools

### tools/pubmed.py — PubMed Literature Search

**search_pubmed(query, max_results)**
- Load NCBI credentials from `.env`
- Use Biopython's `Entrez.esearch` on the `pubmed` database with the query, sorted by relevance
- Fetch summaries for returned IDs using `Entrez.esummary`
- Return a list of dicts, each containing: PMID, title, authors, journal, year, PubMed URL
- Docstring should clearly explain to the LLM what this tool does and when to use it

**get_abstract(pmid)**
- Use `Entrez.efetch` to retrieve the full abstract XML for a given PMID
- Parse out the abstract text, handling both string and list formats
- Return a dict with PMID, title, full abstract text, and PubMed URL

---

### tools/ncbi_gene.py — Gene/Protein Lookup

**lookup_gene(gene_name, organism)**
- Default organism to "Homo sapiens"
- Query NCBI Gene database with `Entrez.esearch` using gene name + organism filters
- Fetch the top result's summary with `Entrez.esummary`
- Return a dict with: gene ID, official symbol, full name, description, chromosome location, short summary (capped at ~500 chars), NCBI URL
- Return a helpful error dict if no gene is found

---

### tools/clinical_trials.py — ClinicalTrials.gov Search

**search_trials(condition, status, max_results)**
- Default status to "RECRUITING"; support "COMPLETED", "ACTIVE_NOT_RECRUITING", "ALL"
- Call the ClinicalTrials.gov REST API v2 at `https://clinicaltrials.gov/api/v2/studies`
- Pass condition and status as query params; request relevant fields only
- Return a list of dicts per trial: NCT ID, title, phase, status, start date, enrollment count, brief summary (capped ~300 chars), URL

---

### tools/rag.py — Local RAG over Cached Papers

**query_local_papers(question, top_k)**
- On first call, lazy-load the SentenceTransformer model (`all-MiniLM-L6-v2`, ~80MB, CPU-friendly) and the FAISS index + chunk metadata from disk
- If no index exists yet, return a helpful message telling the user to run `ingest.py` first
- Encode the question into an embedding vector
- Run a FAISS similarity search over the index for the top-k most relevant chunks
- Return a list of dicts with: source filename, page number, relevance score, chunk text

---

### tools/living_review.py — Living Systematic Review Engine

This is the novel feature of the project. It maintains a local SQLite database of tracked research topics, stores a snapshot of known PubMed paper IDs per topic, and surfaces newly published papers since the last check when called again.

#### SQLite Schema

Two tables:

**topics**
- `id` — auto-increment primary key
- `query` — the PubMed search query string being tracked
- `label` — a human-friendly name for the topic (e.g. "CRISPR cancer 2025")
- `created_at` — ISO timestamp of when tracking started
- `last_checked_at` — ISO timestamp of the most recent check

**seen_papers**
- `id` — auto-increment primary key
- `topic_id` — foreign key to topics
- `pmid` — PubMed ID of a paper already seen for this topic
- `first_seen_at` — ISO timestamp of when this paper was first surfaced

#### Database Initialization

- On module load, ensure `review_db/` directory exists
- Connect to `review_db/topics.db` and create both tables if they don't exist yet
- Use `CHECK NOT EXISTS` so initialization is safe to run repeatedly

---

**track_topic(query, label, max_results)**
- Register a new topic to monitor with a PubMed query string and a friendly label
- Run an initial PubMed search immediately using the query
- Store all returned PMIDs in `seen_papers` as the baseline snapshot — these will not be reported as "new" on future checks
- Insert the topic into the `topics` table with current timestamp for both `created_at` and `last_checked_at`
- Return a confirmation dict with the topic label, query, and how many baseline papers were recorded
- If the same query is already being tracked, return a message saying so instead of duplicating

---

**check_topic(label)**
- Look up the topic by label in the database
- Run a fresh PubMed search using the stored query
- Compare returned PMIDs against all PMIDs in `seen_papers` for this topic
- Papers in the new results but not in `seen_papers` are "new" — fetch their titles and metadata
- Insert the newly discovered PMIDs into `seen_papers` so they won't appear again next check
- Update `last_checked_at` to now
- Return a dict containing: topic label, last checked timestamp, number of new papers found, and a list of new paper dicts (PMID, title, journal, year, PubMed URL)
- If no new papers found, return a friendly message saying the literature is up to date

---

**list_tracked_topics()**
- Query all rows from the `topics` table
- Return a list of dicts with: label, query, created date, last checked date, and total number of seen papers for each topic
- If no topics are being tracked yet, return a helpful prompt suggesting the user call `track_topic` first

---

**untrack_topic(label)**
- Find the topic by label and delete it and all its associated `seen_papers` rows
- Return a confirmation message
- Return a helpful error if the label is not found

---

### rag/ingest.py — PDF Ingestion Script

Run this manually before using the RAG tool to build the local index.

**Logic:**
- Iterate over all PDFs in `rag/papers/`
- For each PDF, open with PyMuPDF and extract text page by page
- Chunk each page's text into overlapping fixed-size character windows (e.g. 400 chars with 50 char overlap)
- Store each chunk as a dict with: text, source filename, page number
- Encode all chunks with SentenceTransformer, normalize embeddings
- Build a FAISS `IndexFlatIP` (inner product = cosine similarity on normalized vectors)
- Save the FAISS index to `rag/index/faiss.index` and chunk metadata to `rag/index/chunks.json`

---

## Resources (MCP Read-Only Data)

Add a `@mcp.resource("bioscience://databases")` decorated function to `server.py` that returns a plain-text description of all available databases and which tool accesses each. This lets the AI know what's available without calling a tool.

---

## Connecting to Claude Desktop

Edit the Claude Desktop config file:
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

Add a `mcpServers` entry with:
- A key name (e.g. `"bioscience"`)
- `"command": "python"`
- `"args"`: absolute path to `server.py`
- `"env"`: your `NCBI_EMAIL`

Restart Claude Desktop. A hammer icon appears in the chat input — click it to confirm your tools are registered.

---

## Testing with MCP Inspector

Run `fastmcp dev server.py` to open a browser-based inspector UI. Use it to:
- Call each tool manually with test inputs
- Inspect raw inputs and outputs
- Debug errors before connecting to a real client

Suggested test order: `track_topic` → wait a few days → `check_topic` → `list_tracked_topics` → `untrack_topic`

---

## Example Demo Prompts (in Claude Desktop)

Once connected, try these:

- *"Start tracking the topic 'mRNA vaccine efficacy' on PubMed"*
- *"What new papers have come out on CRISPR cancer therapy since I last checked?"*
- *"List all the topics I'm currently monitoring"*
- *"Look up the BRCA1 gene and explain its role in breast cancer"*
- *"Find currently recruiting clinical trials for Alzheimer's disease"*
- *"What do my local papers say about immunotherapy?"* (after ingesting PDFs)

---

## Social Media Demo Flow

The living review is the most visually compelling feature for a post. Suggested demo sequence:

1. Show `track_topic` being called — Claude confirms baseline of N papers recorded
2. Fast-forward (or fake a time jump by manually backdating `last_checked_at` in the DB)
3. Show `check_topic` returning newly published papers with titles and links
4. Screenshot or screen-record Claude summarizing what changed in the literature

Hook line options:
- *"I built an MCP server that reads new science papers so you don't have to"*
- *"What if your AI automatically tracked what's new in any research field? I built that."*
- *"PubMed has 36M papers. I built an MCP server that tells you which ones are new since last week."*

---

## Stretch Goals

- **Auto-download to RAG**: When new papers are surfaced by `check_topic`, auto-download any open-access PDFs and re-index so the RAG grows in sync with the living review
- **Scheduled background checks**: Use APScheduler to run `check_topic` on all tracked topics nightly, logging results to a file even without an active AI client session
- **Topic summary diff**: On `check_topic`, ask a local LLM (via Ollama) to summarize what the new papers collectively add to the existing knowledge on this topic
- **NCBI Protein tool**: Add a `lookup_protein` tool wrapping the NCBI Protein database for structural biology queries
- **Export to Markdown**: Add a `export_review(label)` tool that generates a clean Markdown report of all seen papers for a topic, suitable for sharing

---

## Key Dependencies

```
fastmcp>=3.0
biopython>=1.83
requests>=2.31
sentence-transformers>=2.7
faiss-cpu>=1.8
pymupdf>=1.24
python-dotenv>=1.0
numpy>=1.26
# sqlite3 ships with Python standard library — no install needed
```

---

## References

- [FastMCP Docs](https://gofastmcp.com)
- [MCP Specification](https://spec.modelcontextprotocol.io)
- [NCBI Entrez API via Biopython](https://biopython.org/docs/latest/api/Bio.Entrez.html)
- [ClinicalTrials.gov API v2](https://clinicaltrials.gov/data-api/api)
- [sentence-transformers](https://www.sbert.net)
- [FAISS](https://faiss.ai)
- [Claude Desktop MCP Setup](https://docs.anthropic.com/en/docs/claude-desktop/mcp)
