import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"site/mvp"))
from build_public_site import H, build


def test_workflow_main_page_has_truthful_stage_and_twin():
    s=(ROOT/"site/mvp/index.html").read_text()
    for stage in ["intake","sort","disperse","pick","plate","evidence"]:
        assert 'data-stage="'+stage+'"' in s
    assert s.count('id="p-workflow"')==1
    assert 'src="../twin/"' in s
    assert 'data-twin-view="lab"' in s
    assert "NOT_TESTED" in s
    assert 'source(s); access requires original consent' in s

def test_packaging_keeps_twin_and_labware_with_no_person_photos():
    with TemporaryDirectory() as d:
        from pathlib import Path
        root=Path(d)/"site"
        m=build(root,"0"*40)
        assert m["source_ref"]=="0"*40
        for f in ["index.html","mvp.json","twin/index.html","lab/index.html",
                  "lab/lab.js","lab/parts.json","print/labware/previews.png","bench_observation.json"]:
            assert f in m["files"], f
            assert H(root/f)==m["files"][f]["sha256"]
        assert "source_ref" in (root/"deployment-manifest.json").read_text()
        assert "photos" not in [x.parent.name for x in root.rglob("*.jpg")]
        assert json.loads((root/"mvp.json").read_text())["root"]==m["evidence_pack_root"]

def test_virtual_twin_metrics_are_explicitly_simulated():
    twin=(ROOT/"site/twin/index.html").read_text()
    assert "Virtual checks pass" in twin
    assert "modeled recovery, not measured" in twin
    assert "specimens recovered</span>" not in twin

def test_private_photo_record_never_bundles_source_pixels():
    import json
    note=json.loads((ROOT/"docs/bench/bench_photo_observation_20261025.json").read_text())
    assert note["source"]["public_source_bytes"]=="WITHHELD"
    assert note["source"]["publication_consent"]=="UNKNOWN"
    assert len(note["source"]["sha256_exact_file_bytes"])==64

def test_bench_source_withheld_is_reported_as_custody_gap():
    from baebugs import mvp
    report=mvp.build(ROOT)
    assert report["custody"]["withheld_bench_sources"]
    assert report["custody"]["withheld_bench_sources"][0]["public_rehash"]=="NOT_AVAILABLE"
    assert report["custody"]["breaks"]==report["custody"]["result_breaks"]+report["custody"]["withheld_photo_breaks"]+len(report["custody"]["withheld_bench_sources"])

def test_public_manifest_excludes_local_vercel_link_metadata():
    with TemporaryDirectory() as d:
        root=Path(d)/"site"
        (root/".vercel").mkdir(parents=True)
        (root/".vercel/project.json").write_text('{"private":"link metadata"}')
        (root/".gitignore").write_text(".vercel\n")
        report=build(root,"0"*40)
        assert not any(any(part.startswith(".") for part in name.split("/")) for name in report["files"])
        assert ".vercel/project.json" not in report["files"]
