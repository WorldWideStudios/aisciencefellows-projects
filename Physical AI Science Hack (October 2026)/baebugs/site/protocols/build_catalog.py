"""Compile a source-verified, browsable protocol projection from immutable repo AoK.

A compiled recipe is a DERIVED catalog object. It references canonical file
leaves; its content hash identifies exact data but DOES NOT amend the repo's
Merkle root or claim physical execution. BYO client records never enter here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
VALID_STATUSES = {
    "IMPLEMENTED_SOFTWARE", "DESIGN_NOT_VALIDATED", "PHYSICAL_RESULT_NOT_TESTED",
    "MODEL_ONLY", "VIRTUAL_PREFLIGHT_ONLY", "HARDWARE_NOT_TESTED",
    "SOURCE_ACCESS_VARIES", "SOFTWARE_IMPLEMENTED", "EXPLORATORY_RESULTS"
}

def canonical(v):
    return json.dumps(v, sort_keys=True, separators=(",",":"),ensure_ascii=False,allow_nan=False).encode("utf-8")

def H(content):
    return hashlib.sha256(content).hexdigest()

def sha_file(f):
    return H(Path(f).read_bytes())

def build(repo=REPO, pack_path=None):
    repo=Path(repo).resolve()
    pack_path=Path(pack_path) if pack_path else repo/"site/mvp/mvp.json"
    mvp=json.loads(pack_path.read_text())
    source=repo/"protocols/catalog.json"
    catalog=json.loads(source.read_text())
    if catalog["schema"]!="baebugs.protocol_library.v1":
        raise ValueError("Unsupported protocol source schema")
    by_path={x["path"]:x for x in mvp["leaves"]}
    if len(by_path)!=len(mvp["leaves"]):
        raise ValueError("MVP has duplicate canonical path addresses")
    recipes=[]
    ids=set()
    for entry in catalog["recipes"]:
        if not re.fullmatch(r"[a-z][a-z0-9-]{2,70}",entry["id"]) or entry["id"] in ids:
            raise ValueError(f"Duplicate or invalid protocol ID {entry['id']!r}")
        ids.add(entry["id"])
        if entry["status"] not in VALID_STATUSES:
            raise ValueError("Unsupported evidence state")
        if not entry["steps"] or not entry["sources"] or not entry["rights_note"]:
            raise ValueError(f"Missing steps, rights or sources for {entry['id']}")
        atoms=[]
        for path in entry["sources"]:
            item=by_path.get(path)
            if not item:
                raise ValueError(f"Unbound source leaf: {entry['id']}/{path}")
            actual=repo/path
            if not actual.is_file() or sha_file(actual)!=item["sha256"]:
                raise ValueError(f"Source drift from published AoK: {entry['id']}/{path}")
            atoms.append({
                "path":path,
                "sha256":item["sha256"],
                "leaf":item["leaf"],
                "licence":item["licence"],
                "claim":item["claim"],
                "status":item["status"]
            })
        for step in entry["steps"]:
            if step["source"] not in entry["sources"]:
                raise ValueError(f"Step source not declared: {entry['id']}/{step['source']}")
            if step["gate"] not in {"REVIEW_ONLY","OPERATOR_REVIEW","HUMAN_EVIDENCE_REVIEW"}:
                raise ValueError("Unsupported execution permission")
        content_sha=H(canonical(entry))
        occurrence={
            "context":"BAEBUGS_PUBLIC_PROTOCOL_DISCOVERY",
            "evidence_pack_root":mvp["root"],
            "template_content_sha256":content_sha,
            "source_leaf_hashes":[x["leaf"] for x in atoms],
        }
        recipes.append({
            **entry,
            "content_sha256":content_sha,
            "context_sha256":H(canonical(occurrence)),
            "source_atoms":atoms,
            "evidence_root":mvp["root"],
            "execution_permission":"GUIDED_BROWSER_REVIEW_ONLY",
            "signed":"NOT_SIGNED"
        })
    # The edge list is independently addressable as a derived projection.
    # These declared source links do not amend the canonical DAISY hypergraph/MMR.
    relationships=[]
    for recipe in recipes:
        for atom in recipe["source_atoms"]:
            edge={"kind":"REFERENCES_SOURCE_ATOM",
                  "from":"protocol:"+recipe["id"]+":"+recipe["content_sha256"],
                  "to":"leaf:"+atom["path"],
                  "source_sha256":atom["sha256"],
                  "source_leaf":atom["leaf"],
                  "context_pack_root":mvp["root"]}
            relationships.append({**edge,"edge_sha256":H(canonical(edge))})
    registry_leaf=by_path.get("protocols/catalog.json")
    if not registry_leaf or registry_leaf["sha256"]!=sha_file(source):
        raise ValueError("Source registry not committed into current AoK")
    return {
        "schema":"baebugs.protocol_discovery_projection.v1",
        "status":"DERIVED_FROM_SOURCE_VERIFIED_AOK",
        "evidence_root":mvp["root"],
        "catalog_leaf":registry_leaf["leaf"],
        "catalog_source_sha256":registry_leaf["sha256"],
        "source_commit":"PIN_AT_DEPLOYMENT",
        "rights":"Every source atom has its own licence and claim state; aggregated summaries confer no additional rights.",
        "execution_limit":"Only a local browser checklist and source identity validation. No robot, laboratory device, assay, training job or specimen is run.",
        "relationships":relationships,
        "relationships_status":"DERIVED_TYPED_EDGES_NOT_MMR_COMMITTED",
        "recipes":recipes
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",required=True,type=Path)
    p.add_argument("--source-commit",required=True)
    args=p.parse_args()
    d=build()
    if not re.fullmatch(r"[0-9a-f]{40}",args.source_commit):
        raise ValueError("Commit ref must be full 40-character hex SHA")
    d["source_commit"]=args.source_commit
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(d,indent=2,ensure_ascii=False,sort_keys=True)+"\n")
    print(json.dumps({"root":d["evidence_root"],"templates":len(d["recipes"]),"catalog_leaf":d["catalog_leaf"],"file_sha256":sha_file(args.out)}))

if __name__=="__main__":main()
