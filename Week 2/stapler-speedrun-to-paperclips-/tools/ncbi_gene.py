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


def lookup_gene(gene_name: str, organism: str = "Homo sapiens") -> dict[str, Any]:
    """Look up a gene in NCBI Gene and return a compact, human-readable summary."""
    _configure_entrez()

    query = f"{gene_name}[Gene Name] AND {organism}[Organism]"
    handle = Entrez.esearch(db="gene", term=query, retmax=1)
    search_data = Entrez.read(handle)
    handle.close()

    ids = search_data.get("IdList", [])
    if not ids:
        return {
            "error": f"No gene found for '{gene_name}' in organism '{organism}'.",
            "gene_name": gene_name,
            "organism": organism,
        }

    gene_id = str(ids[0])
    summary_handle = Entrez.esummary(db="gene", id=gene_id, retmode="xml")
    summary_data = Entrez.read(summary_handle)
    summary_handle.close()

    if not summary_data:
        return {
            "error": f"No summary available for gene ID {gene_id}.",
            "gene_id": gene_id,
        }

    item = summary_data[0]
    summary_text = str(item.get("Summary", ""))
    if len(summary_text) > 500:
        summary_text = summary_text[:497] + "..."

    return {
        "gene_id": gene_id,
        "official_symbol": str(item.get("Name", "")),
        "full_name": str(item.get("Description", "")),
        "description": str(item.get("OtherAliases", "")),
        "chromosome_location": str(item.get("Chromosome", "")),
        "summary": summary_text,
        "url": f"https://www.ncbi.nlm.nih.gov/gene/{gene_id}",
    }
