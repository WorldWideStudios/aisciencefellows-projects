from baebugs.custody_watch import Watcher
from baebugs.mmr import MMRLog
from baebugs.resolve import Store, dangling, record_breaks


def test_dangling_weights_reference_is_a_break(tmp_path):
    (tmp_path / "daisy").mkdir()
    w = tmp_path / "out" / "A_best.pt"; w.parent.mkdir(); w.write_bytes(b"weights-A")
    import hashlib
    ha = hashlib.sha256(b"weights-A").hexdigest(); hb = "b" * 64
    log = MMRLog(tmp_path / "daisy/impact_mmr.jsonl")
    log.append({"type": "execution", "protocol": "P", "run": "A", "weights_sha256": ha})
    log.append({"type": "execution", "protocol": "P", "run": "B", "weights_sha256": hb})   # never exported
    st = Store([tmp_path], cache=tmp_path / "idx.json").build()
    d = dangling(tmp_path, st)
    assert [x["sha"] for x in d] == [hb] and d[0]["contexts"] == ["P/B"]
    assert len(record_breaks(tmp_path, st)) == 1 and len(record_breaks(tmp_path, st)) == 0   # recorded once
    wt = Watcher(tmp_path, notify=False)
    s, _ = wt.cycle()
    assert s["overall"] == "BREAK" and any(k.startswith("resolve:bbbb") for k in s["checks"])
