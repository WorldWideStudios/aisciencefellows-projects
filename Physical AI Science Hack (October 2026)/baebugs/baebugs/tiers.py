"""Tiers of abstraction in one image, every tier a Merkle node with a bounding box.

From the bottom:
  T0 pixels      each 16-pixel row segment of a tile is a leaf: H(x, y, w, raw bytes)
  T1 tile        16 x 16 pixels; hash = Merkle root of its row leaves
  T2..Tk group   2 x 2 groups of the tier below (32, 64, 128 ... px), up to one node for the whole image
  object         a specimen / part: bbox, label, the tiles it covers, and (if an outline is given) the
                 object's own geometry tree from baebugs.image_levels (aabb -> obb -> hull -> polygon -> contour)
  frame          the image: H(pixel root, objects root, meta: step, module, filter, protocol)

A step snapshot is one frame; steps chain in an MMR (baebugs.ladder), modules and runs roll up above that.

Because every tier is hashed, two snapshots are compared top-down: equal nodes are skipped, so the
first unequal nodes are the BREAK POINTS, and their bounding boxes say where the image changed, at
whatever tier the question needs (where did the specimen move? which tiles? which exact pixel?).
Any single pixel can be proven against the frame root with its row bytes and a sibling path.
"""
from __future__ import annotations

import hashlib
import json

import numpy as np

TILE = 16


def _h(*parts) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(p if isinstance(p, bytes) else json.dumps(p, sort_keys=True, separators=(",", ":")).encode())
        h.update(b"\0")
    return h.hexdigest()


def _merkle(leaves):
    lv = list(leaves) or [_h("empty")]
    while len(lv) > 1:
        if len(lv) % 2:
            lv.append(lv[-1])
        lv = [_h(a, b) for a, b in zip(lv[::2], lv[1::2])]
    return lv[0]


def _row_leaves(img, x0, y0):
    t = img[y0:y0 + TILE, x0:x0 + TILE]
    w = t.shape[1]
    return [_h("px", x0, y0 + r, w, np.ascontiguousarray(t[r]).tobytes()) for r in range(t.shape[0])]


def pyramid(img):
    """Pixel tiers T1..Tk as {tier: {(i, j): {"bbox": [x0,y0,x1,y1], "hash": h}}}; tier 1 = 16 px tiles."""
    H, W = img.shape[:2]
    ny, nx = -(-H // TILE), -(-W // TILE)
    tiers = {1: {}}
    for i in range(ny):
        for j in range(nx):
            x0, y0 = j * TILE, i * TILE
            tiers[1][(i, j)] = {"bbox": [x0, y0, min(W, x0 + TILE), min(H, y0 + TILE)],
                                "hash": _h("tile", x0, y0, _merkle(_row_leaves(img, x0, y0)))}
    k = 1
    while len(tiers[k]) > 1:
        cur, nxt = tiers[k], {}
        my, mx = max(i for i, _ in cur) + 1, max(j for _, j in cur) + 1
        for i in range(-(-my // 2)):
            for j in range(-(-mx // 2)):
                kids = [cur.get((2 * i + a, 2 * j + b)) for a in (0, 1) for b in (0, 1)]
                real = [c for c in kids if c]
                bb = [min(c["bbox"][0] for c in real), min(c["bbox"][1] for c in real),
                      max(c["bbox"][2] for c in real), max(c["bbox"][3] for c in real)]
                nxt[(i, j)] = {"bbox": bb, "hash": _h("group", k + 1, bb, [c["hash"] if c else "" for c in kids])}
        tiers[k + 1] = nxt
        k += 1
    return tiers


def _tiles_in(bbox, tiles):
    x0, y0, x1, y1 = bbox
    return sorted(t["hash"] for t in tiles.values()
                  if t["bbox"][0] < x1 and t["bbox"][2] > x0 and t["bbox"][1] < y1 and t["bbox"][3] > y0)


def object_node(obj, tiles, ppm=None):
    """obj: {"id", "bbox": [x0,y0,x1,y1] px, optional "label", "score", "contour" (Nx2 px)}."""
    geom = None
    if obj.get("contour") is not None and ppm:
        from .image_levels import tree
        geom = tree(np.asarray(obj["contour"], dtype=np.int32).reshape(-1, 1, 2), ppm, obj.get("model", "given"))["root"]
    bb = [int(v) for v in obj["bbox"]]
    tiles_root = _merkle(_tiles_in(bb, tiles))
    node = {"id": obj["id"], "bbox": bb, "label": obj.get("label"), "score": obj.get("score"),
            "tiles_root": tiles_root, "geometry_root": geom}
    node["hash"] = _h("object", {k: v for k, v in node.items()})
    return node


def frame(img, objects=(), meta=None, ppm=None):
    """Build every tier for one image. Returns the frame (root + all tiers + objects)."""
    tiers = pyramid(img)
    top = max(tiers)
    objs = [object_node(o, tiers[1], ppm) for o in objects]
    meta = dict(meta or {})
    pix_root = next(iter(tiers[top].values()))["hash"]
    obj_root = _merkle(sorted(o["hash"] for o in objs)) if objs else _h("no objects")
    img_sha = hashlib.sha256(np.ascontiguousarray(img).tobytes()).hexdigest()
    root = _h("frame", pix_root, obj_root, meta, list(img.shape))
    return {"root": root, "pixel_root": pix_root, "objects_root": obj_root, "image_raw_sha256": img_sha,
            "shape": list(img.shape), "meta": meta, "tiers": tiers, "objects": objs, "tile": TILE}


def summary(fr):
    """JSON-safe record of a frame (what goes in the MMR): roots, tier sizes, objects."""
    return {"root": fr["root"], "pixel_root": fr["pixel_root"], "objects_root": fr["objects_root"],
            "image_raw_sha256": fr["image_raw_sha256"], "shape": fr["shape"], "meta": fr["meta"],
            "tiers": {f"T{k}": len(v) for k, v in fr["tiers"].items()},
            "objects": [{k: o[k] for k in ("id", "bbox", "label", "score", "hash")} for o in fr["objects"]]}


def diff(a, b, tier=1):
    """Top-down comparison of two frames of the same size. Descends only into unequal nodes.
    Returns break points at `tier` merged into boxes, the number of nodes compared, and object changes."""
    if a["shape"] != b["shape"]:
        return {"comparable": False, "reason": "different image size"}
    top = max(a["tiers"])
    compared, frontier = 0, [(top, key) for key in a["tiers"][top]]
    broken = []
    while frontier:
        k, (i, j) = frontier.pop()
        compared += 1
        if a["tiers"][k][(i, j)]["hash"] == b["tiers"][k][(i, j)]["hash"]:
            continue
        if k == tier:
            broken.append((i, j)); continue
        for da in (0, 1):
            for db in (0, 1):
                kid = (2 * i + da, 2 * j + db)
                if kid in a["tiers"][k - 1]:
                    frontier.append((k - 1, kid))
    boxes = _merge(broken, a["tiers"][tier])
    ao = {o["id"]: o for o in a["objects"]}; bo = {o["id"]: o for o in b["objects"]}
    objs = {"added": sorted(set(bo) - set(ao)), "removed": sorted(set(ao) - set(bo)),
            "changed": sorted(i for i in set(ao) & set(bo) if ao[i]["hash"] != bo[i]["hash"])}
    total = sum(len(v) for v in a["tiers"].values())
    return {"comparable": True, "identical": a["root"] == b["root"], "tier": f"T{tier}", "broken_nodes": len(broken),
            "break_boxes": boxes, "nodes_compared": compared, "nodes_total": total, "objects": objs}


def _merge(cells, tiles):
    """Connected changed cells -> bounding boxes (4-connectivity)."""
    left, out = set(cells), []
    while left:
        stack = [left.pop()]; comp = []
        while stack:
            c = stack.pop(); comp.append(c)
            for n in ((c[0] + 1, c[1]), (c[0] - 1, c[1]), (c[0], c[1] + 1), (c[0], c[1] - 1)):
                if n in left:
                    left.remove(n); stack.append(n)
        bbs = [tiles[c]["bbox"] for c in comp]
        out.append([min(b[0] for b in bbs), min(b[1] for b in bbs), max(b[2] for b in bbs), max(b[3] for b in bbs)])
    return sorted(out)


def prove_pixel(img, fr, x, y):
    """Proof that pixel (x, y) is part of this frame: its row bytes, the tile's row leaves, and the tile path."""
    i, j = y // TILE, x // TILE
    x0, y0 = j * TILE, i * TILE
    rows = _row_leaves(img, x0, y0)
    path, k, (ci, cj) = [], 1, (i, j)
    while k < max(fr["tiers"]):
        pi, pj = ci // 2, cj // 2
        sibs = [fr["tiers"][k].get((2 * pi + a, 2 * pj + b)) for a in (0, 1) for b in (0, 1)]
        path.append({"tier": k + 1, "bbox": fr["tiers"][k + 1][(pi, pj)]["bbox"], "slot": (ci - 2 * pi) * 2 + (cj - 2 * pj),
                     "children": [s["hash"] if s else "" for s in sibs]})
        k, ci, cj = k + 1, pi, pj
    seg = img[y, x0:x0 + TILE]
    return {"x": x, "y": y, "pixel": np.asarray(img[y, x]).tolist(), "tile": [x0, y0], "row": y - y0, "w": int(seg.shape[0]),
            "row_bytes": np.ascontiguousarray(img[y, x0:x0 + TILE]).tobytes().hex(),
            "row_leaves": rows, "path": path, "pixel_root": fr["pixel_root"]}


def verify_pixel(proof):
    """Recompute from the row bytes up to the pixel root; also checks the pixel value is inside the row bytes."""
    x0, y0 = proof["tile"]; r = proof["row"]
    raw = bytes.fromhex(proof["row_bytes"])
    leaves = list(proof["row_leaves"])
    if leaves[r] != _h("px", x0, y0 + r, proof["w"], raw):
        return False
    ch = len(raw) // proof["w"]
    if list(raw[(proof["x"] - x0) * ch:(proof["x"] - x0 + 1) * ch]) != (proof["pixel"] if isinstance(proof["pixel"], list) else [proof["pixel"]]):
        return False
    h = _h("tile", x0, y0, _merkle(leaves))
    for step in proof["path"]:
        if step["children"][step["slot"]] != h:
            return False
        h = _h("group", step["tier"], step["bbox"], step["children"])
    return h == proof["pixel_root"]


def draw(img, fr, d=None, tiers=(1, 3, 5)):
    """Snapshot image: tier grids (thin), objects (labelled), break boxes (thick red) if a diff is given."""
    import cv2
    out = img.copy() if img.ndim == 3 else cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    colors = {1: (210, 210, 210), 3: (150, 190, 255), 5: (90, 140, 255)}
    for k in tiers:
        for n in fr["tiers"].get(k, {}).values():
            x0, y0, x1, y1 = n["bbox"]
            cv2.rectangle(out, (x0, y0), (x1 - 1, y1 - 1), colors.get(k, (180, 180, 180)), 1)
    for o in fr["objects"]:
        x0, y0, x1, y1 = o["bbox"]
        cv2.rectangle(out, (x0, y0), (x1, y1), (40, 160, 60), 2)
        cv2.putText(out, f"{o['id']} {o.get('label') or ''} {o['hash'][:6]}", (x0, max(12, y0 - 4)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (40, 160, 60), 1, cv2.LINE_AA)
    for bb in (d or {}).get("break_boxes", []):
        cv2.rectangle(out, (bb[0], bb[1]), (bb[2], bb[3]), (0, 0, 230), 3)
    cv2.putText(out, f"frame {fr['root'][:12]}", (8, out.shape[0] - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2, cv2.LINE_AA)
    cv2.putText(out, f"frame {fr['root'][:12]}", (8, out.shape[0] - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
    return out
