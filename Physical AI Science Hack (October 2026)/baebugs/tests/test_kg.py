import subprocess

import numpy as np

from baebugs.kg import KGLedger, decide, lomo_methods


def ins(i, w, spread=0.02, order="Hymenoptera", family="Apidae", L=None):
    rng = np.random.default_rng(i)
    sizes = {m: {"width_mm": w * (1 + rng.normal(0, spread)), "length_mm": (L or 3 * w)} for m in
             ("teacher", "student", "fastsam", "skimage")}
    return {"insect_id": f"g{i}#0", "taxon": {"order": order, "family": family}, "sizes": sizes, "efd": None}


def test_decision_matrix_cells():
    xs = [ins(i, 6 + 0.01 * i) for i in range(120)]            # agreeing, in-distribution
    xs.append(ins(500, 6.0, spread=0.6))                      # methods disagree, in range -> LABEL
    xs.append(ins(501, 0.4, L=25.0))                          # agree, far outside -> VIP
    xs.append(ins(502, 0.4, spread=0.6, L=25.0))              # disagree + outside -> STEP-IN
    decide(xs)
    d = {x["insect_id"]: x["decision"] for x in xs}
    assert d["g0#0"] == "AUTO" and d["g500#0"] == "LABEL" and d["g501#0"] == "VIP" and d["g502#0"] == "STEP-IN"
    assert xs[0]["tray"] == "PERF-5" and xs[0]["human"] is False


def test_lomo_flags_biased_method():
    xs = [ins(i, 5.0) for i in range(50)]
    for x in xs:
        x["sizes"]["skimage"]["width_mm"] *= 1.3                # ellipse axes run wide
    lo = lomo_methods(xs)
    assert lo["skimage"]["median_rel_dev"] > 0.2 > lo["teacher"]["median_rel_dev"]


def test_ledger_break_point_per_insect(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    xs = decide([ins(i, 5 + 0.01 * i) for i in range(30)])
    led = KGLedger(tmp_path, push=False, push_every=10)
    roots = [led.append(x)["root"] for x in xs]
    assert len(set(roots)) == 30 and len(led.path.read_text().splitlines()) == 30
    led.flush("test")
    log = subprocess.run(["git", "-C", str(tmp_path), "log", "--oneline"], capture_output=True, text=True, check=False).stdout
    assert "KG BP test" in log
