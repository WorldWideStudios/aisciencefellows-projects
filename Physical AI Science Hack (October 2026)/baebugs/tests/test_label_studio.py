import json

from baebugs import label_studio as LS


def test_roundtrip_only_human_annotations(tmp_path):
    exp = [{"data": {"photo_id": "p1", "published_sha256": "ab"},
            "predictions": [{"result": [{"type": "rectanglelabels", "original_width": 200, "original_height": 100,
                                         "value": {"x": 10, "y": 10, "width": 50, "height": 50, "rectanglelabels": ["rack"]}}]}],
            "annotations": [{"completed_by": 1, "updated_at": "t", "result": [
                {"type": "rectanglelabels", "original_width": 200, "original_height": 100,
                 "value": {"x": 25, "y": 50, "width": 50, "height": 25, "rectanglelabels": ["plate"]}}]}]}]
    f = tmp_path / "export.json"; f.write_text(json.dumps(exp))
    (tmp_path / "daisy").mkdir()
    rec = LS.import_confirmed(f, out="labels.json", repo=tmp_path)
    labels = json.loads((tmp_path / "labels.json").read_text())["labels"]
    assert rec["n"] == 1 and labels[0]["label"] == "plate" and labels[0]["bbox"] == [50, 50, 150, 75]
    assert "<RectangleLabels" in LS.config_xml()
