import copy

from baebugs import compare as C


def _pack():
    leaves = [{"path": "a.py", "module": "code", "sha256": "1"}, {"path": "p.stl", "module": "prints", "sha256": "2"}]
    return {"root": "r", "modules": {"code": {"root": "c"}, "prints": {"root": "p"}}, "leaves": leaves}


def test_identical_stops_at_root():
    assert C.compare(_pack(), _pack())["identical"]


def test_break_point_is_the_changed_module():
    a, b = _pack(), copy.deepcopy(_pack())
    b["root"] = "r2"; b["modules"]["prints"]["root"] = "p2"; b["leaves"][1]["sha256"] = "9"
    b["leaves"].append({"path": "byo_tray.stl", "module": "prints", "sha256": "7"})
    r = C.compare(a, b, "claude", "byo")
    assert r["break_points"] == ["prints"] and r["modules"]["code"]["verdict"] == "SAME"
    assert r["modules"]["prints"]["DIFFERS"] == ["p.stl"] and r["modules"]["prints"]["ONLY_byo"] == ["byo_tray.stl"]
