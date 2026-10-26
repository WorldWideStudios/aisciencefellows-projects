from baebugs import calbug

FAKE = {
    "occurrence/search": {"count": 100, "facets": [{"field": "FAMILY_KEY", "counts": [
        {"name": "1", "count": 60}, {"name": "2", "count": 40}]}]},
    "species/1": {"canonicalName": "Chironomidae"},
    "species/2": {"canonicalName": "Carabidae"},
}


def test_composition_and_prior(monkeypatch):
    monkeypatch.setattr(calbug, "_get", lambda path, **kw: FAKE[path])
    comp = calbug.family_composition("Alameda")
    assert comp == {"Chironomidae": 60, "Carabidae": 40}
    mix = calbug.expected_class_mix(comp)
    assert abs(sum(mix.values()) - 1) < 1e-9 and mix["tiny"] > 0.5


def test_compare_flags_mismatch():
    exp = {"tiny": 0.7, "small": 0.2, "medium": 0.1}
    assert not calbug.compare(exp, [0.5] * 7 + [1.5] * 2 + [3.0])["flag"]
    assert calbug.compare(exp, [6.0] * 10)["flag"]
