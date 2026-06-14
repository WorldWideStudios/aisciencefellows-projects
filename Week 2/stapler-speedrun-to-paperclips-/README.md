# BioScience MCP Server

A bioscience-focused MCP server built with FastMCP that exposes PubMed, NCBI Gene, ClinicalTrials.gov, local RAG search over PDFs, and a Living Systematic Review engine.

## Features

- PubMed search and abstract retrieval
- NCBI Gene lookup
- ClinicalTrials.gov search
- Local RAG over cached PDFs using sentence-transformers with optional FAISS acceleration
- Living review tracker with SQLite snapshots to detect new papers over time

## Project Layout

- server.py: FastMCP server entrypoint
- tools/pubmed.py: PubMed search + abstract
- tools/ncbi_gene.py: NCBI Gene lookup
- tools/clinical_trials.py: ClinicalTrials.gov search
- tools/rag.py: local paper query tool with NumPy fallback and optional FAISS acceleration
- tools/living_review.py: topic tracking and diffing engine
- rag/ingest.py: PDF ingestion and index builder
- scripts/smoke_test.py: quick tool smoke checks
- scripts/nightly_scheduler.py: APScheduler nightly checker skeleton

## Setup

1. Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Configure environment variables:

```bash
cp .env .env.local 2>/dev/null || true
```

Then edit .env and set:

- NCBI_EMAIL (required by Entrez)
- NCBI_API_KEY (optional, higher rate limits)

4. Verify FastMCP:

```bash
fastmcp version
```

## Run

Start server:

```bash
python3 server.py
```

Run MCP Inspector:

```bash
fastmcp dev server.py
```

## Build Local RAG Index

1. Put PDFs in rag/papers/
2. Run:

```bash
python3 rag/ingest.py
```

This writes:

- rag/index/faiss.index
- rag/index/embeddings.npy
- rag/index/chunks.json

If FAISS is not installed, the NumPy embedding matrix is still enough for local search.

## Smoke Test

Quick import and local-logic checks:

```bash
python3 scripts/smoke_test.py
```

Optional live API checks (network required):

```bash
python3 scripts/smoke_test.py --live
```

## Nightly Living Review Scheduler

Run a local scheduler (default 02:00) that checks all tracked topics and logs results:

```bash
python3 scripts/nightly_scheduler.py --hour 2 --minute 0
```

Useful flags:

- --run-once: run one pass immediately and exit
- --log-file review_db/nightly_checks.log: choose output log path

## Claude Desktop MCP Config (macOS)

Edit:

~/Library/Application Support/Claude/claude_desktop_config.json

Example:

```json
{
  "mcpServers": {
    "bioscience": {
      "command": "python3",
      "args": [
        "/Users/akhildevarasetty/Desktop/WW_AI_Science_Fellowship/stapler/server.py"
      ],
      "env": {
        "NCBI_EMAIL": "you@example.com"
      }
    }
  }
}
```

Restart Claude Desktop and confirm tools are listed.

## Can I Use This Without Claude Desktop?

Yes. Any MCP-compatible client can use this server.

- VS Code with MCP-compatible tooling
- Cursor (MCP-enabled workflows)
- Other MCP clients that support stdio servers

For llama.cpp specifically:

- llama.cpp itself is an inference runtime, not an MCP client.
- To use llama.cpp models with this MCP server, run them through a host app that supports both local models and MCP tools.
- Practical path: use a UI/orchestrator that can connect to an MCP server and route model calls to a local llama.cpp backend.
- This repo now includes a small bridge script for that workflow: `scripts/llamacpp_mcp_chat.py`.

Example workflow:

1. Start a llama.cpp server that exposes an OpenAI-compatible chat endpoint.
2. Run the bridge script with a prompt.
3. The bridge calls MCP tools on your behalf and prints the model's final answer.

Example:

```bash
python3 scripts/llamacpp_mcp_chat.py \
  --prompt "Look up BRCA1 and summarize its role in breast cancer" \
  --llama-base-url http://127.0.0.1:8080/v1
```

## Suggested Demo Flow

1. Track topic: track_topic
2. Check updates later: check_topic
3. Show active topics: list_tracked_topics
4. Remove topic: untrack_topic
5. Ask RAG question: query_local_papers (after ingest)
