from baebugs import attest as A


def test_claim_id_moves_with_policy_and_logic():
    c1 = A.claim({"mask": "h1"}, "euler = components - holes", "topology.euler@abc", 3, {"abs": 0})
    c2 = A.claim({"mask": "h1"}, "euler = components - holes", "topology.euler@abc", 3, {"abs": 1})
    c3 = A.claim({"mask": "h1"}, "euler = components - holes", "topology.euler@def", 3, {"abs": 0})
    assert len({c1["id"], c2["id"], c3["id"]}) == 3 and A.verify_claim(c1)


def test_multi_verifier_status_and_tamper(tmp_path):
    code = A.actor("code", "baebugs.topology.skeleton_counts", "abc", key="abc", self_or_nonself="self")
    m1, m2, hu = A.actor("model", "gemini-3-flash"), A.actor("model", "qwen3:1.7b"), A.actor("human", "reviewer", key="pk1")
    c = A.claim({"mask": "h1"}, "legs visible", "count", {"legs": 6, "length_mm": 13.5},
                {"abs": 0.0, "length_mm": {"abs": 0.2}}, {"deterministic_required": True, "min_agents": 2, "quorum": 0.66})
    led = A.AttestationLedger(tmp_path / "a.jsonl")
    for r in (code, m1, m2, hu, c):
        led.add(r)
    leaves = [A.attest(c, code, {"legs": 6, "length_mm": 13.6}), A.attest(c, m1, {"legs": 6, "length_mm": 13.4}),
              A.attest(c, m2, {"legs": 4, "length_mm": 12.0})]
    assert leaves[0]["within_policy"] and leaves[1]["within_policy"] and not leaves[2]["within_policy"]
    assert A.status(c, leaves) == "DISPUTED"                       # 1 of 2 agents agree < 0.66
    leaves.append(A.attest(c, hu, {"legs": 6, "length_mm": 13.5}))
    assert A.status(c, leaves) == "SUPPORTED"                      # 2 of 3 agents agree
    for l in leaves:
        led.add(l)
    r = led.roots()
    assert r["tampered"] == [] and r["status_counts"] == {"SUPPORTED": 1}
    bad = dict(leaves[1]); bad["observed"] = {"legs": 8, "length_mm": 1}
    assert not A.verify_leaf(bad)
    assert A.status(c, [A.attest(c, code, {"legs": 5, "length_mm": 13.5})]) == "FAILED"
