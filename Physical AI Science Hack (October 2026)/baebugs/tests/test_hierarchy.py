from baebugs.hierarchy import (
    UNPLACED,
    attest_label,
    build,
    leave_one_level_out,
    partition,
    with_expert,
)

M = [{"id": f"s{i}", "size": s, "order": o, "species": sp} for i, (s, o, sp) in enumerate([
    ("L", "Coleoptera", "a"), ("L", "Coleoptera", "b"), ("L", "Diptera", "c"),
    ("S", "Diptera", "d"), ("S", "Diptera", "d"), ("S", None, "e")])]
LV = [("size", lambda m: m["size"]), ("morphology", lambda m: m["order"]), ("barcode", lambda m: m["species"])]


def test_tree_hash_commits_to_assignments():
    t1, nov = build(M, LV)
    assert [n["id"] for n in nov] == ["s5"] and nov[0]["level"] == "morphology"
    M2 = [dict(m) for m in M]; M2[0]["species"] = "z"
    assert build(M2, LV)[0]["hash"] != t1["hash"]


def test_lolo_shows_contribution():
    r = leave_one_level_out(M, LV)
    assert r["levels"]["barcode"]["groups_lost"] > 0               # DNA splits what morphology cannot
    assert r["levels"]["size"]["identical_partition"] in (True, False)


def test_expert_confirmation_resolves_novelty_and_rehashes():
    t1, _ = build(M, LV)
    m = [dict(x) for x in M]
    attest_label(m[5], "morphology", "Hymenoptera", "expert:austin")
    lv = [LV[0], ("morphology", with_expert(LV[1][1], "morphology")), LV[2]]
    t2, nov = build(m, lv)
    assert not nov and t2["hash"] != t1["hash"]
    assert not any(UNPLACED in str(g) for g in partition(t2))
