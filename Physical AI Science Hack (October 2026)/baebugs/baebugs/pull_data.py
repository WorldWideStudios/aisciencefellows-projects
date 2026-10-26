"""Pull real data in parallel (runs on magicstudio; stdlib + concurrency).

Streams (each its own thread pool / process, all at once):
  essig    - Essig Museum DwC-A archive from GBIF (dataset 5d283bb6-...): full
             taxonomy/locality/preparation table for priors and FCO context
  images   - openly licensed (CC0 / CC-BY) PRESERVED_SPECIMEN insect images from
             GBIF for California (museum specimens ~ preserved samples), downloaded
             concurrently with per-image licence + attribution recorded
  bugpicker- shallow clone of github.com/biokea/BugPicker (trays, scripts, any sample scans)

Every file gets a provenance record (URL, licence, sha256) so it can become an
FCO. Respects robots/terms by using the GBIF API and original media URLs only.

  python -m baebugs.pull_data --root /Volumes/magicLABbox/baebugs --images 2000 --workers 12
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import subprocess
import time
import urllib.parse
import urllib.request
from pathlib import Path

GBIF = "https://api.gbif.org/v1"
ESSIG = "5d283bb6-64dd-4626-8b3b-a4e8db5415c3"
UA = {"User-Agent": "baebugs/0.1 (+https://github.com/biobitworks/baebugs)"}
OPEN_LICENSES = ("CC0_1_0", "CC_BY_4_0")


def _get_json(path, retries=6, **params):
    """GBIF API call with backoff on 429/5xx (honours Retry-After)."""
    import urllib.error
    url = f"{GBIF}/{path}?{urllib.parse.urlencode(params, doseq=True)}"
    for k in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504) or k == retries - 1:
                raise
            wait = float(e.headers.get("Retry-After") or 2 ** k)
            time.sleep(min(wait, 60))


def _download(url, dest: Path, retries=3, timeout=60):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return hashlib.sha256(dest.read_bytes()).hexdigest()
    for k in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = r.read()
            dest.write_bytes(data)
            return hashlib.sha256(data).hexdigest()
        except Exception:  # noqa: BLE001 - fallback; the failure is recorded or degrades
            time.sleep(1.5 * (k + 1))
    return None


# ---------- stream 1: Essig DwC-A ----------

def pull_essig(root: Path, log):
    out = root / "datasets" / "essig"
    eps = _get_json(f"dataset/{ESSIG}/endpoint")
    dwca = [e["url"] for e in eps if e.get("type") == "DWC_ARCHIVE"]
    meta = _get_json(f"dataset/{ESSIG}")
    (out).mkdir(parents=True, exist_ok=True)
    (out / "dataset.json").write_text(json.dumps(meta, indent=1))
    sha = _download(dwca[0], out / "essig_dwca.zip", timeout=600) if dwca else None
    log("essig", {"url": dwca[0] if dwca else None, "sha256": sha, "license": meta.get("license")})
    if sha:
        return out / "essig_dwca.zip"
    return pull_essig_facets(root, log)   # IPT down -> rebuild the prior table from the GBIF API


def pull_essig_facets(root: Path, log, workers=3, family_limit=300):
    """Family x county (GADM level 2) x order counts for the Essig collection,
    counties queried in parallel. This is the table the Calbug prior needs."""
    out = root / "datasets" / "essig"
    counties = _get_json("occurrence/search", datasetKey=ESSIG, limit=0,
                         facet="gadmLevel2Gid", facetLimit=500)["facets"][0]["counts"]

    def one(c):
        res = _get_json("occurrence/search", datasetKey=ESSIG, gadmGid=c["name"], limit=0,
                        facet=["familyKey", "orderKey", "preparations", "lifeStage"],
                        facetLimit=family_limit)
        return c, {f["field"]: f["counts"] for f in res.get("facets", [])}

    rows, keys = [], set()
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        for c, facets in ex.map(one, counties):
            rows.append({"gadm2": c["name"], "n": c["count"], **facets})
            keys |= {x["name"] for x in facets.get("FAMILY_KEY", [])}
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:   # resolve names in parallel
        names = dict(zip(keys, ex.map(lambda k: _get_json(f"species/{k}").get("canonicalName", k), keys)))
    for r in rows:
        r["families"] = {names.get(x["name"], x["name"]): x["count"] for x in r.pop("FAMILY_KEY", [])}
    (out / "essig_family_by_county.json").write_text(json.dumps(rows))
    log("essig_facets", {"counties": len(rows), "families": len(keys),
                         "records": sum(r["n"] for r in rows), "source": "GBIF API facets"})
    return out / "essig_family_by_county.json"


# ---------- stream 2: specimen images ----------

def _occurrence_pages(n_images, state, extra, start=0):
    got, offset = 0, start
    while got < n_images:
        res = _get_json("occurrence/search", classKey=216, mediaType="StillImage",
                        basisOfRecord="PRESERVED_SPECIMEN", stateProvince=state,
                        license=list(OPEN_LICENSES), limit=300, offset=offset, **extra)
        rows = res.get("results", [])
        if not rows:
            return
        for r in rows:
            for m in r.get("media", []):
                if m.get("type") == "StillImage" and m.get("identifier"):
                    yield r, m
                    got += 1
                    break
            if got >= n_images:
                return
        offset += len(rows)
        if res.get("endOfRecords"):
            return


def pull_images(root: Path, n_images, workers, log, state="California", extra=None, start=0,
                subdir="gbif_specimen_images"):
    """Downloads start as soon as each search page arrives (search and
    downloads overlap instead of running back to back)."""
    out = root / "datasets" / subdir
    (out / "images").mkdir(parents=True, exist_ok=True)
    ok = queued = 0
    with cf.ThreadPoolExecutor(max_workers=workers) as ex, \
            (out / "manifest.jsonl").open("a") as man:
        futs = {}
        for r, m in _occurrence_pages(n_images, state, extra or {}, start):
            ext = ".png" if m["identifier"].lower().endswith(".png") else ".jpg"
            dest = out / "images" / f"{r['key']}{ext}"
            meta = {"gbifID": r["key"], "url": m["identifier"], "license": r.get("license"),
                    "rightsHolder": m.get("rightsHolder") or r.get("rightsHolder"),
                    "creator": m.get("creator"), "institutionCode": r.get("institutionCode"),
                    "catalogNumber": r.get("catalogNumber"), "scientificName": r.get("scientificName"),
                    "order": r.get("order"), "family": r.get("family"), "file": dest.name}
            futs[ex.submit(_download, m["identifier"], dest)] = meta
            queued += 1
        for f in cf.as_completed(futs):
            meta = futs[f]
            meta["sha256"] = f.result()
            if meta["sha256"]:
                ok += 1
                man.write(json.dumps(meta) + "\n"); man.flush()
    log("images", {"requested": n_images, "queued": queued, "downloaded": ok})
    return ok


# ---------- stream 3: BugPicker ----------

def pull_bugpicker(root: Path, log):
    dest = root / "datasets" / "BugPicker"
    if not dest.exists():
        subprocess.run(["git", "clone", "--depth", "1", "https://github.com/biokea/BugPicker",
                        str(dest)], check=False, capture_output=True)
    files = sum(1 for _ in dest.rglob("*") if _.is_file()) if dest.exists() else 0
    log("bugpicker", {"path": str(dest), "files": files, "license": "GPL-3.0"})
    return dest


def main(argv=None):
    ap = argparse.ArgumentParser("baebugs-pull")
    ap.add_argument("--root", default="/Volumes/magicLABbox/baebugs")
    ap.add_argument("--images", type=int, default=2000)
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--state", default="California")
    ap.add_argument("--only", nargs="*", default=["essig", "images", "bugpicker"])
    ap.add_argument("--start", type=int, default=0, help="GBIF search offset (resume past earlier pulls)")
    ap.add_argument("--subdir", default="gbif_specimen_images")
    a = ap.parse_args(argv)
    root = Path(a.root)
    logf = root / "datasets" / "pull_log.jsonl"
    logf.parent.mkdir(parents=True, exist_ok=True)

    def log(stream, rec):
        rec = {"t": time.time(), "stream": stream, **rec}
        with logf.open("a") as f:
            f.write(json.dumps(rec) + "\n")
        print(json.dumps(rec), flush=True)

    tasks = {"essig": lambda: pull_essig(root, log),
             "images": lambda: pull_images(root, a.images, a.workers, log, a.state, start=a.start, subdir=a.subdir),
             "bugpicker": lambda: pull_bugpicker(root, log)}
    with cf.ThreadPoolExecutor(max_workers=len(a.only)) as ex:   # all streams at once
        futs = {ex.submit(tasks[k]): k for k in a.only}
        for f in cf.as_completed(futs):
            try:
                f.result()
            except Exception as e:  # noqa: BLE001 - fallback; the failure is recorded or degrades
                log(futs[f], {"status": "error", "error": repr(e)})


if __name__ == "__main__":
    main()
