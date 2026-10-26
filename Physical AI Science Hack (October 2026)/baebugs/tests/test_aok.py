from pathlib import Path

from baebugs import aok

REPO = Path(__file__).resolve().parents[1]


def test_aok_deterministic_and_complete():
    a, b = aok.build(REPO), aok.build(REPO)
    assert a["root"] == b["root"]
    assert aok.check(a, REPO) == []
    assert all(x["licence"] for x in a["leaves"] + a["external"])
    # weights-producing code carries the AGPL term; upstream pins are never claimed
    train = next(x for x in a["leaves"] if x["path"] == "baebugs/train.py")
    assert "ext:ultralytics" in train["terms"] and train["claim"] == aok.OWN_T
    assert all(e["claim"] == aok.THIRD for e in a["external"])
    assert not any(x["path"] in aok.INDEX_FILES for x in a["leaves"])


def test_leaf_changes_with_licence():
    x = {"path": "p", "sha256": "0" * 64, "claim": aok.OWN, "licence": "MIT", "status": "built"}
    assert aok.leaf_hash(x) != aok.leaf_hash({**x, "licence": "MIT + ultralytics terms"})
