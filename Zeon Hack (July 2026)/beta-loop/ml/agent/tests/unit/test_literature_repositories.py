"""Unit tests for open literature repository search — mocked HTTP, no network."""

from __future__ import annotations

import json
from unittest.mock import patch

from agent.tools.literature import search_literature
from agent.tools.literature_repositories import (
    DEFAULT_REPOSITORY_SOURCES,
    list_literature_sources,
    search_repository,
)


def test_list_literature_sources_includes_five_repositories() -> None:
    info = list_literature_sources()
    assert set(DEFAULT_REPOSITORY_SOURCES) == set(info["default_repositories"])
    for src in ("europe_pmc", "pubmed", "chembl", "semantic_scholar", "openalex"):
        assert src in info["repositories"]


@patch("agent.tools.literature_repositories._http_get_json")
def test_search_europe_pmc_formats_hits(mock_json) -> None:
    mock_json.return_value = {
        "resultList": {
            "result": [
                {
                    "title": "TEM-1 tazobactam Ki",
                    "pmid": "12345",
                    "pmcid": "PMC999",
                    "abstractText": "Ki = 0.85 uM nitrocefin assay",
                }
            ]
        }
    }
    result = search_repository("europe_pmc", "TEM-1 tazobactam", limit=5)
    assert result["status"] == "ok"
    assert result["source"] == "europe_pmc"
    assert result["result_id"].startswith("repo_europe_pmc_")
    assert "TEM-1 tazobactam Ki" in result["output"]
    assert result["hit_count"] == 1


@patch("agent.tools.literature_repositories._http_get_json")
def test_search_pubmed_empty(mock_json) -> None:
    mock_json.return_value = {"esearchresult": {"idlist": []}}
    result = search_repository("pubmed", "nonexistent query xyz", limit=3)
    assert result["status"] == "ok"
    assert result["hit_count"] == 0
    assert "Found 0 PubMed results" in result["output"]


@patch("agent.tools.literature.search_repository")
def test_search_literature_routes_repository(mock_repo) -> None:
    mock_repo.return_value = {"status": "ok", "source": "chembl", "output": "hit", "result_id": "repo_chembl_abc"}
    result = search_literature("tazobactam", source="chembl", limit=5)
    mock_repo.assert_called_once_with("chembl", "tazobactam", 5)
    assert result["status"] == "ok"


def test_search_literature_unknown_source() -> None:
    result = search_literature("query", source="not_a_source", limit=5)
    assert result["status"] == "error"
    assert "Unknown source" in result["error"]
