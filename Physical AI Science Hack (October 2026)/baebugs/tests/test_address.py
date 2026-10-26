import json
from pathlib import Path

from baebugs import address as AD


def test_recipe_ignores_noise_and_realizations_differ():
    p = json.loads(Path("daisy/DAISY-BB-001b.json").read_text())
    info = AD.information("truth", p["roots"])
    r1 = AD.recipe(info["address"], p, p["runs"][2])
    p2 = dict(p); p2["settings"] = {**p["settings"], "seed": 7, "workers": 2}
    assert AD.recipe(info["address"], p2, p["runs"][2])["address"] == r1["address"]   # seed/workers are noise here
    a, b = AD.realization(r1["address"], "w1"), AD.realization(r1["address"], "w2")
    assert a["address"] != b["address"]
    ba = AD.behaviour(a["address"], {"map": 0.61}, {"abs": 0.03})
    bb = AD.behaviour(b["address"], {"map": 0.63}, {"abs": 0.03})
    assert AD.equivalent(ba, bb, {"abs": 0.03})["equivalent"]
    assert not AD.equivalent(ba, AD.behaviour(b["address"], {"map": 0.5}, {}), {"abs": 0.03})["equivalent"]
