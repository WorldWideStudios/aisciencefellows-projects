"""Open Targets Platform → mechanism.sqlite (opentargets_dmd_* tables).

Cohort-scope premise source. Pulls the DMD target record (ENSG00000198947)
via the Open Targets GraphQL API and materializes it as four small tables
that later hypothesis-scoring code can cite:

    opentargets_dmd_summary       — 1 row: id, symbol, name, biotype, refreshed_at
    opentargets_dmd_tractability  — modality × label × value (SM / AB / PR / OC)
    opentargets_dmd_pathway       — Reactome pathway rows already associated to DMD
    opentargets_dmd_disease       — top-N disease associations (score, disease name)
    opentargets_dmd_drug          — drugs / clinical candidates targeting DMD
    opentargets_dmd_interaction   — molecular interactors (IntAct, Reactome, Signor)

The raw response is cached to data/raw/opentargets_DMD.json for provenance —
re-runs pull from the cache unless --refresh is passed.

Run:
    python3 -m prototype.ingest.bake_opentargets
    python3 -m prototype.ingest.bake_opentargets --refresh   # re-fetch
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CACHE = REPO / "data" / "raw" / "opentargets_DMD.json"
DB = REPO / "data" / "mechanism.sqlite"

ENSEMBL_ID = "ENSG00000198947"
ENDPOINT = "https://api.platform.opentargets.org/api/v4/graphql"

# Field names verified via introspection against the live v4 schema
# (Nov 2025). Do not add fields without probing __type first — the schema
# has a handful of look-alike names (e.g. drugAndClinicalCandidates.rows
# rejects drugId / drugName; the row wraps a Drug node under .drug).
QUERY = """query DmdTarget {
  target(ensemblId: "%s") {
    id approvedSymbol approvedName biotype
    tractability { modality value label }
    pathways { pathwayId pathway topLevelTerm }
    associatedDiseases(page: {index: 0, size: 40}) {
      count
      rows { score disease { id name } }
    }
    drugAndClinicalCandidates {
      count
      rows {
        maxClinicalStage id
        drug { id name drugType maximumClinicalStage }
      }
    }
    interactions(page: {index: 0, size: 40}) {
      count
      rows {
        intB
        targetB { id approvedSymbol }
        score
        sourceDatabase
      }
    }
  }
}""" % ENSEMBL_ID


SCHEMA = """
CREATE TABLE IF NOT EXISTS opentargets_dmd_summary (
  ensembl_id     TEXT PRIMARY KEY,
  symbol         TEXT NOT NULL,
  name           TEXT,
  biotype        TEXT,
  refreshed_at   TEXT NOT NULL,
  source_url     TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS opentargets_dmd_tractability (
  modality       TEXT NOT NULL,
  label          TEXT NOT NULL,
  value          INTEGER NOT NULL,
  PRIMARY KEY(modality, label)
);
CREATE TABLE IF NOT EXISTS opentargets_dmd_pathway (
  pathway_id     TEXT PRIMARY KEY,
  pathway        TEXT NOT NULL,
  top_level_term TEXT
);
CREATE TABLE IF NOT EXISTS opentargets_dmd_disease (
  disease_id     TEXT PRIMARY KEY,
  disease_name   TEXT NOT NULL,
  score          REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_ot_disease_score ON opentargets_dmd_disease(score);
CREATE TABLE IF NOT EXISTS opentargets_dmd_drug (
  drug_id            TEXT PRIMARY KEY,
  drug_name          TEXT,
  drug_type          TEXT,
  max_clinical_stage TEXT,
  drug_max_stage     TEXT
);
CREATE TABLE IF NOT EXISTS opentargets_dmd_interaction (
  partner_id      TEXT NOT NULL,
  partner_symbol  TEXT,
  score           REAL,
  source_database TEXT,
  PRIMARY KEY(partner_id, source_database)
);
CREATE INDEX IF NOT EXISTS ix_ot_int_score ON opentargets_dmd_interaction(score);
"""


def _fetch(query: str, timeout: int = 60) -> dict:
    req = urllib.request.Request(
        ENDPOINT,
        data=json.dumps({"query": query}).encode(),
        headers={"Content-Type": "application/json",
                 "User-Agent": "alms-inference-env/bake_opentargets"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = json.load(r)
    if "errors" in body:
        raise RuntimeError(f"Open Targets API errors: {body['errors']}")
    return body["data"]


def load_or_fetch(refresh: bool = False) -> dict:
    if not refresh and CACHE.exists():
        return json.loads(CACHE.read_text())
    print(f"[fetch] {ENDPOINT} target={ENSEMBL_ID}", flush=True)
    t0 = time.time()
    payload = _fetch(QUERY)
    print(f"[fetch] {time.time()-t0:.1f}s → {CACHE.relative_to(REPO)}", flush=True)
    payload["_fetched_at"] = datetime.now(timezone.utc).isoformat()
    payload["_source_url"] = f"https://platform.opentargets.org/target/{ENSEMBL_ID}"
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps(payload, indent=2))
    return payload


def upsert(conn: sqlite3.Connection, data: dict) -> dict[str, int]:
    tgt = data["target"]
    now = data.get("_fetched_at", datetime.now(timezone.utc).isoformat())
    url = data.get("_source_url", f"https://platform.opentargets.org/target/{ENSEMBL_ID}")

    conn.execute("DELETE FROM opentargets_dmd_summary")
    conn.execute("DELETE FROM opentargets_dmd_tractability")
    conn.execute("DELETE FROM opentargets_dmd_pathway")
    conn.execute("DELETE FROM opentargets_dmd_disease")
    conn.execute("DELETE FROM opentargets_dmd_drug")
    conn.execute("DELETE FROM opentargets_dmd_interaction")

    conn.execute(
        "INSERT INTO opentargets_dmd_summary VALUES (?,?,?,?,?,?)",
        (tgt["id"], tgt["approvedSymbol"], tgt.get("approvedName"),
         tgt.get("biotype"), now, url),
    )

    tract_rows = [(t["modality"], t["label"], 1 if t["value"] else 0)
                  for t in (tgt.get("tractability") or [])]
    conn.executemany(
        "INSERT OR REPLACE INTO opentargets_dmd_tractability VALUES (?,?,?)",
        tract_rows,
    )

    pw_rows = [(p["pathwayId"], p["pathway"], p.get("topLevelTerm"))
               for p in (tgt.get("pathways") or [])]
    conn.executemany(
        "INSERT OR REPLACE INTO opentargets_dmd_pathway VALUES (?,?,?)",
        pw_rows,
    )

    ad = tgt.get("associatedDiseases") or {}
    dis_rows = []
    for row in (ad.get("rows") or []):
        dis = row.get("disease") or {}
        did = dis.get("id")
        if not did:
            continue
        dis_rows.append((did, dis.get("name") or did, float(row.get("score") or 0.0)))
    conn.executemany(
        "INSERT OR REPLACE INTO opentargets_dmd_disease VALUES (?,?,?)",
        dis_rows,
    )

    dr = tgt.get("drugAndClinicalCandidates") or {}
    drug_rows = []
    for row in (dr.get("rows") or []):
        drug = row.get("drug") or {}
        did = drug.get("id") or row.get("id")
        if not did:
            continue
        drug_rows.append((
            did,
            drug.get("name"),
            drug.get("drugType"),
            row.get("maxClinicalStage"),
            drug.get("maximumClinicalStage"),
        ))
    conn.executemany(
        "INSERT OR REPLACE INTO opentargets_dmd_drug VALUES (?,?,?,?,?)",
        drug_rows,
    )

    inter = tgt.get("interactions") or {}
    int_rows = []
    for row in (inter.get("rows") or []):
        pid = row.get("intB")
        if not pid:
            continue
        tb = row.get("targetB") or {}
        int_rows.append((
            pid,
            tb.get("approvedSymbol"),
            float(row.get("score") or 0.0),
            row.get("sourceDatabase") or "unknown",
        ))
    conn.executemany(
        "INSERT OR REPLACE INTO opentargets_dmd_interaction VALUES (?,?,?,?)",
        int_rows,
    )

    conn.commit()
    return {
        "tractability": len(tract_rows),
        "pathways":     len(pw_rows),
        "diseases":     len(dis_rows),
        "drugs":        len(drug_rows),
        "interactions": len(int_rows),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true",
                    help="re-fetch even if the cache file exists")
    args = ap.parse_args()

    if not DB.exists():
        raise SystemExit(f"missing {DB} — run build_mechanism_sqlite first")

    data = load_or_fetch(refresh=args.refresh)
    conn = sqlite3.connect(DB)
    conn.executescript(SCHEMA)
    counts = upsert(conn, data)

    tgt = data["target"]
    print(f"[opentargets] {tgt['approvedSymbol']} ({tgt['id']}) → {DB.relative_to(REPO)}")
    for k, v in counts.items():
        print(f"  {k:14s}  {v}")
    conn.close()


if __name__ == "__main__":
    sys.exit(main())
