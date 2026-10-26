import json

from baebugs.custody_watch import Watcher
from baebugs.mmr import MMRLog


def _repo(tmp):
    d = tmp / "daisy"; d.mkdir()
    (d / "DAISY-BB-009.json").write_text('{"id": "DAISY-BB-009"}')
    log = MMRLog(d / "impact_mmr.jsonl")
    for i in range(3):
        log.append({"type": "x", "i": i})
    return d


def _levels(s):
    return {k: c["level"] for k, c in s["checks"].items()}


def test_detects_breaks_immediately(tmp_path):
    d = _repo(tmp_path)
    w = Watcher(tmp_path, notify=False)
    s, _ = w.cycle()
    assert _levels(s)["frozen:daisy/DAISY-BB-009.json"] == "OK" and _levels(s)["mmr:impact_mmr.jsonl"] == "OK"
    MMRLog(d / "impact_mmr.jsonl").append({"type": "x", "i": 3})            # legitimate append stays OK
    assert _levels(w.cycle()[0])["mmr:impact_mmr.jsonl"] == "OK"
    (d / "DAISY-BB-009.json").write_text('{"id": "DAISY-BB-009", "epochs": 99}')   # edit a frozen protocol
    s, ch = w.cycle()
    assert _levels(s)["frozen:daisy/DAISY-BB-009.json"] == "BREAK" and s["overall"] == "BREAK"
    assert any(e["to"] == "BREAK" and "frozen" in e["check"] for e in ch)


def test_history_rewrite_and_truncation(tmp_path):
    d = _repo(tmp_path); f = d / "impact_mmr.jsonl"
    w = Watcher(tmp_path, notify=False); w.cycle()
    lines = f.read_text().splitlines()
    # rewrite: rebuild a fully self-consistent log with record 1 changed (verify() alone would pass)
    f.unlink(); log = MMRLog(f)
    for i in range(3):
        log.append({"type": "x", "i": i if i != 1 else 42})
    assert MMRLog(f).verify()[0]
    assert _levels(w.cycle()[0])["mmr:impact_mmr.jsonl"] == "BREAK"
    w2 = Watcher(tmp_path, state_dir=tmp_path / "s2", notify=False)
    f.write_text("\n".join(lines) + "\n"); w2.cycle()
    f.write_text("\n".join(lines[:2]) + "\n")                                  # truncation
    assert "truncated" in w2.cycle()[0]["checks"]["mmr:impact_mmr.jsonl"]["reason"]


def test_event_chain_tamper_evident(tmp_path):
    d = _repo(tmp_path)
    w = Watcher(tmp_path, notify=False); w.cycle()
    (d / "DAISY-BB-009.json").write_text("{}"); w.cycle()
    assert w.verify_events()[0]
    ev = w.events_f.read_text().splitlines(); e = json.loads(ev[-1]); e["reason"] = "nothing to see"
    w.events_f.write_text("\n".join(ev[:-1] + [json.dumps(e)]) + "\n")
    assert not w.verify_events()[0] and w.status()["overall"] == "BREAK"
