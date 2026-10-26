"""Repo stress test ("doctor", milestone BP5). One command, pass/fail per check, nothing hidden.

    python -m baebugs.doctor [--json out.json] [--quick]

Statuses: PASS, FAIL, SKIP (always with a reason). Exit code is 1 if any check FAILs, else 0.
SKIP never counts as a pass in the summary line. --quick skips the heavy checks (pytest, ruff, pip
check, STL, html-validate, axe, npm/brew doctor). Bring-your-own checks: see docs/HOWTO.md
(checks.d/*.py, or a directory in $BAEBUGS_DOCTOR_CHECKS).
"""
from __future__ import annotations

import argparse
import importlib
import importlib.util
import json
import os
import pkgutil
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PASS, FAIL, SKIP = "PASS", "FAIL", "SKIP"


class Skip(Exception):
    """Raised by a check to report SKIP with a reason."""


class Fail(Exception):
    """Raised by a check to report FAIL with a detail."""


def _run(cmd, timeout=900, cwd=ROOT):
    try:
        p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        raise Fail(f"timeout after {timeout}s: {' '.join(map(str, cmd))}")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def _last(text, n=1):
    lines = [x.strip() for x in text.strip().splitlines() if x.strip()]
    return " | ".join(lines[-n:]) if lines else "(no output)"


def _need(tool):
    if shutil.which(tool) is None:
        raise Skip(f"{tool} not on PATH")


def _html_files():
    """Full HTML documents only: site/ pages. dashboard/twin/bench_twin.html is an artifact source fragment
    (no <html>/<head>, wrapped at publish time) and is validated through its full copy site/twin/index.html."""
    out = []
    site = ROOT / "site"
    if site.is_dir():
        out += sorted(site.rglob("*.html"))
    return out


# ---------------------------------------------------------------- checks

def c_pytest():
    rc, out = _run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                    "--ignore=tests/test_doctor.py"], timeout=1800)
    if rc != 0:
        raise Fail(_last(out))
    return _last(out)


def c_ruff():
    if shutil.which("ruff"):
        cmd = ["ruff"]
    else:
        rc, _ = _run([sys.executable, "-m", "ruff", "--version"])
        if rc != 0:
            rc, out = _run([sys.executable, "-m", "pip", "install", "-q", "ruff"])
            if rc != 0:
                raise Skip("ruff missing and pip install failed: " + _last(out))
        cmd = [sys.executable, "-m", "ruff"]
    rc, out = _run(cmd + ["check", "baebugs", "tests", "--statistics"])
    if rc == 0:
        return _last(out)
    total = 0
    for ln in out.splitlines():
        parts = ln.split()
        if parts and parts[0].isdigit():
            total += int(parts[0])
    raise Fail(f"{total or '?'} violation(s); run `ruff check baebugs tests` ({_last(out)})")


def c_pip_check():
    rc, out = _run([sys.executable, "-m", "pip", "check"])
    if rc != 0:
        raise Fail(_last(out, 3))
    return _last(out)


def c_imports():
    bad, n = [], 0
    pkg = importlib.import_module("baebugs")
    names = [m.name for m in pkgutil.walk_packages(pkg.__path__, "baebugs.")]
    for name in names:
        n += 1
        try:
            importlib.import_module(name)
        except BaseException as e:  # noqa: BLE001 - SystemExit from careless modules counts as a failure too
            bad.append(f"{name}: {type(e).__name__}: {e}")
    if bad:
        raise Fail(f"{len(bad)}/{n} failed: " + "; ".join(bad[:5]))
    return f"{n} modules imported"


def c_notebooks():
    nbs = sorted((ROOT / "notebooks").glob("*.ipynb"))
    if not nbs:
        raise Skip("no notebooks/*.ipynb")
    bad = []
    for p in nbs:
        try:
            nb = json.loads(p.read_text(encoding="utf-8"))
            if nb.get("nbformat") != 4 or not isinstance(nb.get("cells"), list) or "metadata" not in nb:
                raise ValueError(f"not nbformat v4 (nbformat={nb.get('nbformat')})")
            for i, c in enumerate(nb["cells"]):
                if c.get("cell_type") not in ("code", "markdown", "raw") or "source" not in c:
                    raise ValueError(f"bad cell {i}")
        except Exception as e:  # noqa: BLE001
            bad.append(f"{p.name}: {e}")
    if bad:
        raise Fail(f"{len(bad)}/{len(nbs)} bad: " + "; ".join(bad[:5]))
    return f"{len(nbs)} notebooks parse as nbformat v4 (not executed)"


def c_stl():
    try:
        import trimesh
    except ImportError:
        raise Skip("trimesh not installed")
    files = sorted(list((ROOT / "print").glob("**/stl/*.stl")) + list((ROOT / "opentrons" / "stl").glob("*.stl")))
    if not files:
        raise Skip("no STL files found")
    bad = []
    for p in files:
        try:
            m = trimesh.load(str(p), force="mesh")
            if not m.is_watertight:
                bad.append(f"{p.relative_to(ROOT)} not watertight")
        except Exception as e:  # noqa: BLE001
            bad.append(f"{p.relative_to(ROOT)} load error: {e}")
    if bad:
        raise Fail(f"{len(bad)}/{len(files)} bad: " + "; ".join(bad[:4]) + (" ..." if len(bad) > 4 else ""))
    return f"{len(files)} STLs load and are watertight"


def c_labware_json():
    files = sorted((ROOT / "opentrons" / "labware").glob("**/*.json"))
    if not files:
        raise Skip("no opentrons/labware/*.json")
    bad = []
    for p in files:
        try:
            json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            bad.append(f"{p.name}: {e}")
    if bad:
        raise Fail("; ".join(bad))
    return f"{len(files)} labware JSON files parse"


def c_html_validate():
    files = _html_files()
    if not files:
        raise Skip("no HTML files")
    _need("node")
    _need("npx")
    bad = []
    for p in files:
        rc, out = _run(["npx", "--yes", "html-validate", str(p)], timeout=300)
        if rc != 0:
            summ = next((x.strip() for x in out.splitlines() if "problem" in x), _last(out))
            rules = sorted({x.split()[-1] for x in out.splitlines() if " error " in x or " warning " in x})
            bad.append(f"{p.relative_to(ROOT)}: {summ} [{', '.join(rules)}]")
    if bad:
        raise Fail("; ".join(bad))
    return f"{len(files)} HTML file(s) valid"


_AXE_JS = r"""
const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const axeSrc = fs.readFileSync(process.argv[2], 'utf8');
  const results = [];
  const browser = await chromium.launch();
  for (const f of process.argv.slice(3)) {
    const page = await browser.newPage();
    await page.goto('file://' + f);
    await page.evaluate(axeSrc);
    const r = await page.evaluate(() => axe.run());
    results.push({file: f, violations: r.violations.map(v => ({id: v.id, impact: v.impact, nodes: v.nodes.length}))});
    await page.close();
  }
  await browser.close();
  console.log('AXE_JSON ' + JSON.stringify(results));
})().catch(e => { console.error(String(e)); process.exit(2); });
"""


def _find_axe():
    cache = Path.home() / ".cache" / "baebugs-doctor"
    for base in (ROOT / "node_modules", cache / "node_modules"):
        p = base / "axe-core" / "axe.min.js"
        if p.exists():
            return p
    _need("npm")
    cache.mkdir(parents=True, exist_ok=True)
    rc, out = _run(["npm", "install", "--no-audit", "--no-fund", "--prefix", str(cache), "axe-core"], timeout=300)
    p = cache / "node_modules" / "axe-core" / "axe.min.js"
    if rc != 0 or not p.exists():
        raise Skip("axe-core unavailable: " + _last(out))
    return p


def c_a11y():
    files = _html_files()
    if not files:
        raise Skip("no HTML files")
    _need("node")
    axe = _find_axe()
    with tempfile.TemporaryDirectory() as td:
        js = Path(td) / "axe_run.js"
        js.write_text(_AXE_JS)
        rc, out = _run(["node", str(js), str(axe)] + [str(p) for p in files], timeout=300)
    line = next((x for x in out.splitlines() if x.startswith("AXE_JSON ")), None)
    if rc != 0 or line is None:
        if "Cannot find module 'playwright'" in out or "Executable doesn't exist" in out:
            raise Skip("playwright/chromium unavailable: " + _last(out))
        raise Fail("axe run errored: " + _last(out, 2))
    res = json.loads(line[len("AXE_JSON "):])
    bad = [f"{Path(r['file']).name}: " + ", ".join(f"{v['id']}({v['impact']},x{v['nodes']})" for v in r["violations"])
           for r in res if r["violations"]]
    if bad:
        raise Fail("; ".join(bad))
    return f"{len(res)} page(s), 0 axe violations"


def _not_ok(out):
    lines, found = out.splitlines(), []
    for i, x in enumerate(lines):
        if x.strip().lower() == "not ok" and i > 0:
            found.append(f"{lines[i - 1].replace('Checking', '').strip()}: {(lines[i + 1] if i + 1 < len(lines) else '')[:90]}")
    return "; ".join(found)


def c_npm_doctor():
    _need("npm")
    rc, out = _run(["npm", "doctor"], timeout=300)
    if rc != 0:
        raise Fail(_not_ok(out) or _last(out, 2))
    if "not ok" in out.lower():
        raise Fail(_not_ok(out))
    return "npm doctor ok"


def c_brew_doctor():
    _need("brew")
    rc, out = _run(["brew", "doctor"], timeout=300)
    if rc != 0:
        raise Fail(_last(out, 2))
    return "Your system is ready to brew"


def c_gum():
    _need("gum")
    rc, out = _run(["gum", "--version"])
    if rc != 0:
        raise Fail(_last(out))
    return _last(out)


def c_resolve():
    from baebugs.resolve import references  # noqa: F401
    return "baebugs.resolve.references importable"


def c_graph():
    """Graph pack is current and every agent surface (Python, npx) returns the same root."""
    import json as _j

    from baebugs import mvp
    built = mvp.build(ROOT)["root"]
    packed = mvp.load(ROOT / mvp.OUT)["root"]
    if built != packed:
        raise Fail(f"site/mvp/mvp.json is stale ({packed[:12]} != {built[:12]}); run python -m baebugs.mvp")
    if shutil.which("node"):
        rc, out = _run(["node", "bin/baebugs.mjs", "get", "root"], timeout=60)
        if rc != 0 or _j.loads(out)["root"] != packed:
            raise Fail("npx surface returns a different root")
    return f"root {packed[:12]} (python == npx == pack)"


HEAVY = {"pytest", "ruff", "pip check", "stl watertight", "html-validate", "axe a11y", "npm doctor", "brew doctor"}
CHECKS = [
    ("pytest", c_pytest), ("ruff", c_ruff), ("pip check", c_pip_check), ("imports", c_imports),
    ("notebooks", c_notebooks), ("stl watertight", c_stl), ("labware json", c_labware_json),
    ("html-validate", c_html_validate), ("axe a11y", c_a11y), ("npm doctor", c_npm_doctor),
    ("brew doctor", c_brew_doctor), ("gum", c_gum), ("resolve", c_resolve), ("graph root", c_graph),
]


def _user_checks():
    """checks.d/*.py in the repo, plus any dir in $BAEBUGS_DOCTOR_CHECKS (os.pathsep-separated).
    Each file defines run() -> detail string; raise doctor.Skip / doctor.Fail, or any exception (= FAIL)."""
    dirs = [ROOT / "checks.d"] + [Path(d) for d in os.environ.get("BAEBUGS_DOCTOR_CHECKS", "").split(os.pathsep) if d]
    out = []
    for d in dirs:
        for f in (sorted(d.glob("*.py")) if d.is_dir() else []):
            def _load(f=f):
                spec = importlib.util.spec_from_file_location(f"doctor_user_{f.stem}", f)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                return str(mod.run() or "ok")
            out.append((f"user:{f.stem}", _load))
    return out


def run_check(name, fn, quick=False):
    t0 = time.time()
    if quick and name in HEAVY:
        status, detail = SKIP, "--quick"
    else:
        try:
            status, detail = PASS, str(fn())
        except Skip as e:
            status, detail = SKIP, str(e)
        except Fail as e:
            status, detail = FAIL, str(e)
        except BaseException as e:  # noqa: BLE001
            status, detail = FAIL, f"{type(e).__name__}: {e} [{traceback.format_exc().splitlines()[-3].strip()}]"
    return {"name": name, "status": status, "seconds": round(time.time() - t0, 2), "detail": detail or "-"}


def render(results):
    w = max(len(r["name"]) for r in results)
    lines = [f"{'CHECK':<{w}}  {'STATUS':<6}  {'TIME':>7}  DETAIL", "-" * (w + 40)]
    for r in results:
        d = r["detail"].replace("\n", " ")
        lines.append(f"{r['name']:<{w}}  {r['status']:<6}  {r['seconds']:>6.1f}s  {d[:200]}")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="baebugs.doctor", description=__doc__.split("\n")[0])
    ap.add_argument("--json", metavar="OUT", help="also write the report as JSON")
    ap.add_argument("--quick", action="store_true", help="skip heavy checks (pytest, ruff, STL, html, axe, npm, brew)")
    a = ap.parse_args(argv)
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    results = []
    for name, fn in CHECKS + _user_checks():
        r = run_check(name, fn, a.quick)
        results.append(r)
        print(f"[{r['status']}] {name} ({r['seconds']}s)", file=sys.stderr, flush=True)
    print(render(results))
    counts = {s: sum(r["status"] == s for r in results) for s in (PASS, FAIL, SKIP)}
    print(f"\n{counts[PASS]} PASS, {counts[FAIL]} FAIL, {counts[SKIP]} SKIP (SKIP is not a pass)")
    if a.json:
        Path(a.json).write_text(json.dumps({"quick": a.quick, "counts": counts, "results": results}, indent=2))
    return 1 if counts[FAIL] else 0


if __name__ == "__main__":
    sys.exit(main())
