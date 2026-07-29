"""Open literature repository search — Europe PMC, PubMed, ChEMBL, Semantic Scholar, OpenAlex."""

from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.parse
import urllib.request
from typing import Any, Callable

USER_AGENT = "beta-loop/1.0 (zeon_hack literature agent; mailto:pvjthomas@users.noreply.github.com)"
REQUEST_TIMEOUT_S = 30

REPOSITORY_SOURCES = frozenset(
    {
        "europe_pmc",
        "pubmed",
        "chembl",
        "semantic_scholar",
        "openalex",
    }
)

PAPERCLIP_SOURCES = frozenset({"pmc", "biorxiv", "proteins", "trials/us"})

ALL_LITERATURE_SOURCES = REPOSITORY_SOURCES | PAPERCLIP_SOURCES

DEFAULT_REPOSITORY_SOURCES = (
    "europe_pmc",
    "pubmed",
    "chembl",
    "semantic_scholar",
    "openalex",
)


def list_literature_sources() -> dict[str, Any]:
    """Return registered literature search backends and defaults."""
    return {
        "repositories": sorted(REPOSITORY_SOURCES),
        "paperclip": sorted(PAPERCLIP_SOURCES),
        "all": sorted(ALL_LITERATURE_SOURCES),
        "default_repositories": list(DEFAULT_REPOSITORY_SOURCES),
    }


def _repo_result_id(source: str, query: str, limit: int) -> str:
    digest = hashlib.sha256(f"{source}|{query}|{limit}".encode()).hexdigest()[:12]
    return f"repo_{source}_{digest}"


def _http_get_json(url: str, headers: dict[str, str] | None = None) -> Any:
    req_headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if headers:
        req_headers.update(headers)
    request = urllib.request.Request(url, headers=req_headers)
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_S) as response:
        return json.loads(response.read().decode())


def _http_get_text(url: str, headers: dict[str, str] | None = None) -> str:
    req_headers = {"User-Agent": USER_AGENT}
    if headers:
        req_headers.update(headers)
    request = urllib.request.Request(url, headers=req_headers)
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_S) as response:
        return response.read().decode()


def _format_hit_lines(title: str, meta: str, snippet: str, idx: int) -> str:
    lines = [f"  {idx}. {title}"]
    if meta:
        lines.append(f"     {meta}")
    if snippet:
        lines.append(f"     {snippet[:400]}")
    return "\n".join(lines)


def search_europe_pmc(query: str, limit: int = 10) -> dict[str, Any]:
    """Search Europe PMC REST API (full-text biomedical index)."""
    params = {
        "query": query,
        "format": "json",
        "pageSize": str(limit),
        "resultType": "core",
    }
    url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search?" + urllib.parse.urlencode(params)
    started = time.perf_counter()
    payload = _http_get_json(url)
    hits = payload.get("resultList", {}).get("result", []) or []
    lines = [f"Found {len(hits)} Europe PMC results [{_repo_result_id('europe_pmc', query, limit)}]", ""]
    for i, hit in enumerate(hits[:limit], 1):
        title = hit.get("title") or "Untitled"
        meta_parts = []
        if hit.get("pmcid"):
            meta_parts.append(hit["pmcid"])
        if hit.get("pmid"):
            meta_parts.append(f"PMID:{hit['pmid']}")
        if hit.get("doi"):
            meta_parts.append(hit["doi"])
        if hit.get("journalTitle"):
            meta_parts.append(str(hit["journalTitle"]))
        if hit.get("pubYear"):
            meta_parts.append(str(hit["pubYear"]))
        snippet = hit.get("abstractText") or hit.get("snippet") or ""
        lines.append(_format_hit_lines(title, " · ".join(meta_parts), snippet, i))
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    return {
        "status": "ok",
        "source": "europe_pmc",
        "query": query,
        "limit": limit,
        "result_id": _repo_result_id("europe_pmc", query, limit),
        "output": "\n".join(lines),
        "elapsed_ms": elapsed_ms,
        "hit_count": len(hits),
        "api_url": url,
    }


def search_pubmed(query: str, limit: int = 10) -> dict[str, Any]:
    """Search PubMed via NCBI E-utilities (esearch + esummary)."""
    api_key = os.getenv("NCBI_API_KEY")
    started = time.perf_counter()
    esearch_params = {
        "db": "pubmed",
        "term": query,
        "retmode": "json",
        "retmax": str(limit),
    }
    if api_key:
        esearch_params["api_key"] = api_key
    esearch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?" + urllib.parse.urlencode(
        esearch_params
    )
    esearch = _http_get_json(esearch_url)
    id_list = esearch.get("esearchresult", {}).get("idlist", [])
    if not id_list:
        output = f"Found 0 PubMed results [{_repo_result_id('pubmed', query, limit)}]"
        return {
            "status": "ok",
            "source": "pubmed",
            "query": query,
            "limit": limit,
            "result_id": _repo_result_id("pubmed", query, limit),
            "output": output,
            "elapsed_ms": int((time.perf_counter() - started) * 1000),
            "hit_count": 0,
            "api_url": esearch_url,
        }

    esummary_params = {
        "db": "pubmed",
        "id": ",".join(id_list),
        "retmode": "json",
    }
    if api_key:
        esummary_params["api_key"] = api_key
    esummary_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?" + urllib.parse.urlencode(
        esummary_params
    )
    esummary = _http_get_json(esummary_url)
    summaries = esummary.get("result", {})
    lines = [f"Found {len(id_list)} PubMed results [{_repo_result_id('pubmed', query, limit)}]", ""]
    for i, pmid in enumerate(id_list, 1):
        item = summaries.get(pmid, {})
        title = item.get("title") or "Untitled"
        meta_parts = [f"PMID:{pmid}"]
        if item.get("source"):
            meta_parts.append(str(item["source"]))
        if item.get("pubdate"):
            meta_parts.append(str(item["pubdate"]))
        if item.get("elocationid"):
            meta_parts.append(str(item["elocationid"]))
        lines.append(_format_hit_lines(title, " · ".join(meta_parts), "", i))
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    return {
        "status": "ok",
        "source": "pubmed",
        "query": query,
        "limit": limit,
        "result_id": _repo_result_id("pubmed", query, limit),
        "output": "\n".join(lines),
        "elapsed_ms": elapsed_ms,
        "hit_count": len(id_list),
        "api_url": esearch_url,
    }


def search_chembl(query: str, limit: int = 10) -> dict[str, Any]:
    """Search ChEMBL molecules + TEM-1-related activities when compound name matches."""
    started = time.perf_counter()
    mol_url = (
        "https://www.ebi.ac.uk/chembl/api/data/molecule/search?"
        + urllib.parse.urlencode({"q": query, "limit": min(limit, 25)})
    )
    mol_payload = _http_get_json(mol_url)
    molecules = mol_payload.get("molecules", []) or []
    lines = [f"ChEMBL molecule search [{_repo_result_id('chembl', query, limit)}]", ""]

    for i, mol in enumerate(molecules[:limit], 1):
        pref_name = mol.get("pref_name") or mol.get("molecule_chembl_id") or "unknown"
        chembl_id = mol.get("molecule_chembl_id", "")
        meta = f"{chembl_id}"
        if mol.get("max_phase") is not None:
            meta += f" · max_phase={mol['max_phase']}"
        lines.append(_format_hit_lines(pref_name, meta, "", i))

        if not chembl_id:
            continue
        act_params = urllib.parse.urlencode(
            {
                "molecule_chembl_id": chembl_id,
                "target_organism": "Escherichia coli",
                "standard_type__in": "Ki,IC50,IC90,Kd",
                "limit": 10,
            }
        )
        act_url = f"https://www.ebi.ac.uk/chembl/api/data/activity.json?{act_params}"
        try:
            act_payload = _http_get_json(act_url)
            activities = act_payload.get("activities", []) or []
            for act in activities[:5]:
                stype = act.get("standard_type") or act.get("type") or "activity"
                sval = act.get("standard_value")
                sunit = act.get("standard_units") or ""
                target = act.get("target_pref_name") or act.get("target_chembl_id") or ""
                assay = act.get("assay_description") or ""
                if sval is not None:
                    lines.append(f"       {stype}={sval} {sunit} vs {target}; assay: {assay[:120]}")
        except Exception:
            continue

    if len(lines) <= 2:
        lines.append("  (no ChEMBL molecule matches)")

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    return {
        "status": "ok",
        "source": "chembl",
        "query": query,
        "limit": limit,
        "result_id": _repo_result_id("chembl", query, limit),
        "output": "\n".join(lines),
        "elapsed_ms": elapsed_ms,
        "hit_count": len(molecules),
        "api_url": mol_url,
    }


def search_chembl_activities(
    compound_name: str,
    *,
    target_query: str = "TEM-1",
    limit: int = 20,
) -> dict[str, Any]:
    """Structured ChEMBL activity lookup for compound vs beta-lactamase target."""
    started = time.perf_counter()
    mol_url = (
        "https://www.ebi.ac.uk/chembl/api/data/molecule/search?"
        + urllib.parse.urlencode({"q": compound_name, "limit": 3})
    )
    mol_payload = _http_get_json(mol_url)
    molecules = mol_payload.get("molecules", []) or []
    if not molecules:
        return {
            "status": "ok",
            "source": "chembl",
            "query": compound_name,
            "target_query": target_query,
            "activities": [],
            "output": f"No ChEMBL molecule for {compound_name}",
            "result_id": _repo_result_id("chembl_act", compound_name, limit),
            "elapsed_ms": int((time.perf_counter() - started) * 1000),
        }

    tgt_url = (
        "https://www.ebi.ac.uk/chembl/api/data/target/search?"
        + urllib.parse.urlencode({"q": f"beta-lactamase {target_query}", "limit": 5})
    )
    tgt_payload = _http_get_json(tgt_url)
    targets = tgt_payload.get("targets", []) or []
    target_ids = [t.get("target_chembl_id") for t in targets if t.get("target_chembl_id")]

    activities: list[dict[str, Any]] = []
    lines = [f"ChEMBL activities for {compound_name} vs {target_query}", ""]

    for mol in molecules[:2]:
        mid = mol.get("molecule_chembl_id")
        mname = mol.get("pref_name") or mid
        if not mid:
            continue
        params: dict[str, str | int] = {
            "molecule_chembl_id": mid,
            "standard_type__in": "Ki,IC50,IC90,Kd",
            "limit": limit,
        }
        if target_ids:
            params["target_chembl_id__in"] = ",".join(target_ids[:5])
        act_url = "https://www.ebi.ac.uk/chembl/api/data/activity.json?" + urllib.parse.urlencode(params)
        act_payload = _http_get_json(act_url)
        for act in act_payload.get("activities", []) or []:
            row = {
                "molecule_chembl_id": mid,
                "molecule_name": mname,
                "target_pref_name": act.get("target_pref_name"),
                "target_chembl_id": act.get("target_chembl_id"),
                "standard_type": act.get("standard_type"),
                "standard_value": act.get("standard_value"),
                "standard_units": act.get("standard_units"),
                "pchembl_value": act.get("pchembl_value"),
                "assay_description": act.get("assay_description"),
                "document_chembl_id": act.get("document_chembl_id"),
            }
            activities.append(row)
            if act.get("standard_value") is not None:
                lines.append(
                    f"  {mname}: {act.get('standard_type')}={act.get('standard_value')} "
                    f"{act.get('standard_units') or ''} vs {act.get('target_pref_name')}; "
                    f"assay: {(act.get('assay_description') or '')[:100]}"
                )

    if len(lines) == 2:
        lines.append("  (no matching activities)")

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    return {
        "status": "ok",
        "source": "chembl",
        "query": compound_name,
        "target_query": target_query,
        "activities": activities,
        "output": "\n".join(lines),
        "result_id": _repo_result_id("chembl_act", f"{compound_name}|{target_query}", limit),
        "elapsed_ms": elapsed_ms,
        "hit_count": len(activities),
    }


def search_semantic_scholar(query: str, limit: int = 10) -> dict[str, Any]:
    """Search Semantic Scholar paper graph."""
    limit = max(1, min(limit, 100))
    fields = "title,year,authors,externalIds,abstract,citationCount,journal"
    params = {"query": query, "limit": str(limit), "fields": fields}
    url = "https://api.semanticscholar.org/graph/v1/paper/search?" + urllib.parse.urlencode(params)
    headers: dict[str, str] = {}
    s2_key = os.getenv("S2_API_KEY") or os.getenv("SEMANTIC_SCHOLAR_API_KEY")
    if s2_key:
        headers["x-api-key"] = s2_key
    started = time.perf_counter()
    payload = _http_get_json(url, headers=headers)
    hits = payload.get("data", []) or []
    lines = [f"Found {len(hits)} Semantic Scholar results [{_repo_result_id('semantic_scholar', query, limit)}]", ""]
    for i, hit in enumerate(hits[:limit], 1):
        title = hit.get("title") or "Untitled"
        meta_parts = []
        ext = hit.get("externalIds") or {}
        if ext.get("DOI"):
            meta_parts.append(f"DOI:{ext['DOI']}")
        if ext.get("PubMed"):
            meta_parts.append(f"PMID:{ext['PubMed']}")
        if hit.get("year"):
            meta_parts.append(str(hit["year"]))
        if hit.get("citationCount") is not None:
            meta_parts.append(f"citations={hit['citationCount']}")
        snippet = hit.get("abstract") or ""
        lines.append(_format_hit_lines(title, " · ".join(meta_parts), snippet, i))
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    return {
        "status": "ok",
        "source": "semantic_scholar",
        "query": query,
        "limit": limit,
        "result_id": _repo_result_id("semantic_scholar", query, limit),
        "output": "\n".join(lines),
        "elapsed_ms": elapsed_ms,
        "hit_count": len(hits),
        "api_url": url,
    }


def search_openalex(query: str, limit: int = 10) -> dict[str, Any]:
    """Search OpenAlex works index."""
    limit = max(1, min(limit, 25))
    params = {
        "search": query,
        "per_page": str(limit),
        "mailto": os.getenv("OPENALEX_MAILTO", "pvjthomas@users.noreply.github.com"),
    }
    oa_key = os.getenv("OPENALEX_API_KEY")
    if oa_key:
        params["api_key"] = oa_key
    url = "https://api.openalex.org/works?" + urllib.parse.urlencode(params)
    started = time.perf_counter()
    payload = _http_get_json(url)
    hits = payload.get("results", []) or []
    lines = [f"Found {len(hits)} OpenAlex results [{_repo_result_id('openalex', query, limit)}]", ""]
    for i, hit in enumerate(hits[:limit], 1):
        title = hit.get("title") or "Untitled"
        meta_parts = []
        if hit.get("doi"):
            meta_parts.append(hit["doi"])
        if hit.get("publication_year"):
            meta_parts.append(str(hit["publication_year"]))
        if hit.get("cited_by_count") is not None:
            meta_parts.append(f"cited_by={hit['cited_by_count']}")
        ids = hit.get("ids") or {}
        if ids.get("pmid"):
            meta_parts.append(f"PMID:{ids['pmid'].replace('https://pubmed.ncbi.nlm.nih.gov/', '')}")
        snippet = hit.get("abstract_inverted_index")
        if isinstance(snippet, dict):
            words = sorted(snippet.items(), key=lambda kv: kv[1][0] if kv[1] else 0)
            snippet_text = " ".join(w for w, _ in words[:80])
        else:
            snippet_text = ""
        lines.append(_format_hit_lines(title, " · ".join(meta_parts), snippet_text, i))
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    return {
        "status": "ok",
        "source": "openalex",
        "query": query,
        "limit": limit,
        "result_id": _repo_result_id("openalex", query, limit),
        "output": "\n".join(lines),
        "elapsed_ms": elapsed_ms,
        "hit_count": len(hits),
        "api_url": url,
    }


_SEARCH_HANDLERS: dict[str, Callable[[str, int], dict[str, Any]]] = {
    "europe_pmc": search_europe_pmc,
    "pubmed": search_pubmed,
    "chembl": search_chembl,
    "semantic_scholar": search_semantic_scholar,
    "openalex": search_openalex,
}


def search_repository(source: str, query: str, limit: int = 10) -> dict[str, Any]:
    """Dispatch to a registered open literature repository."""
    if source not in REPOSITORY_SOURCES:
        return {
            "status": "error",
            "source": source,
            "query": query,
            "error": f"Unknown repository source '{source}'. Known: {sorted(REPOSITORY_SOURCES)}",
        }
    limit = max(1, min(limit, 30))
    try:
        return _SEARCH_HANDLERS[source](query, limit)
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "error",
            "source": source,
            "query": query,
            "limit": limit,
            "error": str(exc),
        }
