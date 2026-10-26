import numpy as np

from baebugs import tiers as T


def _img(seed=0, h=100, w=150):
    return np.random.default_rng(seed).integers(0, 255, (h, w, 3), dtype=np.uint8)


def test_deterministic_and_single_root():
    a, b = T.frame(_img(), meta={"step": "image"}), T.frame(_img(), meta={"step": "image"})
    assert a["root"] == b["root"] and len(a["tiers"][max(a["tiers"])]) == 1
    assert T.frame(_img(), meta={"step": "pick"})["root"] != a["root"]   # same pixels, different step -> different frame


def test_diff_finds_only_the_changed_region():
    img = _img(); img2 = img.copy(); img2[40:50, 70:90] = 0
    objs = [{"id": "s1", "bbox": [60, 30, 100, 60], "label": "Coleoptera"}, {"id": "s2", "bbox": [5, 5, 20, 20]}]
    a, b = T.frame(img, objs), T.frame(img2, objs)
    d = T.diff(a, b)
    assert not d["identical"] and d["break_boxes"] == [[64, 32, 96, 64]]
    assert d["objects"]["changed"] == ["s1"]                  # s1 covers the changed tiles, s2 does not
    assert d["nodes_compared"] < d["nodes_total"]             # equal subtrees were skipped
    assert T.diff(a, T.frame(img, objs))["identical"]


def test_pixel_proof():
    img = _img(); fr = T.frame(img)
    p = T.prove_pixel(img, fr, 123, 77)
    assert T.verify_pixel(p)
    p["pixel"] = [0, 0, 0] if p["pixel"] != [0, 0, 0] else [1, 1, 1]
    assert not T.verify_pixel(p)
