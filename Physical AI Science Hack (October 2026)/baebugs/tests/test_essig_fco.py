import cv2

from baebugs.bugpicker_bridge import (
    export_yolo,
    manifest_record,
    object_records,
    write_scan,
)
from baebugs.essig_adapter import (
    gbif_fco,
    label_fco,
    page_fco,
    parse_label,
    specimen_context,
    vision_label_fco,
    vision_prompt_context,
)
from baebugs.fco import FCO
from baebugs.measure import classical_measure
from baebugs.synthetic import make_sample

LABEL = """CA: Alameda Co., Tilden Regional Park
37.8968, -122.2453  320 m
12 VI 2019  coll. J. Smith  malaise
EMEC1005585"""


def test_fco_id_is_content_addressed():
    a, b = FCO("x", "s", {"k": 1}), FCO("x", "s", {"k": 1})
    assert a.id == b.id and FCO("x", "s", {"k": 2}).id != a.id


def test_parse_label():
    f = parse_label(LABEL)
    assert f["lat_long"] == [37.8968, -122.2453] and f["specimen_no"] == "EMEC1005585"
    assert f["method"].lower() == "malaise" and f["collector"].startswith("J. Smith")
    assert "Tilden" in f["locality"]


def test_hybridize_priority_and_conflicts():
    lab = label_fco(LABEL)
    gb = gbif_fco({"key": 1, "catalogNumber": "EMEC1005585", "family": "Carabidae",
                   "decimalLatitude": 37.8968, "decimalLongitude": -122.2453,
                   "preparations": "pin", "locality": "Tilden Park"})
    vis = vision_label_fco({"locality": "Tilden Pk (smudged)", "family": "Staphylinidae"},
                           "claude", "ab" * 32)
    gaps = FCO("essig_page:gaps", "u", {"gap_items": ["Carabidae of the Sierra", "Diptera: Mycetophilidae"]})
    ctx = specimen_context(vis, gb, lab, gaps=gaps)
    assert ctx.fields["family"] == "Carabidae"               # museum record beats vision guess
    assert ctx.fields["locality"].startswith("CA: Alameda")  # label is highest priority
    assert any(c["field"] == "family" for c in ctx.fields["_conflicts"])
    assert ctx.fields["gap_novelty_boost"] and len(ctx.parents) == 4
    assert "date" not in ctx.fields["missing"] and "Carabidae" in vision_prompt_context(ctx)


def test_blocked_pages_are_explicit_without_fetch():
    p = page_fco("gaps")                    # no saved file, no live fetch
    assert p.status == "unknown" and p.fields["gap_items"] == []


def test_yolo_export(tmp_path):
    img, _ = make_sample(n=6, px_per_mm=40, seed=4)
    (tmp_path / "scan" / "frames").mkdir(parents=True)
    cv2.imwrite(str(tmp_path / "scan" / "frames" / "f0.png"), img)
    fr = manifest_record("frames/f0.png", 0, 40, img.shape, "small")
    write_scan(tmp_path / "scan", [fr], object_records(classical_measure(img, 40), fr))
    out = export_yolo(tmp_path / "scan", tmp_path / "yolo", val_every=99)
    lines = (out / "labels" / "train" / "f0.txt").read_text().split()
    assert len(lines) == 6 * 5 and all(0 <= float(v) <= 1 for v in lines[1:5])
    assert (out / "images" / "train" / "f0.png").exists()
