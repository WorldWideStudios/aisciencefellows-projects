import json
import subprocess
import sys
from pathlib import Path

from baebugs import doctor

ROOT = Path(__file__).resolve().parent.parent


def test_quick_report_structure(tmp_path):
    out = tmp_path / "r.json"
    p = subprocess.run([sys.executable, "-m", "baebugs.doctor", "--quick", "--json", str(out)],
                       cwd=ROOT, capture_output=True, text=True, timeout=300, check=False)
    assert p.returncode in (0, 1), p.stderr
    rep = json.loads(out.read_text())
    assert rep["quick"] is True
    names = {r["name"] for r in rep["results"]}
    assert {"pytest", "ruff", "imports", "notebooks", "resolve", "axe a11y"} <= names
    for r in rep["results"]:
        assert r["status"] in ("PASS", "FAIL", "SKIP")
        assert set(r) == {"name", "status", "seconds", "detail"}
        assert r["detail"]
    heavy = [r for r in rep["results"] if r["name"] in doctor.HEAVY]
    assert heavy and all(r["status"] == "SKIP" and r["detail"] == "--quick" for r in heavy)
    assert sum(rep["counts"].values()) == len(rep["results"])
    assert (p.returncode == 1) == (rep["counts"]["FAIL"] > 0)
    assert "CHECK" in p.stdout and "SKIP is not a pass" in p.stdout


def test_failures_are_reported_not_hidden():
    def boom():
        raise RuntimeError("x")

    def skip():
        raise doctor.Skip("because")

    assert doctor.run_check("a", boom)["status"] == "FAIL"
    r = doctor.run_check("b", skip)
    assert (r["status"], r["detail"]) == ("SKIP", "because")
    assert doctor.run_check("c", lambda: "ok")["status"] == "PASS"
