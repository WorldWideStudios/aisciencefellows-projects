import hashlib
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

ROOT=Path(__file__).resolve().parents[1]
MODULE=ROOT/"site/protocols/build_catalog.py"
spec=importlib.util.spec_from_file_location("baebugs_protocol_builder",MODULE)
builder=importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)

def test_nine_curated_source_linked_templates():
    registry=json.loads((ROOT/"protocols/catalog.json").read_text())
    assert len(registry["recipes"])==9
    ids=[x["id"] for x in registry["recipes"]]
    assert len(ids)==len(set(ids))
    assert all(x["steps"] and x["sources"] and x["rights_note"] for x in registry["recipes"])
    pack=json.loads((ROOT/"site/mvp/mvp.json").read_text())
    derived=builder.build(ROOT)
    assert derived["evidence_root"]==pack["root"]
    assert len(derived["recipes"])==9
    assert len(derived["relationships"])==sum(len(x["sources"]) for x in registry["recipes"])
    assert all(x["execution_permission"]=="GUIDED_BROWSER_REVIEW_ONLY" for x in derived["recipes"])
    assert derived["relationships_status"]=="DERIVED_TYPED_EDGES_NOT_MMR_COMMITTED"
    for r in derived["recipes"]:
        raw={k:v for k,v in r.items() if k not in
             {"content_sha256","context_sha256","source_atoms","evidence_root","execution_permission","signed"}}
        assert builder.H(builder.canonical(raw))==r["content_sha256"]
        assert not r["signed"] or r["signed"]=="NOT_SIGNED"
        for atom in r["source_atoms"]:
            assert hashlib.sha256((ROOT/atom["path"]).read_bytes()).hexdigest()==atom["sha256"]
    for edge in derived["relationships"]:
        d={k:v for k,v in edge.items() if k!="edge_sha256"}
        assert builder.H(builder.canonical(d))==edge["edge_sha256"]

def test_source_drift_fails_closed(monkeypatch):
    original=builder.sha_file
    def altered(f):
        if Path(f).name=="camera.py":
            return "0"*64
        return original(f)
    monkeypatch.setattr(builder,"sha_file",altered)
    with pytest.raises(ValueError, match="Source drift"):
        builder.build(ROOT)

def test_curated_source_rights_and_deployment():
    import sys
    sys.path.insert(0,str(ROOT/"site/mvp"))
    from build_public_site import build
    with TemporaryDirectory() as d:
        root=Path(d)/"site"
        m=build(root,"f"*40)
        for p in ["index.html","protocols/index.html","protocols/app.js",
                  "protocols/styles.css","protocols/catalog.json","mvp.json",
                  "lab/index.html","twin/index.html"]:
            assert p in m["files"],p
        web=json.loads((root/"protocols/catalog.json").read_text())
        assert web["source_commit"]=="f"*40
        assert web["evidence_root"]==m["evidence_pack_root"]
        assert all(x["source_atoms"] for x in web["recipes"])
        assert all(x["rights_note"] for x in web["recipes"])
        js=(root/"protocols/app.js").read_text()
        assert "physical_execution" in js and "NOT_TESTED" in js
        assert "localStorage" in js
        assert "GUIDED_BROWSER_REVIEW_ONLY" in js
        assert "crypto.subtle" in js
        assert not any("__pycache__" in f or f.endswith(".pyc") for f in m["files"])
        assert "collection:" in js
        assert "My collections" in js

def test_main_page_has_discovery_first_without_removing_evidence_gates():
    html=(ROOT/"site/mvp/index.html").read_text()
    assert html.index('id="proto-entry-heading"')<html.index('id="roots"')
    assert 'action="../protocols/"' in html
    assert 'id="custody"' in html
    assert 'id="workflow-twin"' in html
