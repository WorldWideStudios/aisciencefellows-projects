"""Simulate stage: deterministic validation, no LLM.

Runs the zeon-projects skill's validator (structural checks, node params against
real skill signatures, and — because it scans the whole project — the round's
inputs/<round_id>.json preset against the workflow it targets) and, if `zeon` is
authenticated and the command has landed, the server-side `zeon verify` IK/collision
check. As of this CLI build `zeon verify` prints "Not yet implemented" — that's
treated as a skip, not a failure, so Simulate degrades to validate.py-only rather
than blocking every round on a command that doesn't exist yet.

Never touches beads directly except through beads_writer (the single writer).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "pipeline"))
import beads_writer as bw  # noqa: E402

# Vendored in the zeon-projects plugin skill, not this project — resolved from the
# marketplace cache path used elsewhere in this session. If the skill isn't
# installed, validate() reports that as a deviation rather than crashing.
_VALIDATE_CANDIDATES = [
    Path.home() / ".claude/plugins/marketplaces/zeon/skills/zeon-projects/scripts/validate.py",
    Path.home() / ".claude/plugins/cache/zeon/zeon-project-skill/b7d50f2bb25c/skills/zeon-projects/scripts/validate.py",
]


def _find_validate_script() -> Path | None:
    for p in _VALIDATE_CANDIDATES:
        if p.exists():
            return p
    return None


class SimulateResult:
    def __init__(self, ok: bool, errors: list[str], warnings: list[str], verify_skipped_reason: str | None):
        self.ok = ok
        self.errors = errors
        self.warnings = warnings
        self.verify_skipped_reason = verify_skipped_reason

    def reason(self) -> str:
        if self.ok:
            note = f" (zeon verify skipped: {self.verify_skipped_reason})" if self.verify_skipped_reason else ""
            return f"validate.py clean, {len(self.warnings)} warning(s){note}"
        return "; ".join(self.errors[:5]) + (f" (+{len(self.errors) - 5} more)" if len(self.errors) > 5 else "")


def run_validate(root: Path = PROJECT_ROOT) -> tuple[list[str], list[str]]:
    """Returns (errors, warnings) from scripts/validate.py --json, or one error
    entry if the script itself can't be found/run."""
    script = _find_validate_script()
    if script is None:
        return (["zeon-projects skill's scripts/validate.py not found — is the plugin installed?"], [])

    proc = subprocess.run(
        [sys.executable, str(script), str(root), "--json"],
        capture_output=True, text=True,
    )
    try:
        report = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return ([f"validate.py produced non-JSON output (exit {proc.returncode}): {proc.stdout[-500:]}"], [])

    def fmt(i):
        return f"{i['where']}: {i['msg']}" if isinstance(i, dict) and "where" in i else str(i)

    errors = [fmt(i) for i in report.get("errors", [])]
    warnings = [fmt(i) for i in report.get("warnings", [])]
    return errors, warnings


def run_zeon_verify() -> str | None:
    """Returns a skip reason (non-fatal) if verify isn't usable, else None on a
    clean pass. Raises only if verify actually reports real IK/collision errors."""
    proc = subprocess.run(["zeon", "verify"], capture_output=True, text=True)
    output = (proc.stdout + proc.stderr).strip()
    if "not yet implemented" in output.lower():
        return "not yet implemented on this zeon CLI build"
    if proc.returncode != 0:
        raise RuntimeError(f"zeon verify reported problems: {output[-1000:]}")
    return None


def simulate_round(round_id: str) -> SimulateResult:
    errors, warnings = run_validate()
    if errors:
        bw.set_stage(round_id, "deviated", reason=f"validate.py failed: {'; '.join(errors[:3])}")
        return SimulateResult(ok=False, errors=errors, warnings=warnings, verify_skipped_reason=None)

    try:
        skip_reason = run_zeon_verify()
    except RuntimeError as exc:
        bw.set_stage(round_id, "deviated", reason=str(exc))
        return SimulateResult(ok=False, errors=[str(exc)], warnings=warnings, verify_skipped_reason=None)

    result = SimulateResult(ok=True, errors=[], warnings=warnings, verify_skipped_reason=skip_reason)
    bw.set_stage(round_id, "simulated", reason=result.reason())
    return result


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python pipeline/simulate.py <round_id>", file=sys.stderr)
        sys.exit(2)
    res = simulate_round(sys.argv[1])
    print(res.reason())
    sys.exit(0 if res.ok else 1)
