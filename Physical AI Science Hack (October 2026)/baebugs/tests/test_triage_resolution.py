import numpy as np

from baebugs.measure import Measurement
from baebugs.resolution import at_megapixels, leave_one_resolution_out
from baebugs.triage import summarize, triage


def M(L, W, conf=0.9, flag=None):
    return Measurement(0, 0, L, W, L * W, "consensus", conf, flag=flag)


def test_unknown_vs_novel_vs_known():
    rng = np.random.default_rng(0)
    refL, refW = rng.uniform(5, 15, 400), rng.uniform(2, 6, 400)
    ms = [M(10, 4),                         # known
          M(10, 4, conf=0.2),               # unknown: low confidence
          M(10, 4, flag="width_disagree_40%"),  # unknown: sizers disagree
          M(28, 1.0),                       # novel: long and thin, far from database
          M(28, 1.0, conf=0.2)]             # low-confidence outlier -> unknown, not VIP
    a = triage(ms, refL, refW)
    assert [x.status for x in a] == ["known", "unknown", "unknown", "novel", "unknown"]
    assert a[3].priority == "VIP" and a[1].priority == "normal"
    assert summarize(a) == {"known": 1, "unknown": 3, "novel": 1, "vip": 1}


def test_gap_taxa_make_novel():
    refL, refW = np.full(50, 10.0) + np.arange(50) * 0.01, np.full(50, 4.0)
    a = triage([M(10, 4)], refL, refW, gap_taxa_hit=True)
    assert a[0].status == "novel" and "collection-gap" in a[0].reasons[0]


def test_megapixel_resample_keeps_mm_scale():
    img = np.zeros((3000, 4000, 3), np.uint8)
    out, ppm, s = at_megapixels(img, 3.0, px_per_mm=40.0)
    assert abs(out.shape[0] * out.shape[1] / 1e6 - 3.0) < 0.05
    assert abs(ppm - 40.0 * s) < 1e-9 and s < 1


def test_lomo_resolution():
    sw = {"0.3MP": {"yolo": {"median_wid_err": 0.20}}, "3MP": {"yolo": {"median_wid_err": 0.05}},
          "12MP": {"yolo": {"median_wid_err": 0.04}}}
    r = leave_one_resolution_out(sw)
    assert r["0.3MP"]["delta"] > 0 > r["12MP"]["delta"]
