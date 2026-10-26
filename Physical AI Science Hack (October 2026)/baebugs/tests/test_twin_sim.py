import json
import shutil
import subprocess

import pytest

NODE = shutil.which("node")


@pytest.mark.skipif(not NODE, reason="node not installed")
def test_js_twin_matches_python_passage_rule():
    js = """const S=require('./dashboard/twin/sim.js');
    console.log(JSON.stringify([S.passes([20,6,1],1.5,'slot'),S.passes([20,6,1],1.5,'square'),S.passes([2,1.4,1],2,'round')]));"""
    out = json.loads(subprocess.run([NODE, "-e", js], capture_output=True, text=True, check=True).stdout)
    from baebugs.variable_aperture import passes
    assert out == [passes((20, 6, 1), 1.5, 19.05, mode="slot"), passes((20, 6, 1), 1.5, 19.05, mode="square"),
                   passes((2, 1.4, 1), 2, 19.05, mode="square")]
