import json
import subprocess

from baebugs.git_ledger import GitLedger


def test_ledger_commits_each_break_point(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "w.pt").write_bytes(b"weights")
    led = GitLedger("run1", tmp_path, push=False)
    led.append("pull", {"images": 10})
    r = led.append("epoch_001", {"metrics": {"mAP50": 0.9}}, files={"best.pt": tmp_path / "w.pt"})
    assert r["n"] == 2 and len(r["root"]) == 64 and r["files"]["best.pt"]
    log = subprocess.run(["git", "-C", str(tmp_path), "log", "--oneline"], capture_output=True, text=True, check=False).stdout
    assert log.count("BP run1") == 2 and "epoch_001" in log
    assert led.verify()
    lines = led.path.read_text().splitlines()
    rec = json.loads(lines[0]); rec["payload"]["images"] = 11; lines[0] = json.dumps(rec)
    led.path.write_text("\n".join(lines) + "\n")
    assert not led.verify()
