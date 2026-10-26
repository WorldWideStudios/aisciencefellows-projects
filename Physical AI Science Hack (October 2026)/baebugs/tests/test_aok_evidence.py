"""AoK source/atom/Merkle contract and adversarial negative controls."""
import copy
import importlib.util
import pathlib

REPO=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("aok",(REPO/"tools/aok_build.py"))
aok=importlib.util.module_from_spec(spec);spec.loader.exec_module(aok)
def test_complete_receipts_and_recomputed_tree():
    v=aok.verify()
    assert v["PASS"],v
    assert v["nodes"]==247 and v["edges"]==135
    assert v["source_files_rehashed"]>=25
    r=aok.read("site/aok/data/root.json")
    assert r["root"]==v["root"]
    assert r["signed"]=="NOT_SIGNED" and r["historical_mmr_commit"]=="NOT_COMPUTED"
def test_every_leaf_and_context_addressable():
    g=aok.read("site/aok/data/graph.json")
    assert len({n["id"] for n in g["nodes"]})==len(g["nodes"])
    for n in g["nodes"]:
        assert n["content_canonical_utf8"]==aok.canon(n["content"]).decode()
        assert n["context_canonical_utf8"]==aok.canon(n["context"]).decode()
        assert n["fco_id"]=="fco:sha256:"+aok.h(n["content_canonical_utf8"].encode())
        assert n["occurrence_id"]=="occ:sha256:"+aok.h(n["context_canonical_utf8"].encode())
def test_part_bytes_match_registry_and_rights_are_not_overwritten():
    g=aok.read("site/aok/data/graph.json")
    parts=[n for n in g["nodes"] if n["type"]=="part"]
    assert len(parts)==24
    for p in parts:assert aok.fpath(p["source_path"])==p["source_sha256"]==p["details"]["sha256_from_manifest"]
    labels={n["id"]:n["license"] for n in g["nodes"] if n["type"]=="source"}
    assert labels["source:baebugs"]=="MIT"
    assert labels["source:bugpicker"]=="GPL-3.0"
    assert labels["source:bugsorter"]=="UNKNOWN"
    assert labels["source:entosieve"]=="UNKNOWN"
def test_negative_leaf_tamper_detected():
    g=aok.read("site/aok/data/graph.json")
    mutated=copy.deepcopy(g["nodes"])
    mutated[0]["body"]="INJECTED_FALSE_CLAIM"
    newroot,_,_=aok.tree(mutated)
    assert newroot!=g["root"]
def test_negative_wrong_sibling_and_root_detected():
    r=aok.read("site/aok/data/root.json")
    e=copy.deepcopy(r["ordered_leaves"][0])
    assert aok.proof_ok(e["sha256"],e["proof"],r["root"])
    e["proof"][0]["hash"]="0"*64
    assert not aok.proof_ok(e["sha256"],e["proof"],r["root"])
    assert not aok.proof_ok(r["ordered_leaves"][0]["sha256"],r["ordered_leaves"][0]["proof"],"f"*64)
def test_negative_source_drift_detected_without_editing_real_source(monkeypatch,tmp_path):
    true_hash=aok.fpath
    def changed(path):
        return "0"*64 if path=="LICENSE" else true_hash(path)
    monkeypatch.setattr(aok,"fpath",changed)
    result=aok.verify()
    assert not result["PASS"]
    assert "SOURCE_DRIFT:LICENSE" in result["errors"]
def test_graph_not_claim_causality():
    g=aok.read("site/aok/data/graph.json")
    assert all("from" in edge and "to" in edge and "type" in edge for edge in g["edges"])
    r=aok.read("site/aok/data/root.json")
    assert len(r["references"])==2
    assert all(x["type"]=="DECLARED_NOT_MERGED" for x in r["references"])
    n=next(n for n in g["nodes"] if n["id"]=="claim:novel")
    assert n["status"]=="NOT_TESTED"
def test_no_restricted_media_in_public_site():
    site=REPO/"site/aok"
    assert not list(site.rglob("*.pt"))
    assert not list(site.rglob("*.tif"))
    assert not list(site.rglob("*.tiff"))
    assert not list(site.rglob("*.fastq"))
    assert not list(site.rglob("*.fasta"))


def test_every_fcg_relation_has_included_leaf():
    g=aok.read("site/aok/data/graph.json")
    r=aok.read("site/aok/data/root.json")
    index={n["id"]:n for n in g["nodes"]}
    assert len([n for n in g["nodes"] if n["type"]=="fcg_edge"])==135
    for e in g["edges"]:
        x=index[e["atom_id"]]
        payload={k:e[k] for k in ("from","to","type","status")}
        assert x["details"]["relationship"]==payload
        assert x["details"]["relationship_sha256"]==aok.h(aok.canon(payload))
        proof=next(z for z in r["ordered_leaves"] if z["id"]==e["atom_id"])
        assert aok.proof_ok(proof["sha256"],proof["proof"],r["root"])

def test_adversarial_relation_retcon_detection(monkeypatch):
    read_orig=aok.read
    def compromised(path):
        g=read_orig(path)
        if path=="site/aok/data/graph.json":
            g["edges"][0]["type"]="SILENT_CAUSAL_CLAIM"
        return g
    monkeypatch.setattr(aok,"read",compromised)
    report=aok.verify()
    assert not report["PASS"]
    assert any(s.startswith("EDGE_ATOM_MISMATCH:") for s in report["errors"])
