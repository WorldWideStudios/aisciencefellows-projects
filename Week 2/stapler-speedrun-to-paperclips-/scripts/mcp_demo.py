from __future__ import annotations

import json
import sys
from pathlib import Path
from pprint import pprint

# Ensure project root is on sys.path so we can import the `tools` package
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.pubmed import search_pubmed, get_abstract
from tools.ncbi_gene import lookup_gene
from tools.clinical_trials import search_trials
from tools.rag import query_local_papers


def safe_print(title: str, data):
    print("\n=== {} ===".format(title))
    try:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    except Exception:
        pprint(data)


def main() -> None:
    # 1) PubMed search
    pm = search_pubmed("BRCA1 breast cancer", max_results=3)
    safe_print("PubMed search (BRCA1)", pm)

    # 2) Get abstract (if we found a PMID)
    if pm:
        pmid = pm[0].get("pmid")
        if pmid:
            abstract = get_abstract(pmid)
            safe_print(f"PubMed abstract ({pmid})", abstract)

    # 3) Gene lookup
    try:
        gene = lookup_gene("BRCA1", organism="Homo sapiens")
    except Exception as exc:
        gene = {"error": f"lookup_gene raised: {exc!r}"}
    safe_print("NCBI Gene lookup (BRCA1)", gene)

    # 4) Clinical trials
    try:
        trials = search_trials(condition="breast cancer", status="RECRUITING", max_results=3)
    except Exception as exc:
        trials = {"error": f"search_trials raised: {exc!r}"}
    safe_print("ClinicalTrials (breast cancer, recruiting)", trials)

    # 5) Local RAG (if any index exists)
    try:
        rag = query_local_papers("BRCA1 in breast cancer", top_k=3)
    except Exception as exc:
        rag = {"error": f"query_local_papers raised: {exc!r}"}
    safe_print("Local RAG query", rag)


if __name__ == "__main__":
    main()
