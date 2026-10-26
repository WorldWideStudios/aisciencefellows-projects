from baebugs import print_parts as pp
from baebugs import trommel_plate as tp


def test_fits_x1c_and_trays(tmp_path):
    before = dict(pp.P)
    i = tp.build("x1c", tmp_path)
    assert pp.P == before                                      # global params restored
    assert i["fits_bed"] and not i["parts_overlap"] and all(f["watertight"] for f in i["files"])
    q = i["params"]
    assert q["zone_len"] >= max(t[0] for t in tp.TRAYS.values())        # one zone per tray, no overlap
    assert q["hole_band"] < min(t[0] for t in tp.TRAYS.values())        # fines land inside the narrower tray
    assert i["drum_bottom_above_bench_mm"] > max(t[2] for t in tp.TRAYS.values()) + 5
