import json
import shutil
import subprocess
from pathlib import Path

import pytest

from baebugs import mvp

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def pack():
    return mvp.build(REPO)


def test_pack_levels_have_addresses(pack):
    assert pack["root"] and pack["roots"]["aok"] and pack["roots"]["hypergraph"]
    assert all(b["leaf"] for b in pack["bugs"]) and all(p["leaf"] for p in pack["parts"])
    assert mvp.get(pack, "root")["root"] == pack["root"]
    assert mvp.get(pack, "leaf:LICENSE")["claim"] == "OWN"
    assert mvp.get(pack, "module:daisy-results")["leaves"]
    assert all(r["leaf"] for r in pack["remixes"])          # printable labware remixes resolve to STL leaves


def test_prove_matches_and_differs(pack):
    fco = mvp.fco_of(["LICENSE"], REPO)
    fco["leaves"].append({"path": "README.md", "sha256": "0" * 64})
    att = mvp.prove(pack, fco)
    assert [r["verdict"] for r in att["rows"]] == ["MATCH", "DIFFERS"] and att["graph_root"] == pack["root"]


@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
def test_npx_surface_same_answer(tmp_path, pack):
    f = tmp_path / "mvp.json"; f.write_text(json.dumps(pack))
    # run the node bin against this pack by placing it where the bin looks
    site = tmp_path / "site/mvp"; site.mkdir(parents=True); (site / "mvp.json").write_text(json.dumps(pack))
    (tmp_path / "bin").mkdir(); shutil.copy(REPO / "bin/baebugs.mjs", tmp_path / "bin/baebugs.mjs")
    out = subprocess.run(["node", str(tmp_path / "bin/baebugs.mjs"), "get", "leaf:LICENSE"], capture_output=True, text=True, check=True)
    assert json.loads(out.stdout) == mvp.get(pack, "leaf:LICENSE")
