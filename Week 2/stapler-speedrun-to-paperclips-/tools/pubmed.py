from __future__ import annotations

import os
from typing import Any

from Bio import Entrez
from dotenv import load_dotenv


load_dotenv()


def _configure_entrez() -> None:
    Entrez.email = os.getenv("NCBI_EMAIL", "")
    api_key = os.getenv("NCBI_API_KEY", "").strip()
    if api_key:
        Entrez.api_key = api_key


def _safe_year(pub_date: str) -> str:
    if not pub_date:
        return ""
    return pub_date[:4]


def _pubmed_url(pmid: str) -> str:
    return f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"


def search_pubmed(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    """Search PubMed for relevant bioscience papers and return concise metadata.

    Use this for literature discovery before drilling into a specific paper with
    get_abstract.
    """
    _configure_entrez()

    handle = Entrez.esearch(
        db="pubmed",
        term=query,
        retmax=max_results,
        sort="relevance",
    )
    search_data = Entrez.read(handle)
    handle.close()

    pmids = search_data.get("IdList", [])
    if not pmids:
        return []

    summary_handle = Entrez.esummary(db="pubmed", id=",".join(pmids), retmode="xml")
    summaries = Entrez.read(summary_handle)
    summary_handle.close()

    results: list[dict[str, Any]] = []
    for item in summaries:
        pmid = str(item.get("Id", ""))
        authors = item.get("AuthorList", []) or []
        author_names = [str(a) for a in authors[:8]]

        results.append(
            {
                "pmid": pmid,
                "title": str(item.get("Title", "")),
                "authors": author_names,
                "journal": str(item.get("FullJournalName", "")),
                "year": _safe_year(str(item.get("PubDate", ""))),
                "url": _pubmed_url(pmid),
            }
        )

    return results


def _flatten_abstract_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        parts = [str(part).strip() for part in value if str(part).strip()]
        return "\n".join(parts)
    return str(value).strip()


def get_abstract(pmid: str) -> dict[str, Any]:
    """Fetch the full PubMed abstract for a PMID.

    Use this after search_pubmed when you want the detailed abstract text for a
    specific paper.
    """
    _configure_entrez()

    handle = Entrez.efetch(db="pubmed", id=pmid, rettype="abstract", retmode="xml")
    data = Entrez.read(handle)
    handle.close()

    articles = data.get("PubmedArticle", [])
    if not articles:
        return {
            "error": f"No PubMed article found for PMID {pmid}",
            "pmid": pmid,
            "url": _pubmed_url(pmid),
        }

    article = articles[0].get("MedlineCitation", {}).get("Article", {})
    title = str(article.get("ArticleTitle", ""))
    abstract_node = article.get("Abstract", {})
    abstract_text = _flatten_abstract_text(abstract_node.get("AbstractText", ""))

    return {
        "pmid": str(pmid),
        "title": title,
        "abstract": abstract_text,
        "url": _pubmed_url(str(pmid)),
    }
