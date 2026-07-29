"""Paperclip + open repository literature tools for the β-Loop ADK agent."""

from __future__ import annotations

import json
from typing import Any

from agent.paths import LITERATURE_DIR, LITERATURE_SUMMARY_JSON
from agent.tools.literature_repositories import (
    ALL_LITERATURE_SOURCES,
    DEFAULT_REPOSITORY_SOURCES,
    REPOSITORY_SOURCES,
    list_literature_sources,
    search_chembl_activities,
    search_repository,
)


def _paperclip_client():
    from gxl_paperclip import PaperclipClient

    return PaperclipClient.from_env()


def load_literature_summary() -> dict[str, Any]:
    """Load pre-baked literature priors from data/literature_summary.json.

    Use this before Round 1 and as the default literature source. Faster and
    more reliable than live Paperclip searches during a screen turnaround.
    """
    if not LITERATURE_SUMMARY_JSON.exists():
        return {
            "status": "missing",
            "message": (
                f"No summary at {LITERATURE_SUMMARY_JSON}. "
                "Run Phase 0 Paperclip searches or hardcode a summary file."
            ),
            "known_inhibitors": [
                "clavulanic acid",
                "sulbactam",
                "tazobactam",
                "enmetazobactam",
            ],
            "expected_substrates_low_inhibition": [
                "ampicillin",
                "cephalexin",
                "penicillins",
                "cephalosporins",
            ],
            "assay_notes": {
                "typical_screen_conc_uM": 50,
                "pre_incubation_min": 10,
                "read_wavelength_nm": 490,
                "metric": "initial slope A490 vs time",
            },
        }
    return json.loads(LITERATURE_SUMMARY_JSON.read_text())


def search_literature(
    query: str,
    source: str = "europe_pmc",
    limit: int = 10,
) -> dict[str, Any]:
    """Search biomedical literature via open repositories or Paperclip.

    Open repositories (no map quota): europe_pmc, pubmed, chembl, semantic_scholar, openalex.
    Paperclip (full-text map): pmc, biorxiv, proteins.

    Prefer europe_pmc + chembl for Ki/IC50; use Paperclip map only when needed.

    Args:
        query: Natural-language search query.
        source: Repository id — see list_literature_sources().
        limit: Maximum number of results (default 10, cap at 30).
    """
    limit = max(1, min(limit, 30))
    if source in REPOSITORY_SOURCES:
        return search_repository(source, query, limit)

    if source not in ALL_LITERATURE_SOURCES:
        return {
            "status": "error",
            "query": query,
            "source": source,
            "error": (
                f"Unknown source '{source}'. "
                f"Use list_literature_sources() — known: {sorted(ALL_LITERATURE_SOURCES)}"
            ),
        }

    try:
        client = _paperclip_client()
        result = client.search(query, source=source, limit=limit)
        return {
            "status": "ok",
            "query": query,
            "source": source,
            "limit": limit,
            "backend": "paperclip",
            "result_id": result.result_id,
            "output": result.output,
        }
    except Exception as exc:  # noqa: BLE001 — surface tool errors to the agent
        summary = load_literature_summary()
        return {
            "status": "error",
            "query": query,
            "source": source,
            "backend": "paperclip",
            "error": str(exc),
            "fallback_summary": summary,
        }


def save_literature_search(
    query: str,
    source: str = "europe_pmc",
    limit: int = 10,
    filename: str | None = None,
) -> dict[str, Any]:
    """Run a literature search and save raw output under data/compound_literature/."""
    result = search_literature(query=query, source=source, limit=limit)
    if result.get("status") != "ok":
        return result

    LITERATURE_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = filename or f"{source}_{abs(hash(query)) % 10_000_000}.txt"
    out_path = LITERATURE_DIR / safe_name
    out_path.write_text(result.get("output", ""))
    result["saved_path"] = str(out_path)
    return result


def map_literature_results(question: str, from_results: str) -> dict[str, Any]:
    """Run Paperclip map against a prior Paperclip search result set (Ki/IC50 extraction).

    Note: from_results must be a Paperclip result_id (s_*). Repository result_ids
    (repo_*) are not mappable — parse search output directly or use search_chembl_activities().
    """
    if from_results.startswith("repo_"):
        return {
            "status": "error",
            "question": question,
            "from_results": from_results,
            "error": (
                "Repository searches are not Paperclip-mappable. "
                "Use search_chembl_activities() or parse the repository output text."
            ),
        }
    try:
        from gxl_paperclip import MapResultEvent

        client = _paperclip_client()
        result_event: MapResultEvent | None = None
        for event in client.map_(question, from_results=from_results):
            if isinstance(event, MapResultEvent):
                result_event = event
        if result_event is None:
            return {
                "status": "error",
                "question": question,
                "from_results": from_results,
                "error": "Paperclip map returned no result event",
            }
        return {
            "status": "ok",
            "question": question,
            "from_results": from_results,
            "backend": "paperclip",
            "result_id": result_event.result_id,
            "output": result_event.output,
            "elapsed_ms": result_event.elapsed_ms,
        }
    except Exception as exc:  # noqa: BLE001 — surface tool errors to the agent
        return {
            "status": "error",
            "question": question,
            "from_results": from_results,
            "error": str(exc),
        }


__all__ = [
    "ALL_LITERATURE_SOURCES",
    "DEFAULT_REPOSITORY_SOURCES",
    "load_literature_summary",
    "list_literature_sources",
    "map_literature_results",
    "save_literature_search",
    "search_chembl_activities",
    "search_literature",
]
