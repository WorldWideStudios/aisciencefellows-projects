import ast
import json
import subprocess
import sys


def test_generated_kernel_saves_weights_and_fails_closed(tmp_path):
    subprocess.run([sys.executable, "kaggle/make_daisy_kernel.py", "--proto", "daisy/DAISY-BB-002a.json", "--out", str(tmp_path)],
                   check=True, capture_output=True)
    nb = json.loads(next(tmp_path.glob("*.ipynb")).read_text())
    src = "\n".join("".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code")
    ast.parse("\n".join(l for l in src.splitlines() if not l.lstrip().startswith("!")))
    assert "on_model_save" in src and "weights_saved" in src and "custody_check" in src and "CUSTODY BREAK" in src
    assert src.index("keep(best") < src.index("EVAL") if "EVAL" in src else True
