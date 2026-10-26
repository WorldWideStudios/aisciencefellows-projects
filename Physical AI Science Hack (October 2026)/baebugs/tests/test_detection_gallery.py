"""Published bounding boxes are sourced from existing PA12 toy photo records."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "baebugs_detection_builder", ROOT / "site/detection/build_detection.py"
)
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


def test_recorded_boxes_match_exact_source_bytes_and_context():
    gallery = builder.compile_detection(ROOT)
    pack = json.loads((ROOT / "site/mvp/mvp.json").read_text())
    assert gallery["source_evidence_root"] == pack["root"]
    assert gallery["human_labels"] == "NOT_VERIFIED"
    assert gallery["inference_execution_this_build"] == "NOT_EXECUTED"
    assert gallery["physical_specimen_recovery"] == "NOT_TESTED"
    assert gallery["mmr_commit"] == "NOT_COMPUTED"
    assert len(gallery["images"]) == 2
    counts = [[len([p for p in e["model_predictions"] if p["model"] == m])
               for m in ("yoloe", "owlv2")] for e in gallery["images"]]
    assert counts == [[3, 4], [0, 1]]
    for entry in gallery["images"]:
        atom = entry["source_photo"]
        assert atom["path"].startswith("assets/photos/pa12_toys_")
        assert hashlib.sha256((ROOT / atom["path"]).read_bytes()).hexdigest() == atom["sha256"]
        for detection in entry["model_predictions"]:
            assert detection["content_sha256"] != detection["context_sha256"]
            assert detection["status"] == "RECORDED_INFERENCE_NOT_GROUND_TRUTH"
            x, y, x2, y2 = detection["bbox_xyxy_pixels"]
            assert 0 <= x < x2 <= entry["width"]
            assert 0 <= y < y2 <= entry["height"]
            assert detection["scientific_identity"] == "NOT_VERIFIED"
            assert detection["physical_recovery"] == "NOT_TESTED"


def test_detection_image_export_strips_exif_and_preserves_coordinates():
    with TemporaryDirectory() as folder:
        target = Path(folder) / "viewer"
        ref = "a" * 40
        gallery = builder.build_gallery(ROOT, target, ref, ROOT / "site/mvp/mvp.json")
        assert gallery["source_commit"] == ref
        for entry in gallery["images"]:
            img_file = target / entry["image_path"]
            assert builder.sha_file(img_file) == entry["web_image_sha256"]
            with Image.open(img_file) as img:
                assert img.size == (entry["width"], entry["height"])
                assert not img.getexif()
        data = json.loads((target / "detections.json").read_text())
        assert data["publication_scope"] == "REPOSITORY_PUBLIC_SOURCE_PHOTOS_WITHOUT_PERSONS"
        assert data["live_webcam"] == "NOT_CONNECTED"


def test_gallery_fails_closed_on_photo_drift(monkeypatch):
    normal = builder.sha_file

    def alter(path):
        if Path(path).name == "pa12_toys_two_on_floor.jpg":
            return "0" * 64
        return normal(path)

    monkeypatch.setattr(builder, "sha_file", alter)
    with pytest.raises(ValueError, match="Detection source hash drift"):
        builder.compile_detection(ROOT)


def test_source_bound_publication_paths():
    import importlib.util as util
    spec = util.spec_from_file_location("baebugs_pub", ROOT / "site/mvp/build_public_site.py")
    mod = util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    with TemporaryDirectory() as folder:
        out = Path(folder) / "site"
        report = mod.build(out, "b" * 40)
        for name in ["detection/index.html", "detection/app.js", "detection/style.css",
                     "detection/detections.json", "detection/images/pa12_toys_two_on_floor.webp",
                     "detection/images/pa12_toys_box.webp", "detection/preview.jpg"]:
            assert name in report["files"]
            assert mod.H(out / name) == report["files"][name]["sha256"]
        assert report["recorded_bounding_box_photo_count"] == 2
        assert report["model_inference_on_deployment"] == "NOT_EXECUTED"
        assert report["detector_ground_truth"] == "NOT_VERIFIED"
        assert 'href="detection/"' in (out / "index.html").read_text()
        assert 'href="../detection/"' in (out / "review/index.html").read_text()
