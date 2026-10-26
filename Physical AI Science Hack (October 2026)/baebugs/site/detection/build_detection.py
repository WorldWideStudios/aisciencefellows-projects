"""Compile public, source-verified, recorded object detections for the Baebugs viewer.

No model is inferred or executed here. Inputs are the existing recorded
PA12 toy photographs and docs/toy_photo_models/results.json; fail closed on
source digest drift, out-of-frame coordinates and inconsistent records.
Output is a DERIVED web projection, not an MMR commitment or scientific proof.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parents[2]
SRC_RESULT = "docs/toy_photo_models/results.json"
SRC_EXECUTOR = "baebugs/toy_photo_models.py"
PROVENANCE_CONTEXT = "BAEBUGS_PA12_TOY_DETECTION_VISUALIZATION_20261025"


def canonical_bytes(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def sha_file(path):
    return sha(Path(path).read_bytes())


def compile_detection(repo=REPO, mvp_path=None):
    repo = Path(repo).resolve()
    mvp_path = Path(mvp_path) if mvp_path else repo / "site/mvp/mvp.json"
    pack = json.loads(mvp_path.read_text())
    leaves = {item["path"]: item for item in pack["leaves"]}
    if len(leaves) != len(pack["leaves"]):
        raise ValueError("Duplicate canonical source paths in MVP graph")

    def source(path):
        atom = leaves.get(path)
        if atom is None:
            raise ValueError("Unaddressed detection source: " + path)
        actual = sha_file(repo / path)
        if actual != atom["sha256"]:
            raise ValueError("Detection source hash drift: " + path)
        return {key: atom[key] for key in ("path", "sha256", "leaf", "licence", "claim", "status")}

    results_atom = source(SRC_RESULT)
    executor_atom = source(SRC_EXECUTOR)
    results = json.loads((repo / SRC_RESULT).read_text())
    photos = results.get("photos")
    if not isinstance(photos, list) or len(photos) != 2:
        raise ValueError("Unexpected number of recorded toy photographs")

    entries = []
    for photo in photos:
        filename = photo["photo"]
        if filename not in ("pa12_toys_two_on_floor.jpg", "pa12_toys_box.jpg"):
            raise ValueError("Unexpected source photo identity")
        path = "assets/photos/" + filename
        photo_atom = source(path)
        if photo["sha256"] != photo_atom["sha256"]:
            raise ValueError("Photo hash and model-run receipt do not agree")

        with Image.open(repo / path) as image:
            width, height = image.size
        if width <= 0 or height <= 0:
            raise ValueError("Invalid photo dimensions")
        proposals = []
        for model_name in ("yoloe", "owlv2"):
            rows = photo[model_name]
            if not isinstance(rows, list):
                raise ValueError("Expected array of predictions")
            for i, item in enumerate(rows):
                box = item["bbox"]
                if (not isinstance(box, list) or len(box) != 4
                    or any(type(n) is not int for n in box)):
                    raise ValueError("Bounding box is not four integers")
                x0, y0, x1, y1 = box
                if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
                    raise ValueError("Bounding box extends outside photograph")
                conf = item["conf"]
                if type(conf) not in (float, int) or not (0 <= conf <= 1):
                    raise ValueError("Unusable detection confidence")
                order = item.get("order")
                if order is not None:
                    if not isinstance(order.get("label"), str) or not (0 <= order["conf"] <= 1):
                        raise ValueError("Bad inherited ORDER inference")
                content = {
                    "schema": "baebugs.RecordedDetectionAtom.v1",
                    "source_image_sha256": photo_atom["sha256"],
                    "source_result_sha256": results_atom["sha256"],
                    "model": model_name,
                    "model_identity": results["models"][model_name],
                    "record_index": i,
                    "label": item["label"],
                    "confidence": conf,
                    "bbox_xyxy_pixels": box,
                    "order_inference": order,
                    "image_width": width,
                    "image_height": height,
                    "scientific_identity": "NOT_VERIFIED",
                    "physical_recovery": "NOT_TESTED",
                }
                occurrence = {
                    "context": PROVENANCE_CONTEXT,
                    "root": pack["root"],
                    "photo_file_leaf": photo_atom["leaf"],
                    "results_file_leaf": results_atom["leaf"],
                    "detection_content_sha256": sha(canonical_bytes(content)),
                }
                proposals.append({
                    **content,
                    "content_sha256": sha(canonical_bytes(content)),
                    "context_sha256": sha(canonical_bytes(occurrence)),
                    "status": "RECORDED_INFERENCE_NOT_GROUND_TRUTH"
                })
        entries.append({
            "photo": filename,
            "width": width,
            "height": height,
            "image_path": "images/" + filename.replace(".jpg", ".webp"),
            "source_photo": photo_atom,
            "frame_root_source_reported": photo["frame_root"],
            "frame_root_recomputed": "NOT_COMPUTED",
            "model_predictions": proposals,
            "vlm_reported": photo["vlm"],
        })
    return {
        "schema": "baebugs.RecordedBoundingBoxGallery.v1",
        "source_evidence_root": pack["root"],
        "source_commit": "PIN_AT_DEPLOYMENT",
        "results_atom": results_atom,
        "executor_atom": executor_atom,
        "images": entries,
        "model_license_context": {
            "yoloe": "Ultralytics AGPL-3.0/commercial terms — check model and weight reuse",
            "owlv2": "Google OWLv2 — separately review upstream model/weight license",
            "order": "ORDER_best.pt SHA is an identity claim, not independent validation",
        },
        "publication_scope": "REPOSITORY_PUBLIC_SOURCE_PHOTOS_WITHOUT_PERSONS",
        "derivation_status": "EXACT_SOURCE_BYTES_VERIFIED",
        "inference_execution_this_build": "NOT_EXECUTED",
        "human_labels": "NOT_VERIFIED",
        "live_webcam": "NOT_CONNECTED",
        "physical_specimen_recovery": "NOT_TESTED",
        "signature": "NOT_SIGNED",
        "mmr_commit": "NOT_COMPUTED",
    }


def build_gallery(repo, target, source_commit, mvp_path):
    repo = Path(repo).resolve()
    target = Path(target)
    target.mkdir(parents=True, exist_ok=True)
    gallery = compile_detection(repo, mvp_path)
    if len(source_commit) != 40 or any(c not in "0123456789abcdef" for c in source_commit):
        raise ValueError("Full 40-character commit required")
    gallery["source_commit"] = source_commit

    image_dir = target / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    for entry in gallery["images"]:
        source = repo / entry["source_photo"]["path"]
        output = target / entry["image_path"]
        with Image.open(source) as image:
            # Deterministic, metadata-free derivative, preserving full geometry.
            im = image.convert("RGB")
            im.save(output, format="WEBP", quality=82, method=6, exif=b"")
        with Image.open(output) as check:
            if check.size != (entry["width"], entry["height"]):
                raise ValueError("Photo geometry drift during re-encoding")
            if check.getexif():
                raise ValueError("Derived public image contains EXIF")
        entry["web_image_sha256"] = sha_file(output)
        entry["public_photo_derivation"] = "Pillow RGB/WebP quality82 method6 EXIF stripped"
    catalog = target / "detections.json"
    catalog.write_text(json.dumps(gallery, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    return gallery


if __name__ == "__main__":
    print("Import build_gallery from the source-pinned static deployment builder")
