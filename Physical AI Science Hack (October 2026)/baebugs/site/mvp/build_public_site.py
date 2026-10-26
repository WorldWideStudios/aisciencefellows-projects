"""Deterministically stage Baebugs MVP root, bench twin, CAD/STL viewer and labware.

Derived deployment files are not a new Merkle root; the included source pack
remains pinned and separately validated by repo source identity.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil

REPO = Path(__file__).resolve().parents[2]

def H(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1024*1024),b''):
            h.update(b)
    return h.hexdigest()

def build(target: Path, source_ref: str):
    if not re.fullmatch(r"[0-9a-f]{40}", source_ref):
        raise ValueError("Source revision must be a full verified Git commit SHA")
    target=target.resolve()
    if target == REPO or REPO in target.parents:
        raise ValueError("Output must be outside repository to avoid evidence recursion")
    target.mkdir(parents=True, exist_ok=True)
    html=(REPO/"site/mvp/index.html").read_text()
    marker="const BASE = new URL('../../', location.href);"
    assert html.count(marker)==1
    html=html.replace(marker,
        "const BASE = new URL('https://raw.githubusercontent.com/biobitworks/baebugs/"+source_ref+"/');")
    assert 'id="workflow-twin"' in html
    assert 'id="p-workflow"' in html
    (target/"index.html").write_text(html)
    shutil.copy2(REPO/"site/mvp/mvp.json",target/"mvp.json")
    shutil.copy2(REPO/"docs/bench/bench_photo_observation_20261025.json",target/"bench_observation.json")
    for rel in ["site/lab","site/twin","site/protocols","site/detection"]:
        d=target/Path(rel).name
        if d.exists():
            shutil.rmtree(d)
        shutil.copytree(REPO/rel,d,ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    # Public protocols are source-verified derived projections, not execution proof.
    import sys
    sys.path.insert(0, str(REPO / "site/protocols"))
    from build_catalog import build as compile_protocols
    resolved = compile_protocols(REPO, target/"mvp.json")
    resolved["source_commit"] = source_ref
    (target/"protocols/catalog.json").write_text(
        json.dumps(resolved, indent=2, ensure_ascii=False, sort_keys=True)+chr(10))
    # Public PA12 toy bounding boxes are recorded inference, not new model runs.
    sys.path.insert(0, str(REPO / "site/detection"))
    from build_detection import build_gallery
    detections = build_gallery(REPO, target / "detection", source_ref, target / "mvp.json")
    shutil.copy2(
        REPO / "docs/toy_photo_models/pa12_toys_two_on_floor_models.jpg",
        target / "detection" / "preview.jpg"
    )
    # The 3D labware preview and Opentrons schemas linked by the Parts tab.
    for rel in ["print/labware/previews.png"]:
        dest = target / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / rel, dest)
    sh=REPO/"print/labware/opentrons"
    if sh.exists():
        d=target/"print/labware/opentrons"
        if d.exists():
            shutil.rmtree(d)
        shutil.copytree(sh,d)
    # Build the story in the derived output, never over the committed predecessor.
    # The story refers to the source graph root but its bytes differ from the
    # committed older story occurrence, which is recorded below.
    sys.path.insert(0, str(REPO / "site/story"))
    from build_story import build as compile_story
    story_out = target / "story" / "index.html"
    compile_story(story_out)
    committed_story = REPO / "site/story/index.html"

    # Portal board has older mvp-kg branch links. Pin browsing to this exact
    # source commit, without rewriting historical source files.
    board_out = target / "board" / "index.html"
    board_out.parent.mkdir(parents=True, exist_ok=True)
    board_html = (REPO / "site/board/index.html").read_text()
    board_html = board_html.replace("/blob/mvp-kg/", "/blob/" + source_ref + "/")
    board_html = board_html.replace("/raw/mvp-kg/", "/raw/" + source_ref + "/")
    board_out.write_text(board_html)

    # Publish only already-present, explicitly classified repo-owned media.
    # In particular, do not ingest PR #34 or other user/team face photos.
    videos = [
        ("docs/demo/baebugs_mvp_demo.mp4", "mvp_walkthrough_45s.mp4", 44.64,
         "Silent screen walkthrough; software only; older counts shown inside the recording"),
        ("docs/workflow_video/biokea_vs_baebugs_v2.mp4", "biokea_vs_baebugs_animation_30s.mp4", 30.0,
         "Silent CAD animation; not real hardware footage"),
        ("docs/sieving_robot/sieving_demo.mp4", "robot_animation_63s.mp4", 62.65,
         "Silent animation; exceeds event 60-second limit; purity figures illustrative"),
        ("docs/demo/baebugs_reel.mp4", "research_reel_67s.mp4", 66.60,
         "Soundtrack and over-length; not compliant with event footage requirement"),
    ]
    media_out = target / "demo"
    media_out.mkdir(parents=True, exist_ok=True)
    for original, dest, duration, note in videos:
        shutil.copy2(REPO / original, media_out / dest)

    import html as html_module
    media_cards = "".join(
        '<article><h2>' + html_module.escape(dest.replace("_", " ").replace(".mp4", "")) +
        '</h2><p>' + html_module.escape(note) +
        '</p><video controls muted preload="metadata" playsinline src="' +
        html_module.escape(dest, quote=True) +
        '" width="600"></video><p><a href="' + html_module.escape(dest, quote=True) +
        '">Open video file</a></p></article>'
        for original, dest, duration, note in videos
    )
    (media_out / "index.html").write_text(
        '<!doctype html><html lang="en"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Baebugs · video evidence review</title>'
        '<style>body{font:16px system-ui;background:#0a191d;color:#e9f4eb;'
        'max-width:1050px;margin:2rem auto;padding:0 1rem}'
        'article{border:1px solid #48695e;border-radius:12px;'
        'margin:20px 0;padding:16px}video{max-width:100%;height:auto}'
        'a{color:#a9efce}</style>'
        '<h1>Video review · software evidence vs physical validation</h1>'
        '<p>No independently verified unedited physical sorting video is '
        'included in this source. Animation and software footage do not '
        'establish specimen recovery.</p>' + media_cards +
        '<p><a href="../story/">Seven-stage story</a> · '
        '<a href="../">Evidence homepage</a> · '
        '<a href="https://github.com/biobitworks/baebugs/blob/main/docs/SUBMISSION_LINKS.md">'
        'Submission source ledger</a></p></html>'
    )

    # A video URL supplied in merged source is not evidence of duration,
    # unlisted visibility or hardware demonstration; display its status clearly.
    submitted_links_text = (REPO / "docs/SUBMISSION_LINKS.md").read_text()
    yt_matches = re.findall(r"https://youtu\.be/[A-Za-z0-9_-]{11}", submitted_links_text)
    source_youtube_url = yt_matches[0] if yt_matches else None
    external_youtube_status = (
        "SOURCE_REPORTED_NOT_INDEPENDENTLY_VERIFIED" if source_youtube_url
        else "NOT_PROVIDED"
    )
    youtube_markup = (
        '<a href="' + html_module.escape(source_youtube_url, quote=True) +
        '" target="_blank" rel="noopener noreferrer">'
        'Team-reported YouTube video (external, unverified)</a>'
        if source_youtube_url else "No YouTube link recorded in source ledger"
    )
    review_out = target / "review" / "index.html"
    review_out.parent.mkdir(parents=True, exist_ok=True)
    pack = json.loads((target / "mvp.json").read_text())
    review_out.write_text(
        '<!doctype html><html lang="en"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Baebugs · final publication review</title>'
        '<style>body{font:16px system-ui;background:#0a191d;color:#e9f4eb;'
        'max-width:970px;margin:2rem auto;padding:0 1rem}'
        'a{color:#a9efce}li{margin:.8rem 0}code{overflow-wrap:anywhere}</style>'
        '<h1>Baebugs · publication review</h1><p>Source commit <code>' + source_ref +
        '</code>; snapshot root <code>' + html_module.escape(pack["root"]) +
        '</code>; ' + str(len(pack["leaves"])) +
        ' addressable leaves; ' + str(pack["custody"]["breaks"]) +
        ' declared custody gaps. The published website is a derived projection '
        'and is <strong>not a new signed MMR commitment</strong>.</p>'
        '<ol><li><a href="../story/">End-to-end BioKEA story</a></li>'
        '<li><a href="../demo/">Four video assets, with compliance boundaries</a></li>'
        '<li><a href="../protocols/">Discover, save, and remix protocols</a></li>'
        '<li><a href="../board/">Specimen workflow board</a></li>'
        '<li><a href="../lab/">3D printed parts</a></li>'
        '<li><a href="../detection/">Model bounding-box evidence</a></li>'
        '<li><a href="../">Root-to-leaf evidence graph</a></li>'
        '<li><a href="https://github.com/biobitworks/baebugs/blob/main/docs/SUBMISSION_LINKS.md">'
        'Repository submission index</a></li></ol>'
        '<p><strong>Submission gates:</strong> The GitHub ledger reports '
        + youtube_markup + '. The external video content and visibility are '
        'NOT_INDEPENDENTLY_VERIFIED. A Google Slides submission URL is not '
        'recorded. A 14-slide extended deck and autoplay slideshows do not '
        'satisfy the maximum five-slide requirement.</p>'
        '<p>Physical arm transfer, calibrated purity and specimen recovery: '
        '<strong>NOT_TESTED</strong>. Photo permissions stay source-specific. '
        'Open PR #34 contains face-bearing imagery and is not included here.</p>'
        '<p><a href="../deployment-manifest.json">Verify every deployed byte</a></p>'
        '</html>'
    )
    detector_preview = (
        '<section aria-labelledby="bbox-home-title" style="display:grid;'
        'grid-template-columns:repeat(auto-fit,minmax(min(100%,260px),1fr));'
        'gap:16px;margin:18px 0;padding:18px;border:1px solid #527469;'
        'border-radius:12px;background:#152f31;color:#e7f7eb">'
        '<div><span style="font-size:10px;letter-spacing:.16em;color:#91e2bd">'
        'IMAGE ANALYSIS / RECORDED MODEL PREDICTIONS</span>'
        '<h2 id="bbox-home-title" style="margin:10px 0;letter-spacing:-.04em">'
        'See the bounding boxes. Trace the evidence.</h2>'
        '<p style="font-size:12px;max-width:660px;color:#bdd6c7">'
        'Compare YOLOE and OWLv2 on real photographs of printed PA12 toy insects.'
        ' Adjust model confidence thresholds and inspect each source atom.'
        ' Accuracy and biological identity remain NOT_VERIFIED.</p>'
        '<a style="display:inline-block;padding:11px 15px;background:#c0eed0;'
        'border-radius:8px;color:#184035;text-decoration:none;font-size:12px;'
        'font-weight:750" href="detection/">Explore bounding boxes →</a>'
        '</div><a href="detection/" aria-label="Open recorded object detection">'
        '<img alt="Source-recorded blue and amber bounding boxes around two'
        ' 3D printed toy insects" src="detection/preview.jpg" loading="lazy"'
        ' style="width:100%;height:205px;object-fit:cover;object-position:center 40%;'
        'border:1px solid #54786f;border-radius:9px"></a></section>'
    )
    marker = '<section class="protocol-discovery-entry"'
    homepage = (target / "index.html").read_text()
    assert homepage.count(marker) == 1, "Homepage placement drift"
    badge = (
        '<aside aria-label="Submission review" style="border:1px solid #77b39c;'
        'background:#123436;color:#e6f2eb;padding:15px 19px;'
        'border-radius:10px;margin:18px 0">'
        '<strong>BioKEA · end-to-end team review</strong> · '
        '<a style="color:#b7f1d3" href="review/">Publication review</a> · '
        '<a style="color:#b7f1d3" href="story/">Seven-stage story</a> · '
        '<a style="color:#b7f1d3" href="demo/">Demo videos</a> · '
        '<a style="color:#b7f1d3" href="board/">Protocol Board</a>. '
        'Hardware recovery remains NOT_TESTED.</aside>'
    )
    (target / "index.html").write_text(homepage.replace(marker, badge + detector_preview + marker, 1))

    # Do not package source photos withheld for licensing or consent.
    assert not (target/"assets/photos").exists()
    (target/"robots.txt").write_text("User-agent: *\nAllow: /\n")
    files={}
    for p in sorted(target.rglob("*")):
        if p.is_file() and p.name!="deployment-manifest.json" and not any(x.startswith(".") for x in p.relative_to(target).parts):
            files[p.relative_to(target).as_posix()]={"sha256":H(p),"bytes":p.stat().st_size}
    manifest={"schema":"baebugs.portal.deployment-manifest.v1",
              "source_ref":source_ref,"evidence_pack_root":json.loads((target/"mvp.json").read_text())["root"],
              "status":"DERIVED_DEPLOYMENT_PACKAGE", "signed":"NOT_SIGNED",
              "files":files,"included_people_photos":False,
              "reproduces_physical_robot_execution":False,
              "story_projection":{
                "source_story_sha256":H(committed_story),
                "published_story_sha256":H(story_out),
                "derived_from_current_source_data":True,
                "canonical_source_story_modified":False,
                "signature":"NOT_SIGNED"
              },
              "recorded_bounding_box_photo_count":len(detections["images"]),
              "model_inference_on_deployment":"NOT_EXECUTED",
              "detector_ground_truth":"NOT_VERIFIED",
              "excluded_pr34_face_photos":True,
              "submitted_google_slides_link":"NOT_VERIFIED",
              "submitted_youtube_link":external_youtube_status,
              "reported_youtube_url":source_youtube_url}
    (target/"deployment-manifest.json").write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
    return manifest

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--out",type=Path,required=True)
    ap.add_argument("--ref",required=True)
    args=ap.parse_args()
    m=build(args.out,args.ref)
    print(json.dumps({"root":m["evidence_pack_root"],"file_count":len(m["files"]),
                      "manifest_sha256":H(args.out/"deployment-manifest.json"),"staged_to":str(args.out)}))
if __name__ == "__main__":
    main()
