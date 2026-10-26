"""Each printed insect as a Merkle knowledge graph, verified bottom-up.

Levels (a node's hash covers its children's hashes, its bounding box and the
results of its logic checks, so any failed check or changed child moves every
hash above it, and the first mismatching level is the break point):

  L0 primitive   ellipsoid / rod / plate with its exact build spec
  L1 part        head_body, thorax_body, abdomen_body, leg_1L..leg_3R (femur+tibia),
                 antenna_L/R, wing_L/R
  L2 tagma       head (body + antennae), thorax (body + legs + wings), abdomen
  L3 insect      the printed body: the INSECT HASH (deterministic: rebuild from
                 (length, plan) and the same hash comes back, on any machine)
  L4 specimen    provenance: family, SD level, group, size source, STL sha256

Collection: insect -> family -> group -> collection root.

Checks get stricter as the bounding box grows:
  L0  fuse minimums (rod Ø>=0.8, plate >=0.8, wall >=0.6), watertight,
      mesh bbox inside the analytic spec bbox
  L1  children contained, extents monotone, union volume bounds,
      leg joints continuous (tibia starts at femur end)
  L2  contained, monotone, volume bounds, appendages attached to their body
      (leg / antenna base inside the body ellipsoid, wing overlaps the body),
      left/right mirror symmetry
  L3  contained, monotone, volume bounds, head < thorax < abdomen along the body
      axis, body span = length, union bbox = children bbox, watertight,
      appendage counts (0/6 legs, 0/2 antennae, 0/2 wings), kit tray = f(width)
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh

from .printmodels import CA_FAMILIES, PIN, PLATE, insect_parts, tray_for

TOL = 0.05      # mm, containment / bbox tolerance
VTOL = 0.02     # relative volume tolerance


def _r(x, nd):
    if isinstance(x, (list, tuple, np.ndarray)):
        return [_r(v, nd) for v in x]
    v = round(float(x), nd)
    return 0.0 if v == 0 else v      # no -0.0


def _h(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _union(meshes):
    return meshes[0] if len(meshes) == 1 else trimesh.boolean.union(meshes, engine="manifold")


def _bbox(m):
    return [_r(m.bounds[0], 2), _r(m.bounds[1], 2)]


def _contains(outer, inner, tol=TOL):
    return all(outer[0][i] - tol <= inner[0][i] and inner[1][i] <= outer[1][i] + tol for i in range(3))


def _ext(bb):
    return [round(bb[1][i] - bb[0][i], 2) for i in range(3)]


def _in_ellipsoid(pt, center, radii, slack=1.0):
    return float(sum(((pt[i] - center[i]) / radii[i]) ** 2 for i in range(3))) <= slack


def _overlap(a, b):
    return all(a[0][i] <= b[1][i] + TOL and b[0][i] <= a[1][i] + TOL for i in range(3))


def _node(level, kind, name, children, mesh, checks, spec=None, extra=None):
    checks = {k: bool(v) for k, v in checks.items()}
    bb = _bbox(mesh)
    vol = _r(mesh.volume, 1)
    body = {"level": level, "kind": kind, "name": name, "bbox": bb, "volume_mm3": vol,
            "children": [c["hash"] for c in children], "checks": checks}
    if spec is not None:
        body["spec"] = spec
    if extra:
        body.update(extra)
    topo = _h({"kind": kind, "name": name, "children": [c["topo"] for c in children]})
    return {**body, "hash": _h(body), "topo": topo, "ok": all(checks.values()) and all(c["ok"] for c in children),
            "_mesh": mesh}


def _group_checks(children, mesh):
    bb = _bbox(mesh)
    vols = [c["volume_mm3"] for c in children]
    return {
        "children_contained": all(_contains(bb, c["bbox"]) for c in children),
        "extents_monotone": all(all(_ext(bb)[i] + TOL >= _ext(c["bbox"])[i] for i in range(3)) for c in children),
        "union_volume_bounds": max(vols) * (1 - VTOL) - 0.1 <= round(float(mesh.volume), 1) <= sum(vols) * (1 + VTOL) + 0.1,
    }


def insect_tree(length_mm, plan):
    """Build the L0-L3 Merkle tree for one insect. Returns (nodes, root) where
    nodes is a flat list (parents after children) and root is the L3 node."""
    prims, _feats, d = insect_parts(length_mm, plan)
    L, W = d["L"], d["W"]
    nodes = []
    # L0
    leaves = []
    for pr in prims:
        m = _union(pr["meshes"])
        s = pr["spec"]
        if pr["kind"] == "ellipsoid":
            c, r = s["center"], s["radii"]
            spec_bb = [[c[i] - r[i] for i in range(3)], [c[i] + r[i] for i in range(3)]]
            fuse = 2 * min(r) >= 0.6
        elif pr["kind"] == "rod":
            a, b, dd = np.array(s["a"]), np.array(s["b"]), s["d"]
            spec_bb = [list(np.minimum(a, b) - dd / 2), list(np.maximum(a, b) + dd / 2)]
            fuse = dd >= PIN - 1e-9
        else:
            c, e = s["center"], s["extents"]
            spec_bb = [[c[i] - e[i] / 2 for i in range(3)], [c[i] + e[i] / 2 for i in range(3)]]
            fuse = min(e) >= PLATE - 1e-9
        checks = {"fuse_minimum": bool(fuse), "watertight": bool(m.is_watertight),
                  "bbox_within_spec": _contains(_r(spec_bb, 2), _bbox(m))}
        n = _node(0, pr["kind"], f"{pr['part']}.{pr['seg']}", [], m, checks,
                  spec={k: _r(v, 3) for k, v in s.items()}, extra={"part": pr["part"], "tagma": pr["tagma"]})
        leaves.append(n); nodes.append(n)
    # L1 parts
    parts = {}
    for n in leaves:
        parts.setdefault(n["part"], []).append(n)
    l1 = {}
    for name, ch in parts.items():
        m = _union([c["_mesh"] for c in ch])
        checks = _group_checks(ch, m)
        if name.startswith("leg_"):
            fem, tib = ch[0]["spec"], ch[1]["spec"]
            checks["joint_continuous"] = fem["b"] == tib["a"]
        n = _node(1, "part", name, ch, m, checks, extra={"tagma": ch[0]["tagma"]})
        l1[name] = n; nodes.append(n)
    # L2 tagmata
    l2 = {}
    for tg in ("head", "thorax", "abdomen"):
        ch = [n for n in l1.values() if n["tagma"] == tg]
        body = l1[f"{tg}_body"]
        bspec = parts[f"{tg}_body"][0]["spec"]
        m = _union([c["_mesh"] for c in ch])
        checks = _group_checks(ch, m)
        att = True
        for c in ch:
            if c["name"].startswith(("leg_", "antenna_")):
                base = parts[c["name"]][0]["spec"]["a"]
                att &= _in_ellipsoid(base, bspec["center"], bspec["radii"])
            if c["name"].startswith("wing_"):
                att &= _overlap(c["bbox"], body["bbox"]) or _overlap(c["bbox"], l1["abdomen_body"]["bbox"])
        checks["appendages_attached"] = bool(att)
        mirror = True
        for c in ch:
            if c["name"].endswith("L"):
                twin = l1.get(c["name"][:-1] + "R")
                mirror &= twin is not None and abs(c["bbox"][0][1] + twin["bbox"][1][1]) <= TOL \
                    and abs(c["bbox"][1][1] + twin["bbox"][0][1]) <= TOL
        checks["left_right_mirror"] = bool(mirror)
        n = _node(2, "tagma", tg, ch, m, checks)
        l2[tg] = n; nodes.append(n)
    # L3 insect
    ch = [l2["head"], l2["thorax"], l2["abdomen"]]
    m = _union([c["_mesh"] for c in ch])
    checks = _group_checks(ch, m)
    cx = [parts[f"{t}_body"][0]["spec"]["center"][0] for t in ("head", "thorax", "abdomen")]
    span = l1["abdomen_body"]["bbox"][1][0] - l1["head_body"]["bbox"][0][0]
    child_bb = [[min(c["bbox"][0][i] for c in ch) for i in range(3)], [max(c["bbox"][1][i] for c in ch) for i in range(3)]]
    n_leg = sum(k.startswith("leg_") for k in l1)
    n_ant = sum(k.startswith("antenna_") for k in l1)
    n_wing = sum(k.startswith("wing_") for k in l1)
    tray = tray_for(W)
    checks.update({
        "tagma_order": cx[0] < cx[1] < cx[2],
        "body_span_matches_length": 0.97 * L <= span <= 1.06 * L,
        "union_bbox_equals_children": all(abs(_bbox(m)[j][i] - child_bb[j][i]) <= TOL for i in range(3) for j in range(2)),
        "watertight": bool(m.is_watertight),
        "appendage_counts": n_leg in (0, 6) and n_ant in (0, 2) and n_wing in (0, 2),
        "tray_from_width": tray != "out of range",
    })
    root = _node(3, "insect", plan, ch, m, checks, extra={
        "plan": plan, "length_mm": _r(L, 2), "body_width_mm": _r(W, 2), "kit_tray": tray,
        "counts": {"legs": n_leg, "antennae": n_ant, "wings": n_wing}})
    nodes.append(root)
    return nodes, root


def observe(root):
    """What the camera / digital twin sees of a printed insect: envelope (0.1 mm,
    ~10 px/mm), top-down silhouette area, appendage counts. No length, no hash."""
    m = root["_mesh"]
    ext = _ext(root["bbox"])
    return {"envelope_mm": [round(e, 1) for e in ext], "top_area_mm2": round(silhouette_area(m), 0), **root["counts"]}


def silhouette_area(mesh):
    """Top-down silhouette area (mm^2): union of the up-facing triangles
    projected onto XY (shapely / GEOS). This is what a camera above the tray sees."""
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    tri = mesh.vertices[mesh.faces[mesh.face_normals[:, 2] > 1e-9]][:, :, :2]
    polys = [Polygon(t) for t in tri]
    polys = [p for p in polys if p.area > 1e-12]
    return float(unary_union(polys).area)


def strip(n):
    return {k: v for k, v in n.items() if not k.startswith("_")}


def verify_tree(nodes):
    """Recompute every hash from the stored node bodies (no geometry): proves the
    record was not edited. Returns (ok, first_bad_node_name)."""
    by = {n["hash"]: n for n in nodes}
    for n in nodes:
        body = {k: n[k] for k in ("level", "kind", "name", "bbox", "volume_mm3", "children", "checks")}
        for k in ("spec", "part", "tagma", "plan", "length_mm", "body_width_mm", "kit_tray", "counts"):
            if k in n:
                body[k] = n[k]
        if _h(body) != n["hash"] or any(c not in by for c in n["children"]):
            return False, n["name"]
    return True, None


def rebuild_hash(length_mm, plan):
    """Deterministic check: the insect hash for (length, plan)."""
    return insect_tree(length_mm, plan)[1]["hash"]


def break_point(nodes_a, nodes_b):
    """Compare two trees top-down; return the deepest-level node names that differ
    (L3 -> L2 -> L1 -> L0), i.e. where the insects diverge."""
    A = {(n["level"], n["name"]): n["hash"] for n in nodes_a}
    B = {(n["level"], n["name"]): n["hash"] for n in nodes_b}
    diff = sorted({k for k in A.keys() | B.keys() if A.get(k) != B.get(k)})
    if not diff:
        return None
    lo = min(k[0] for k in diff)
    return {"level": lo, "nodes": [k[1] for k in diff if k[0] == lo]}


# ---------------------------------------------------------------- collection

def _family_stats():
    st = {fam: {"order": o, "n": n, "mean": mu, "sd": sd, "plan": plan} for o, fam, n, mu, sd, plan in CA_FAMILIES}
    return st


def build_collection(manifest_csv, out_dir, ledger=None):
    """Per-insect trees + family/group/collection roots. Writes
    out_dir/insects/<stem>.json, index.json, collection.json, nodes.csv."""
    out = Path(out_dir); (out / "insects").mkdir(parents=True, exist_ok=True)
    with open(manifest_csv) as fh:
        rows = list(csv.DictReader(fh))
    base = Path(manifest_csv).parent
    index, level_ok = [], {0: [0, 0], 1: [0, 0], 2: [0, 0], 3: [0, 0]}
    for r in rows:
        nodes, root = insect_tree(float(r["length_mm"]), r["plan"])
        for n in nodes:
            level_ok[n["level"]][0] += 1
            level_ok[n["level"]][1] += all(n["checks"].values())
        stl = base / r["file"]
        spec = {"representation": r.get("representation", "toy"), "size_flag": r.get("size_flag", ""),
                "training_role": r.get("training_role", ""),
                "group": r["group"], "order": r["order"], "family": r["family"], "level": r["level"],
                "size_source": r["size_source"], "note": r["note"], "file": r["file"],
                "stl_sha256": hashlib.sha256(stl.read_bytes()).hexdigest() if stl.exists() else None}
        l4 = {"level": 4, "kind": "specimen", "name": Path(r["file"]).stem, "insect_hash": root["hash"], **spec}
        l4["hash"] = _h(l4)
        stem = Path(r["file"]).stem
        (out / "insects" / f"{stem}.json").write_text(json.dumps(
            {"insect_hash": root["hash"], "specimen_hash": l4["hash"], "nodes": [strip(n) for n in nodes], "specimen": l4},
            indent=1))
        fam = r["family"].split(" (")[0]
        index.append({"name": stem, **spec, "family_base": fam, "plan": r["plan"],
                      "length_mm": root["length_mm"], "body_width_mm": root["body_width_mm"],
                      "kit_tray": root["kit_tray"], "insect_hash": root["hash"], "topo_hash": root["topo"],
                      "specimen_hash": l4["hash"], "all_checks_ok": root["ok"],
                      "failed_checks": sorted({f"L{n['level']}:{n['name']}:{k}" for n in nodes for k, v in n["checks"].items() if not v}),
                      "n_nodes": len(nodes), "observation": observe(root)})
    # family -> group -> collection
    fams = {}
    for x in index:
        fams.setdefault((x["group"], x["family_base"]), []).append(x)
    stats = _family_stats()
    fam_nodes = []
    for (g, f), xs in sorted(fams.items()):
        body = {"level": 5, "kind": "family", "name": f, "group": g,
                "children": sorted(x["specimen_hash"] for x in xs),
                "stats": stats.get(f) if g == "california" else None,
                "length_range_mm": [min(x["length_mm"] for x in xs), max(x["length_mm"] for x in xs)]}
        body["hash"] = _h(body); fam_nodes.append(body)
    groups = []
    for g in sorted({fn["group"] for fn in fam_nodes}):
        body = {"level": 6, "kind": "group", "name": g, "children": sorted(fn["hash"] for fn in fam_nodes if fn["group"] == g)}
        body["hash"] = _h(body); groups.append(body)
    coll = {"level": 7, "kind": "collection", "name": "baebugs_fuse1_TOY_print_kg", "representation": "toy", "children": sorted(g["hash"] for g in groups)}
    coll["hash"] = _h(coll)
    (out / "index.json").write_text(json.dumps(index, indent=1))
    (out / "collection.json").write_text(json.dumps({"root": coll, "groups": groups, "families": fam_nodes,
                                                     "level_checks": {f"L{k}": {"nodes": v[0], "passed": v[1]} for k, v in level_ok.items()}},
                                                    indent=1))
    with (out / "nodes.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["insect", "level", "kind", "name", "hash", "ok", "bbox_x", "bbox_y", "bbox_z", "volume_mm3", "failed"])
        for x in index:
            for n in json.loads((out / "insects" / f"{x['name']}.json").read_text())["nodes"]:
                e = _ext(n["bbox"])
                w.writerow([x["name"], n["level"], n["kind"], n["name"], n["hash"][:16], all(n["checks"].values()),
                            *e, n["volume_mm3"], ";".join(k for k, v in n["checks"].items() if not v)])
    if ledger is not None:
        for lv, (tot, ok) in level_ok.items():
            ledger.append(f"verify_L{lv}", {"nodes": tot, "passed": ok})
        ledger.append("collection_root", {"root": coll["hash"], "insects": len(index), "families": len(fam_nodes),
                                          "groups": {g["name"]: len(g["children"]) for g in groups}},
                      files={"index": out / "index.json", "collection": out / "collection.json"})
    return index, coll


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser("baebugs-insect-kg")
    ap.add_argument("--manifest", default="print/fuse1/manifest.csv")
    ap.add_argument("--out", default="print/fuse1/kg")
    ap.add_argument("--ledger", action="store_true", help="commit+push a break point per verified level")
    ap.add_argument("--repo", default=".")
    a = ap.parse_args(argv)
    led = None
    if a.ledger:
        from .git_ledger import GitLedger
        led = GitLedger("print_kg", a.repo)
    idx, coll = build_collection(a.manifest, a.out, led)
    bad = [x for x in idx if not x["all_checks_ok"]]
    print(f"{len(idx)} insects, collection root {coll['hash'][:16]}, {len(bad)} with failed checks")
    for x in bad[:20]:
        print(" ", x["name"], x["failed_checks"][:6])


if __name__ == "__main__":
    main()
