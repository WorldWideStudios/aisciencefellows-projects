from pathlib import Path

from baebugs import assets

REPO = Path(__file__).resolve().parents[1]


def test_asset_db_deterministic_and_honest():
    a, b = assets.build(REPO), assets.build(REPO)
    assert a["root"] == b["root"] and a["n_assets"] == len(assets.ASSETS)
    for x in a["assets"]:
        assert x["photo_sha256"] and x["dims_source"] in {"spec", "design", "ruler-photo", "not measured"}
        if x["dims_source"] == "not measured":
            assert not x.get("dims_mm")          # no number without a source
