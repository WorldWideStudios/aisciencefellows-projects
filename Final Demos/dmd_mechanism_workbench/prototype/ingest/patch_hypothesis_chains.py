"""Patch mechanism.sqlite in-place: load curated chain data for H02, H03, H04.

The original build_mechanism_sqlite.py left these three hypotheses with
empty chains (only H01 was curated). This script imports the HYPOTHESES
list from build_mechanism_sqlite (which now carries curated chains for
all four) and inserts only the missing rows — preserving H01, HPA
celltype rows, Reactome pathway rows, and all other tables.

Idempotent: wipes prior chain rows for H02/03/04 before insert.

Run:
    python3 -m prototype.ingest.patch_hypothesis_chains
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from prototype.ingest.build_mechanism_sqlite import HYPOTHESES

REPO = Path(__file__).resolve().parents[2]
DB = REPO / "data" / "mechanism.sqlite"

PATCH_IDS = ("02", "03", "04")


def main() -> None:
    conn = sqlite3.connect(DB)

    for hid in PATCH_IDS:
        conn.execute("DELETE FROM hypothesis_chain_nodes         WHERE hypothesis_id=?", (hid,))
        conn.execute("DELETE FROM hypothesis_chain_edges         WHERE hypothesis_id=?", (hid,))
        conn.execute("DELETE FROM hypothesis_chain_edge_evidence WHERE hypothesis_id=?", (hid,))
        conn.execute("DELETE FROM hypothesis_therapeutic_node    WHERE hypothesis_id=?", (hid,))
        conn.execute("DELETE FROM hypothesis_evidence            WHERE hypothesis_id=?", (hid,))
        # Update the lede on the hypotheses row too (was NULL before)
        h = next(x for x in HYPOTHESES if x["id"] == hid)
        conn.execute("UPDATE hypotheses SET lede=? WHERE id=?", (h["lede"], hid))

        for ord_, (tone, text, cite) in enumerate(h["evidence_list"]):
            conn.execute("INSERT INTO hypothesis_evidence VALUES (?,?,?,?,?)",
                         (hid, ord_, tone, text, cite))
        for (nid, col, row_, tier, l1, l2, meta) in h["chain_nodes"]:
            conn.execute("INSERT INTO hypothesis_chain_nodes VALUES (?,?,?,?,?,?,?,?)",
                         (hid, nid, col, row_, tier, l1, l2, meta))
        for (a, b) in h["chain_edges"]:
            conn.execute("INSERT INTO hypothesis_chain_edges VALUES (?,?,?)",
                         (hid, a, b))
        edge_ord: dict[tuple[str, str], int] = {}
        for (a, b, tone, text, cite) in h["chain_edge_evidence"]:
            key = (a, b)
            ord_ = edge_ord.get(key, 0)
            edge_ord[key] = ord_ + 1
            conn.execute(
                "INSERT INTO hypothesis_chain_edge_evidence VALUES (?,?,?,?,?,?,?)",
                (hid, a, b, ord_, tone, text, cite),
            )
        if h.get("therapy"):
            conn.execute("INSERT INTO hypothesis_therapeutic_node VALUES (?,?,?)",
                         (hid, h["therapy"][0], h["therapy"][1]))

        print(f"[patched] H{hid}: {len(h['chain_nodes']):>2} nodes · "
              f"{len(h['chain_edges']):>2} edges · "
              f"{len(h['chain_edge_evidence']):>2} edge-evi · "
              f"{len(h['evidence_list']):>2} evi")

    conn.commit()
    conn.close()
    print(f"[done] patched {len(PATCH_IDS)} hypotheses in {DB}")


if __name__ == "__main__":
    main()
