"""Build the Sieve Render Lab: every session's sim replays in the one viewer, with a Run menu added to the
viewer's own options panel (picking a run opens that run's viewer). runs_def.py lists the runs.

Usage (Windows venv, from sim/render_site/):  ..\\..\\.venv\\Scripts\\python.exe build_site.py
Writes out/index.html (it forwards to the first run) and out/runs/<id>/view.html next to this script; out/ is
gitignored. A run whose view.html is missing or older than its traj.npz is rebuilt with viewer.py --rig bugsorter.
Replays load three.js from jsDelivr (three@0.186.1, the version sim/vendor pins) instead of data: URLs, so the
published page's CSP allows them. The run folders live in each worktree's sim/out/ (gitignored, this laptop only).
run_onebox.py runs sorter.py with the optimizer's one-box seesaw patch, for one-piece designs (gated, plinko).
"""
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_SIM = HERE.parent
PY = REPO_SIM.parent / ".venv" / "Scripts" / "python.exe"

CDN_MAP = json.dumps({"imports": {
    "three": "https://cdn.jsdelivr.net/npm/three@0.186.1/build/three.module.min.js",
    "three/addons/OrbitControls.js": "https://cdn.jsdelivr.net/npm/three@0.186.1/examples/jsm/controls/OrbitControls.js"}})

from runs_def import RUNS  # noqa: E402  (grouped, credited run list)


def fmt_stroke(st):
    if not st:
        return "none"
    if st.get("profile") == "seesaw":
        s = f"seesaw ±{st.get('deg', 10):g}°, {st.get('period_s', 2):g} s per rock"
        if st.get("vib_mm"):
            s += f" + buzz {st['vib_mm']:g} mm at {st.get('vib_hz', 40):g} Hz"
        return s
    return ", ".join(f"{k}={v}" for k, v in st.items())


def fmt_mix(mix):
    return ", ".join(f"{k.replace('_', ' ')} {v}" for k, v in (mix or {}).items()) or "none"


def fmt_clump(cl):
    if not cl:
        return None
    if isinstance(cl, str):
        return cl
    kinds = cl.get("kinds") or {k: v for k, v in cl.items() if isinstance(v, int)}
    s = ", ".join(f"{k.replace('_', ' ')} {v}" for k, v in kinds.items())
    if cl.get("bond") is not None:
        s += f"; bonds {cl['bond']}"
    return s


def build_view(run_dir: Path):
    view = run_dir / "view.html"
    newest = max((run_dir / "traj.npz").stat().st_mtime, (REPO_SIM / "viewer_template.html").stat().st_mtime,
                 (REPO_SIM / "viewer.py").stat().st_mtime)
    if not view.exists() or view.stat().st_mtime < newest:
        subprocess.run([str(PY), "viewer.py", str(run_dir), "--rig", "bugsorter"], cwd=REPO_SIM, check=True,
                       capture_output=True)
    return view


def main():
    site = HERE / "out"
    meta = []
    pending = []
    for rid, group, title, rdir, note in RUNS:
        res_p = rdir / "results.json"
        if not res_p.exists() or not (rdir / "traj.npz").exists():
            print(f"skip {rid}: not rendered yet ({rdir})")
            continue
        try:
            view = build_view(rdir)
        except subprocess.CalledProcessError as e:
            print(f"skip {rid}: viewer failed: {e.stderr[-300:]!r}")
            continue
        html = view.read_text(encoding="utf-8")
        html, n = re.subn(r'<script type="importmap">.*?</script>', lambda m: f'<script type="importmap">{CDN_MAP}</script>',
                          html, count=1, flags=re.S)
        if n != 1:
            sys.exit(f"{rid}: importmap not found")
        pending.append((rid, html, note))
        out = site / "runs" / rid / "view.html"
        r = json.loads(res_p.read_text(encoding="utf-8"))
        cfg = r["config"]
        zones = [z["name"] if isinstance(z, dict) else z for z in r.get("zones", [])]
        counts = r.get("counts", {})
        used = [z for z in zones if any(counts.get(k, {}).get(z, 0) for k in counts)]
        clumps = r.get("clumps") or {}
        cm = {}
        for key in ("free_frac", "t50_s", "t90_s", "largest_cluster"):
            v = clumps.get(key)
            if isinstance(v, (int, float)) or v is None:
                cm[key] = v
        meta.append({
            "id": rid, "group": group, "title": title, "note": note,
            "config": {
                "Design": cfg.get("design"),
                "Motion": fmt_stroke(cfg.get("stroke")),
                "Grains": fmt_mix(cfg.get("mix")) if cfg.get("mix") else None,
                "Clump": fmt_clump(cfg.get("clump")),
                "Spray": (cfg.get("spray") or {}).get("jets", "default") if isinstance(cfg.get("spray"), dict) else (cfg.get("spray") or "off"),
                "Run": f"{cfg.get('settle_s', 1):g} s settle + {cfg.get('duration_s'):g} s, seed {cfg.get('seed')}",
                "Contacts": f"dt {cfg.get('dt', 0) * 1000:g} ms, timeconst {cfg.get('contact', {}).get('timeconst', 0) * 1000:g} ms, friction {cfg.get('contact', {}).get('friction')}",
            },
            "zones": used,
            "counts": {k: {z: v.get(z, 0) for z in used} for k, v in counts.items()},
            "clump": cm,
            "wall_s": r.get("wall_s"), "resets": len(r.get("unstable_resets") or []),
        })
    # A "Run" picker at the top of each viewer's own options panel; picking one opens that run's viewer.
    groups = []
    for m in meta:
        if m["group"] not in groups:
            groups.append(m["group"])
    for rid, html, note in pending:
        opts = "".join(
            f'<optgroup label="{g}">' + "".join(
                f'<option value="{m["id"]}"{" selected" if m["id"] == rid else ""}>{m["title"]}</option>'
                for m in meta if m["group"] == g) + "</optgroup>" for g in groups)
        block = ('<section id="run-sec"><h2>Run</h2>'
                 f'<select id="run-pick" style="width:100%" aria-label="Run">{opts}</select>'
                 f'<div class="note">{note}</div></section>')
        html, n = re.subn(r'(<aside id="panel">)', lambda m_: m_.group(1) + "\n    " + block, html, count=1)
        if n != 1:
            sys.exit(f"{rid}: panel not found")
        js = ("<script>document.getElementById('run-pick').addEventListener('change',"
              "e=>{location.href='../'+e.target.value+'/view.html';});</script>")
        html = html.replace("</body>", js + "\n</body>", 1)
        out = site / "runs" / rid / "view.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(html, encoding="utf-8")
        print(f"ok {rid}: {out.stat().st_size / 1e6:.1f} MB")
    first = meta[0]["id"]
    (site / "index.html").write_text(
        "<title>Sieve Render Lab</title>\n"
        f'<script>location.replace("runs/{first}/view.html");</script>\n'
        f'<p style="font:15px system-ui;padding:16px"><a href="runs/{first}/view.html">Open the sim replays</a></p>\n',
        encoding="utf-8")
    print(f"index.html -> runs/{first}/view.html, {len(meta)} runs")


if __name__ == "__main__":
    main()
