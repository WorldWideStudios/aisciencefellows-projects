"""Source-backed end-to-end static portal release checks; no hardware commands."""
from __future__ import annotations
from pathlib import Path
from tempfile import TemporaryDirectory
import hashlib
import json
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "baebugs_final_release_builder", ROOT / "site/mvp/build_public_site.py"
)
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)
build = builder.build

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def test_all_final_review_routes_source_pinned_and_private_media_excluded():
    with TemporaryDirectory() as d:
        site=Path(d)/"release"
        ref="f"*40
        manifest=build(site,ref)
        assert manifest["source_ref"]==ref
        assert manifest["evidence_pack_root"]==json.loads((site/"mvp.json").read_text())["root"]
        assert manifest["excluded_pr34_face_photos"] is True
        assert manifest["submitted_youtube_link"]=="SOURCE_REPORTED_NOT_INDEPENDENTLY_VERIFIED"
        assert manifest["reported_youtube_url"]=="https://youtu.be/O4Gq-r018cI"
        assert manifest["submitted_google_slides_link"]=="NOT_VERIFIED"
        for route in [
            "index.html","story/index.html","board/index.html","review/index.html",
            "demo/index.html","protocols/index.html","lab/index.html",
            "demo/mvp_walkthrough_45s.mp4",
            "demo/biokea_vs_baebugs_animation_30s.mp4",
            "demo/robot_animation_63s.mp4",
            "demo/research_reel_67s.mp4",
        ]:
            assert route in manifest["files"], route
            output=site/route
            assert sha(output.read_bytes())==manifest["files"][route]["sha256"]
        assert not any("slideshow" in f for f in manifest["files"])
        assert not any("photos" in f for f in manifest["files"])
        assert 'href="review/"' in (site/"index.html").read_text()
        assert 'href="story/"' in (site/"index.html").read_text()
        assert "/blob/mvp-kg/" not in (site/"board/index.html").read_text()
        assert "/blob/"+ref+"/" in (site/"board/index.html").read_text()
        assert 'NOT_TESTED' in (site/"review/index.html").read_text()
        assert 'NOT_SIGNED'==manifest["story_projection"]["signature"]
        assert manifest["story_projection"]["published_story_sha256"]==sha((site/"story/index.html").read_bytes())
        assert (ROOT/"site/story/index.html").is_file()
        assert all(not any(x.startswith(".") for x in path.split("/")) for path in manifest["files"])

def test_story_builder_writes_derived_target_without_mutating_repo():
    story_spec = importlib.util.spec_from_file_location(
        "baebugs_derived_story", ROOT / "site/story/build_story.py"
    )
    story_module = importlib.util.module_from_spec(story_spec)
    story_spec.loader.exec_module(story_module)
    story_build = story_module.build
    original=(ROOT/"site/story/index.html").read_bytes()
    with TemporaryDirectory() as tmp:
        dest=Path(tmp)/"story.html"
        story_build(dest)
        content=dest.read_text()
        pack=json.loads((ROOT/"site/mvp/mvp.json").read_text())
        assert '"root": "'+pack["root"]+'"' in content
    assert original==(ROOT/"site/story/index.html").read_bytes()
