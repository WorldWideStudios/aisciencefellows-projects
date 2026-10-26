import pytest

from baebugs import punch_filters as PF
from baebugs import tower_twin as TT
from baebugs.sieve import load_yaml


def test_p_pass_orientations():
    cfg = load_yaml("tower.yaml")
    inv = {f["id"]: f for f in TT.tower_inventory()}
    grain = {"length_mm": 6.5, "width_mm": 2.3}                    # rice-like
    assert TT.p_pass(grain, inv["SS-SLOT-3.2x19"], cfg) == 1.0       # lies flat along the slot
    assert TT.p_pass(grain, inv["SS-PERF-3.2"], cfg) < 1.0           # round hole: end-on only
    assert TT.p_pass({"length_mm": 7.0, "width_mm": 6.0}, inv["SS-PERF-3.2"], cfg) == 0.0


def test_plan_and_emulate_fail_closed():
    objs = TT.demo_objects()[:80]
    r = TT.run(objs)
    assert r["plan"]["best"]["tiers"] and r["seconds"] > 0 and len(r["run_root"]) == 64
    cfg = load_yaml("tower.yaml")
    inv = TT.tower_inventory()
    st = TT.initial_state(cfg, inv)
    bad = [("insert", {"tray": "SCREEN-1", "filter_slot": 2}), ("insert", {"tray": "PERF-5", "filter_slot": 1})]
    with pytest.raises(TT.PreflightError):
        TT.emulate(bad, cfg, st, inv)                                # fine above coarse


def test_metal_library():
    ids = {e[0] for e in PF.LIBRARY}
    assert {"SS-PERF-3.2", "SS-SLOT-3.2x19", "SS-MESH-1.0"} <= ids
    assert PF.spec(next(e for e in PF.LIBRARY if e[0] == "SS-PERF-3.2"))["materials"]
