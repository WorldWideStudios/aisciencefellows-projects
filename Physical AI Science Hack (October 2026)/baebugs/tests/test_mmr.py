import hashlib

from baebugs.mmr import MMR, MMRLog


def _l(i):
    return hashlib.sha256(str(i).encode()).hexdigest()


def test_mmr_proofs_hold_after_growth(tmp_path):
    m = MMR()
    for i in range(13):
        m.append(_l(i))
        for j in range(i + 1):
            assert MMR.verify(m.proof(j), m.root)
    p = m.proof(3); p["leaf"] = _l(99)
    assert not MMR.verify(p, m.root)
    log = MMRLog(tmp_path / "x.jsonl")
    for i in range(5):
        log.append({"event": i})
    assert MMRLog(tmp_path / "x.jsonl").verify() == (True, None)
