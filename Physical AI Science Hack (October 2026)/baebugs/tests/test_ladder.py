import numpy as np

from baebugs import ladder as L
from baebugs import tiers as T
from baebugs.mmr import MMRLog


def _ladder(conf_taxon=0.95, conf_local=0.5):
    return [
        L.Rung("taxon:ORDER", "tensor:abc", lambda c: {"outcome": "APPROVE", "confidence": conf_taxon, "label": c["order"]},
               threshold=0.9, novelty_ceiling=0.9),
        L.Rung("local:qwen2.5vl:3b", "ollama:fb90", lambda c: {"outcome": "APPROVE", "confidence": conf_local}, threshold=0.8,
               novelty_ceiling=0.99),
        L.Rung("frontier:claude", "claude", lambda c: {"outcome": "HOLD" if c["novelty"] > 0.99 else "APPROVE", "confidence": 0.85},
               threshold=0.8),
        L.Rung("human", "entomologist", lambda c: {"outcome": "APPROVE", "confidence": 1.0}),
    ]


def test_ladder_escalates_on_novelty_and_scope():
    d, att = L.climb(_ladder(), {"order": "Coleoptera", "novelty": 0.5})
    assert d["decided_by"] == "taxon:ORDER" and len(att) == 1
    d, att = L.climb(_ladder(), {"order": "Coleoptera", "novelty": 0.995})
    assert d["decided_by"] == "frontier:claude" and d["outcome"] == "HOLD" and [a["result"] for a in att] == ["SKIP", "SKIP", "DECIDE"]
    d, _ = L.climb(_ladder(conf_taxon=0.5, conf_local=0.5), {"order": "Diptera", "novelty": 0.95})
    assert d["decided_by"] == "frontier:claude"


def test_chain_and_markov_are_deterministic(tmp_path):
    img = np.zeros((64, 64, 3), np.uint8)
    for path in (tmp_path / "a.jsonl", tmp_path / "b.jsonl"):
        log = MMRLog(path)
        for sid, nov in (("s1", 0.2), ("s2", 0.995), ("s3", 0.2)):
            frames, ctxs = {}, {}
            for step in ("sort", "image", "pick"):
                fr = T.frame(img, [{"id": sid, "bbox": [8, 8, 40, 40]}], meta={"step": step})
                frames[step] = [(T.summary(fr), fr["objects"][0])]
                ctxs[step] = [{"order": "Coleoptera", "family": "Coccinellidae", "novelty": nov, "filter": "HEX-2", "protocol": "P1"}]
            L.run_specimen(log, sid, frames, ctxs, _ladder())
    a, b = L.markov(L.load(tmp_path / "a.jsonl")), L.markov(L.load(tmp_path / "b.jsonl"))
    assert a["stats_sha256"] == b["stats_sha256"]
    assert MMRLog(tmp_path / "a.jsonl").records[-1]["root"] == MMRLog(tmp_path / "b.jsonl").records[-1]["root"]
    held = [t for t in a["transitions"] if t["from"] == "sort:HOLD"]
    assert held and held[0]["to"] == "END"            # the novel specimen stopped at the first step
    assert a["decided_by"]["Coccinellidae"]["taxon:ORDER"] == 6
