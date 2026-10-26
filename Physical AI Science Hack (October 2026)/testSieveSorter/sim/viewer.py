"""Replay page for one recorded sorter run: a single standalone three.js HTML file.

Run from sim\\:  python viewer.py <run_dir> [--open] [--rig bugsorter]
Reads run_dir/scene.json and run_dir/traj.npz (sim_contract.md, "Recording") and writes
run_dir/view.html. three.js, the scene and the trajectory are inlined, so the page opens from
file:// with no server and no network. --open opens it in the default browser. --rig draws the
bench tower (frame, rods and knobs, spray plate, tub) round a holder-box run: display only, from
rig.py, with sizes estimated from a photo.

Tray motion: tray_d (frames x 3) is the lab offset of the tray frame. A rocking run also records
tray_q (frames x 4, w x y z), the tray frame's orientation in the lab, about the point
scene["tray"]["pivot"] (mm in the tray frame, default the origin): a tray-frame point x is drawn at
tray_d + pivot + R(tray_q) (x - pivot). Particles are recorded in the tray frame, so they rock with it.
A seesaw run (docs/SYSTEM.md section 3: each level rocks about its own pivot, neighbours alternating) runs
in the lab frame and records level_q (frames x levels x 4, w x y z), each level's orientation in the lab,
with scene["levels"][k] = {"pivot": [x, y, z] mm, "geoms": [indices into scene["tray"]["geoms"]]}. Those
geoms are drawn turned by level_q about their level's pivot; the others, and the particles, as recorded.

The trajectory is quantized (positions int16 at 0.01 mm, so +/-327 mm; quaternions int16 at
1/32767; wetness uint8), delta-coded along time, byte-shuffled, zlib-compressed and base64'd.
The page undoes this with the browser's built-in DecompressionStream. If the page would still
be over MAX_HTML_MB, frames are decimated and a note is printed.

three.js is vendored in sim/vendor/, pinned to three@0.186.1. The npm package ships no .min.js
any more, so the two minified files are jsDelivr's build of the npm files:
  vendor/three.module.min.js  https://cdn.jsdelivr.net/npm/three@0.186.1/build/three.module.min.js
  vendor/three.core.min.js    https://cdn.jsdelivr.net/npm/three@0.186.1/build/three.core.min.js
  vendor/OrbitControls.js     three@0.186.1 npm package, examples/jsm/controls/OrbitControls.js
They are inlined as data: URLs in an import map, so the page's module code imports 'three'.
"""
import argparse
import base64
import html
import json
import math
import os
import re
import zlib
from pathlib import Path

import numpy as np

THREE_VERSION = "0.186.1"
HERE = Path(__file__).resolve().parent
TEMPLATE = HERE / "viewer_template.html"
VENDOR = HERE / "vendor"
MAX_HTML_MB = 25.0
POS_PER_MM = 100.0      # int16 position units per mm (0.01 mm)
QUAT_SCALE = 32767.0
INT16_MAX = 32767


def data_url(js: str) -> str:
    js = re.sub(r"^//# sourceMappingURL=.*$", "", js, flags=re.M)
    return "data:text/javascript;base64," + base64.b64encode(js.encode("utf-8")).decode("ascii")


def import_map() -> str:
    """three, three-core and OrbitControls as data: URLs; three's relative import of the core is
    rewritten to the bare name because relative specifiers can't resolve against a data: URL."""
    core = (VENDOR / "three.core.min.js").read_text(encoding="utf-8")
    module, n = re.subn(r"""from\s*(["'])\./three\.core(\.min)?\.js\1""", 'from"three-core"',
                        (VENDOR / "three.module.min.js").read_text(encoding="utf-8"))
    if n == 0:
        raise SystemExit("viewer: vendor/three.module.min.js no longer imports ./three.core.js; re-vendor")
    orbit = (VENDOR / "OrbitControls.js").read_text(encoding="utf-8")
    return json.dumps({"imports": {"three-core": data_url(core), "three": data_url(module),
                                   "three/addons/OrbitControls.js": data_url(orbit)}})


def pack(arr: np.ndarray, delta: bool) -> str:
    """Frames-first array -> base64(zlib(byte-shuffled data)). Integer arrays are delta-coded
    along frames first (wrapping in their dtype); the page undoes it with a running sum."""
    a = np.ascontiguousarray(arr)
    if delta and len(a) > 1:
        a = np.concatenate([a[:1], np.diff(a, axis=0)])
    shuffled = a.view(np.uint8).reshape(-1, a.dtype.itemsize).T     # like bytes compress better together
    return base64.b64encode(zlib.compress(shuffled.tobytes(), 6)).decode("ascii")


def quantize(traj: dict, step: int) -> tuple[dict, int]:
    """name -> little-endian array at every step-th frame; also the number of clamped positions."""
    fr = slice(None, None, step)
    pos = np.nan_to_num(traj["pos"][fr].astype(np.float64)) * POS_PER_MM
    clamped = int(np.count_nonzero(np.abs(pos) > INT16_MAX))
    out = {
        "t": traj["t"][fr].astype("<f4"),
        "tray_d": np.nan_to_num(traj["tray_d"][fr]).astype("<f4"),
        "pos": np.clip(np.rint(pos), -INT16_MAX, INT16_MAX).astype("<i2"),
        "quat": np.clip(np.rint(np.nan_to_num(traj["quat"][fr]) * QUAT_SCALE), -INT16_MAX, INT16_MAX).astype("<i2"),
    }
    if "tray_q" in traj:           # rocking: the tray frame's orientation, w x y z, about scene tray.pivot
        out["tray_q"] = np.nan_to_num(traj["tray_q"][fr]).astype("<f4")
    if "level_q" in traj:          # seesaw: each level's orientation, frames x levels x 4, about scene levels[k].pivot
        out["level_q"] = np.nan_to_num(traj["level_q"][fr]).astype("<f4")
    if "zone_counts" in traj:
        out["zone_counts"] = np.clip(traj["zone_counts"][fr], 0, 65535).astype("<u2")
    if "wet" in traj:
        out["wet"] = np.rint(np.clip(np.nan_to_num(traj["wet"][fr]), 0, 1) * 255).astype("u1")
    return out, clamped


def encode(traj: dict, step: int) -> tuple[dict, dict, int]:
    arrays, clamped = quantize(traj, step)
    dtypes = {"<f4": "float32", "<i2": "int16", "<u2": "uint16", "|u1": "uint8"}
    meta, blobs = {}, {}
    for name, a in arrays.items():
        delta = a.dtype.kind in "iu"
        meta[name] = {"dtype": dtypes[a.dtype.str], "shape": list(a.shape), "delta": delta}
        blobs[name] = pack(a, delta)
    return meta, blobs, clamped


def json_safe(x):
    """NaN/inf -> null, since JSON.parse rejects them."""
    if isinstance(x, float):
        return x if math.isfinite(x) else None
    if isinstance(x, dict):
        return {k: json_safe(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [json_safe(v) for v in x]
    return x


def script_json(obj) -> str:
    return json.dumps(json_safe(obj), separators=(",", ":")).replace("</", "<\\/")


def build(run_dir: Path, rig: str | None = None) -> Path:
    scene = json.loads((run_dir / "scene.json").read_text(encoding="utf-8"))
    if rig:                        # display-only surroundings, in the lab frame (rig.py)
        import rig as rig_module
        scene["rig"] = {"name": rig, "geoms": getattr(rig_module, rig)(scene)}
    with np.load(run_dir / "traj.npz") as z:
        traj = {k: z[k] for k in z.files}
    for g in scene.get("tray", {}).get("geoms", []):
        if g.get("type") == "mesh" and "faces" not in g:
            print(f"viewer: warning: tray mesh ({g.get('role')}) has no faces; it is not drawn")

    template = TEMPLATE.read_text(encoding="utf-8")
    fixed = {"TITLE": html.escape(f"Sorter replay: {scene.get('design', run_dir.name)}"),
             "IMPORTMAP": import_map(), "SCENE": script_json(scene)}
    budget = MAX_HTML_MB * 1e6 - len(template) - sum(len(v) for v in fixed.values())
    n_frames = len(traj["t"])
    step = 1
    while True:
        meta, blobs, clamped = encode(traj, step)
        size = sum(len(b) for b in blobs.values())
        if size <= budget or math.ceil(n_frames / step) <= 2:
            break
        step = max(step + 1, math.ceil(step * size / budget))
    if step > 1:
        print(f"viewer: note: kept every {step}th frame ({n_frames} -> {math.ceil(n_frames / step)}) "
              f"to stay under {MAX_HTML_MB:.0f} MB")
    if clamped:
        print(f"viewer: note: {clamped} position values beyond +/-327 mm were clamped (lost bodies?)")

    fps = scene.get("fps")
    meta = {"arrays": meta, "pos_scale": 1 / POS_PER_MM, "quat_scale": 1 / QUAT_SCALE,
            "step": step, "fps": fps / step if fps else None, "three": THREE_VERSION}
    data = "\n".join(f'<script type="application/octet-stream" id="d-{k}">{v}</script>' for k, v in blobs.items())
    fills = dict(fixed, META=script_json(meta), DATA=data)
    page = re.sub(r"__(TITLE|IMPORTMAP|SCENE|META|DATA)__", lambda m: fills[m.group(1)], template)
    out = run_dir / "view.html"
    out.write_text(page, encoding="utf-8")
    print(f"viewer: wrote {out} ({out.stat().st_size / 1e6:.1f} MB, {len(scene.get('bodies', []))} bodies, "
          f"{math.ceil(n_frames / step)} frames)")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run_dir", type=Path)
    ap.add_argument("--open", action="store_true", help="open the page in the default browser")
    ap.add_argument("--rig", choices=["bugsorter"],
                    help="draw the bench tower round a holder-box run (rig.py; display only, sizes estimated)")
    args = ap.parse_args()
    out = build(args.run_dir, args.rig)
    if args.open:
        os.startfile(out)


if __name__ == "__main__":
    main()
