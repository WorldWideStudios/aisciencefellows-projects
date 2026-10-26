import json

from baebugs import local_vlm
from baebugs.synth_seg import build_dataset
from baebugs.train import bench


def test_synth_dataset_and_classical_bench(tmp_path):
    d = build_dataset(tmp_path / "s", n_train=2, n_val=8, seed=3)
    lines = (d / "labels" / "train" / "train_00000.txt").read_text().strip().splitlines()
    assert lines and all(l.startswith("0 ") and len(l.split()) >= 7 for l in lines)
    truth = json.loads((d / "truth_val.json").read_text())
    assert truth[0]["objects"] and "width_mm" in truth[0]["objects"][0]
    r = bench(None, d / "truth_val.json")
    assert r["classical"]["median_wid_err"] < 0.25 and r["n_true"] > 0   # 1-30 mm incl. legs: harder


def test_ollama_adapter_offline(monkeypatch):
    assert local_vlm.available("definitely-not-a-model") is False
    monkeypatch.setattr(local_vlm, "chat_json", lambda p, img=None, model=None: {"ok_to_sieve": True})
    import numpy as np
    assert local_vlm.read_label(np.zeros((10, 10, 3), np.uint8))["ok_to_sieve"]
