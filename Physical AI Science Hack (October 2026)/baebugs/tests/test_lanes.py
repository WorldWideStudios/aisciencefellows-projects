import json

from baebugs.bugpicker_bridge import (
    manifest_record,
    object_records,
    read_bugpicker_objects,
    write_scan,
)
from baebugs.measure import classical_measure
from baebugs.provenance import Provenance
from baebugs.sieve import plan_stack
from baebugs.sieve_calibrate import measure_aperture, synthetic_mesh
from baebugs.synthetic import make_sample


def test_mesh_calibration_square_and_round():
    for ap, rnd in [(1.2, False), (2.2, False), (5.0, True)]:
        r = measure_aperture(synthetic_mesh(ap, 0.4, 30, round_holes=rnd), 30)
        assert abs(r["aperture_mm"] - ap) / ap < 0.08, (ap, r)


def test_kit_plan_uses_real_frames_and_catch_tray():
    # rice-ish (1.5-2 mm wide), chia (~1 mm), pasta (5+ mm)
    plan = plan_stack([1.0, 1.1, 1.6, 1.8, 2.0, 5.5, 6.0])
    ids = [s.sieve_id for s in plan.steps]
    assert ids[-1] == "TRAY" and plan.passthrough_expected == 0
    aps = [s.aperture_mm for s in plan.steps]
    assert aps == sorted(aps, reverse=True)


def test_bugpicker_roundtrip(tmp_path):
    img, _ = make_sample(n=8, px_per_mm=40, seed=3)
    ms = classical_measure(img, 40)
    fr = manifest_record("frames/frame_00000.png", 0, 40, img.shape, "small", 2)
    write_scan(tmp_path, [fr], object_records(ms, fr))
    rows = [json.loads(l) for l in (tmp_path / "objects.jsonl").read_text().splitlines()]
    assert rows[0]["tray_size_class"] == "small" and rows[0]["sorting_tray_slot"] == 2
    back = read_bugpicker_objects(tmp_path / "objects.jsonl")
    assert abs(back[0].width_mm - ms[0].width_mm) < 1e-6


def test_provenance_chain(tmp_path):
    p = Provenance(tmp_path / "prov.jsonl")
    p.record("measure", "S1", {"a": 1})
    p.record("plan", "S1")
    p.record("measure", "S2")
    assert p.verify() and len(p.trace("S1")) == 2
    lines = (tmp_path / "prov.jsonl").read_text().splitlines()
    tampered = json.loads(lines[0]); tampered["params"]["a"] = 2
    lines[0] = json.dumps(tampered)
    (tmp_path / "prov.jsonl").write_text("\n".join(lines) + "\n")
    assert not p.verify()
