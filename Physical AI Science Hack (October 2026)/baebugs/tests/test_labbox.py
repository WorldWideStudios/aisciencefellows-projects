from baebugs.labbox import ARMS, add_arm, build, lomo, route


def test_routes_cover_every_stage_and_lomo_finds_single_points_of_failure():
    g = build(".")
    for cls in ("routine", "vip", "novel"):
        r = route(g, cls)
        assert not r["breaks"] and all(s["platform"] for s in r["steps"])
    L = lomo(".")
    assert set(L["modules"]["vision_gate"]["stages_lost"]) == {"bench:image", "flex:image"}
    assert build(".", leave_out="turnstile_incubator")["root"] != g["root"]


def test_byo_arm_joins_the_graph():
    n0 = len(build(".")["edges"])
    add_arm("my_arm", {"interfaces": ["suction_pad"], "reach_mm": 250})
    try:
        assert len(build(".")["edges"]) > n0
    finally:
        ARMS.pop("my_arm")
