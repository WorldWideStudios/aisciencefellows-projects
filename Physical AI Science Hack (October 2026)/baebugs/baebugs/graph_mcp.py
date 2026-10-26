"""MCP server for the baebugs graph: the same pack and the same answers as the web page, CLI and npx.

  claude mcp add baebugs-graph -- python -m baebugs.graph_mcp      (needs `pip install mcp`)
Tools: root(), get(address_or_text), prove(fco_json), claims()
"""
from __future__ import annotations

import json

from . import mvp

PACK = mvp.load()


def root() -> dict:
    """The MVP root and the roots it is built from (AoK, hypergraph, MMR logs), plus custody status."""
    return {"root": PACK["root"], "roots": PACK["roots"], "custody": PACK["custody"]}


def get(q: str) -> dict:
    """Resolve 'root', 'module:<name>', 'leaf:<path>', a leaf hash or a file sha256; otherwise search text."""
    return mvp.get(PACK, q)


def prove(fco_json: str) -> dict:
    """Compare an FCO/FCG ({"leaves":[{"path","sha256"}]}) with the graph and return an attestation."""
    return mvp.prove(PACK, json.loads(fco_json))


def claims() -> dict:
    """What is claimed under which licence: legend, per-module claims and outside terms, external atoms."""
    return {"legend": PACK["legend"], "totals": PACK["totals"],
            "modules": {k: {x: v[x] for x in ("claims", "terms", "root")} for k, v in PACK["modules"].items()},
            "external": [{x: e[x] for x in ("id", "name", "licence", "effect")} for e in PACK["external"]]}


def serve():
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as e:      # missing, or mcp 2.x (FastMCP renamed)
        raise SystemExit('baebugs.graph_mcp needs mcp 1.x: pip install "mcp>=1.2,<2"') from e
    app = FastMCP("baebugs-graph")
    for f in (root, get, prove, claims):
        app.tool()(f)
    app.run()


if __name__ == "__main__":
    serve()
