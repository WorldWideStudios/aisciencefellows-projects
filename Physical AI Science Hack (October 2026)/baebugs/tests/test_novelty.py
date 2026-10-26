import itertools

import numpy as np

from baebugs.explore import (
    CAPTURE,
    HARDWARE,
    Ledger,
    compare_lomo_breakpoints,
    lomo,
    simulate_run,
)
from baebugs.novelty import mesh_gaps, novel_sizes, suggest_filters
from baebugs.preservation import part_risks
from baebugs.sieve import load_yaml

MAT = {m["id"]: m for m in load_yaml("materials.yaml")["materials"]}


def test_soft_parts_riskier_on_rough_mesh():
    hex_ = part_risks("scaled_wings", MAT["HEX-2"])
    nylon = part_risks("scaled_wings", MAT["NYLON-500"])
    beetle = part_risks("hard_bodied", MAT["HEX-2"])
    assert hex_["wings"] > nylon["wings"] and hex_["wings"] > beetle["body"]
    assert part_risks("scaled_wings", MAT["HEX-2"], preservation="dry")["wings"] > hex_["wings"]


def test_novel_size_detected():
    rng = np.random.default_rng(0)
    refL, refW = rng.uniform(4, 7, 200), rng.uniform(1.5, 2.2, 200)  # rice-like reference
    L = np.r_[rng.uniform(4, 7, 5), [2.5]]
    W = np.r_[rng.uniform(1.5, 2.2, 5), [0.9]]                       # one chia-like body
    res = novel_sizes(L, W, refL, refW)
    assert res[-1]["novel"] and sum(r["novel"] for r in res[:-1]) <= 1


def test_gap_and_filter_suggestion_prefers_gentle_for_wings():
    widths = [3.0, 3.1, 3.3, 2.9, 3.4]                # between HEX-2 (2.42) and GRID-4 (4.4)
    gaps = mesh_gaps(widths, [5.0, 4.0, 2.2, 1.2])
    assert gaps and gaps[0]["between_mm"][0] == 2.42
    kit_only = suggest_filters(gaps[0], "scaled_wings")
    assert all(s.get("in_kit", False) or s["material"] == "FABRICATE" for s in kit_only)
    sug = suggest_filters(gaps[0], "scaled_wings", include_procurable=True)
    assert sug[0]["aperture_mm"] < 4.0 and sug[0]["material"] in ("PRINT-SMOOTH-3", "PERF-3")
    assert sug[0]["damage_risk"] <= max(s["damage_risk"] for s in sug)


def test_ledger_lomo_breakpoints():
    bodies = [{"width_mm": w, "profile": "membrane_wings"} for w in np.linspace(1.4, 2.0, 20)]
    led = Ledger()
    for i, (f, h, c) in enumerate(itertools.product(
            ["SCREEN-1", "NET-MOSQ", "HEX-2"], HARDWARE, CAPTURE)):
        cfg = {"filter": f, "hardware": h, "capture": c, "flow": 0.5}
        led.append(cfg, simulate_run(cfg, bodies, (1.3, 2.1), seed=i))
    assert led.verify() and len(led.golden_path()) >= 1
    assert lomo(led, "filter")[0]["drop_if_removed"] >= 0
    rep = compare_lomo_breakpoints(led)
    assert set(rep) == {"filter", "hardware", "capture"}
    led.runs[0]["results"]["recovery"] = 1.0                    # tamper
    assert not led.verify()
