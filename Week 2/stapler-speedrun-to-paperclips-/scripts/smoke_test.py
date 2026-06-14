from __future__ import annotations

import argparse
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.clinical_trials import search_trials
from tools.living_review import list_tracked_topics
from tools.ncbi_gene import lookup_gene
from tools.pubmed import search_pubmed
from tools.rag import query_local_papers


def _ok(name: str, detail: str) -> None:
    print(f"[OK] {name}: {detail}")


def _fail(name: str, detail: str) -> None:
    print(f"[FAIL] {name}: {detail}")


def run_non_live_checks() -> int:
    status = 0

    # This should always return either a dict message or list, even if no index exists.
    rag_result = query_local_papers("test question", top_k=2)
    if isinstance(rag_result, (dict, list)):
        _ok("query_local_papers", f"returned {type(rag_result).__name__}")
    else:
        status = 1
        _fail("query_local_papers", "unexpected return type")

    topics = list_tracked_topics()
    if isinstance(topics, (dict, list)):
        _ok("list_tracked_topics", f"returned {type(topics).__name__}")
    else:
        status = 1
        _fail("list_tracked_topics", "unexpected return type")

    return status


def run_live_checks() -> int:
    status = 0

    try:
        papers = search_pubmed("mRNA vaccine efficacy", max_results=2)
        if isinstance(papers, list):
            _ok("search_pubmed", f"returned {len(papers)} items")
        else:
            status = 1
            _fail("search_pubmed", "did not return a list")
    except (requests.RequestException, OSError, ValueError, RuntimeError) as exc:
        status = 1
        _fail("search_pubmed", str(exc))

    try:
        gene = lookup_gene("BRCA1")
        if isinstance(gene, dict) and ("gene_id" in gene or "error" in gene):
            _ok("lookup_gene", "returned expected dict shape")
        else:
            status = 1
            _fail("lookup_gene", "unexpected dict shape")
    except (requests.RequestException, OSError, ValueError, RuntimeError) as exc:
        status = 1
        _fail("lookup_gene", str(exc))

    try:
        trials = search_trials("Alzheimer disease", status="RECRUITING", max_results=2)
        if isinstance(trials, list):
            _ok("search_trials", f"returned {len(trials)} items")
        else:
            status = 1
            _fail("search_trials", "did not return a list")
    except (requests.RequestException, OSError, ValueError, RuntimeError) as exc:
        status = 1
        _fail("search_trials", str(exc))

    return status


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke checks for BioScience MCP tools")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Run live network checks against PubMed/Gene/ClinicalTrials APIs",
    )
    args = parser.parse_args()

    status = run_non_live_checks()
    if args.live:
        status = max(status, run_live_checks())

    return status


if __name__ == "__main__":
    raise SystemExit(main())
