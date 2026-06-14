from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any, Callable

from fastmcp import FastMCP


ROOT = Path(__file__).resolve().parent


def _load_tool(module_name: str, filename: str, function_name: str) -> Callable[..., Any]:
    module_path = ROOT / "tools" / filename
    spec = spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module spec for {module_path}")

    module = module_from_spec(spec)
    spec.loader.exec_module(module)

    fn = getattr(module, function_name, None)
    if not callable(fn):
        raise RuntimeError(f"Tool function '{function_name}' not found in {module_path}")
    return fn


search_pubmed = _load_tool("tool_pubmed", "pubmed.py", "search_pubmed")
get_abstract = _load_tool("tool_pubmed", "pubmed.py", "get_abstract")
lookup_gene = _load_tool("tool_gene", "ncbi_gene.py", "lookup_gene")
search_trials = _load_tool("tool_trials", "clinical_trials.py", "search_trials")
query_local_papers = _load_tool("tool_rag", "rag.py", "query_local_papers")
track_topic = _load_tool("tool_living_review", "living_review.py", "track_topic")
check_topic = _load_tool("tool_living_review", "living_review.py", "check_topic")
list_tracked_topics = _load_tool(
    "tool_living_review", "living_review.py", "list_tracked_topics"
)
untrack_topic = _load_tool("tool_living_review", "living_review.py", "untrack_topic")

mcp = FastMCP(
    name="BioScience MCP Server",
    instructions=(
        "Use these tools to search PubMed, NCBI Gene, and ClinicalTrials.gov, "
        "query local indexed PDFs, and run living systematic reviews that track new "
        "papers over time. Prefer precise bioscience queries and include source URLs."
    ),
)


@mcp.resource("bioscience://databases")
def databases_resource() -> str:
    return (
        "Available bioscience databases and tools:\n"
        "- PubMed (literature): search_pubmed, get_abstract\n"
        "- NCBI Gene (gene summaries): lookup_gene\n"
        "- ClinicalTrials.gov (clinical studies): search_trials\n"
        "- Local cached papers (FAISS index): query_local_papers\n"
        "- Living topic monitor (SQLite + PubMed snapshots): "
        "track_topic, check_topic, list_tracked_topics, untrack_topic"
    )


mcp.tool(search_pubmed)
mcp.tool(get_abstract)
mcp.tool(lookup_gene)
mcp.tool(search_trials)
mcp.tool(query_local_papers)
mcp.tool(track_topic)
mcp.tool(check_topic)
mcp.tool(list_tracked_topics)
mcp.tool(untrack_topic)


if __name__ == "__main__":
    mcp.run()
