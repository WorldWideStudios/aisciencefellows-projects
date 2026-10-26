from baebugs import watch_commit as W


def test_summary_falls_back_deterministically(monkeypatch):
    def boom(*a, **k):
        raise OSError("no local model here")
    monkeypatch.setattr(W, "_post", boom)
    s, route, prompt = W.summarise(" daisy/x.json | 2 +-\n kg/aok.json | 4 ++--\n")
    assert route == "deterministic" and s.startswith("update 2 file(s)") and "daisy/x.json" in prompt
