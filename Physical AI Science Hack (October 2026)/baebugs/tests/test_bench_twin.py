import copy

from baebugs import bench_twin as BT
from baebugs import tower_twin as TT
from baebugs.sieve import load_yaml


def test_tree_hash_and_fail_closed():
    tw = BT.BenchTwin()
    r0 = tw.state_root()
    assert r0 == BT.BenchTwin().state_root()                       # same config -> same state hash
    plan = TT.plan_tiers(TT.demo_objects()[:60], TT.tower_inventory(), load_yaml("tower.yaml"), 2)
    acts = TT.actions_for(plan["best"], load_yaml("tower.yaml"), TT.initial_state(load_yaml("tower.yaml"), TT.tower_inventory()))
    res = tw.run_actions(acts)
    assert res["status"] in ("EXECUTED", "STOPPED_AT_BREAK_POINT") and res["actions"] >= 1
    cfg = copy.deepcopy(load_yaml("tower.yaml")); cfg["arm"]["reach_mm"] = 600.0
    tw2 = BT.BenchTwin(cfg=cfg)
    assert tw2.run_actions(acts)["status"] == "EXECUTED"           # longer reach -> the same plan clears every check
