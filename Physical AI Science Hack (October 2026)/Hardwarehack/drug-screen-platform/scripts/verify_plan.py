"""
Verify a plate layout's pipetting plan by simulating every transfer.

Kept for existing habits; same as ``uv run plate check``.

Usage
-----
    uv run python scripts/verify_plan.py                     # built-in example plate
    uv run python scripts/verify_plan.py my_plate.json       # saved layout
    uv run python scripts/verify_plan.py my_plate.json --volume 100 --min-transfer 5

Exit code is 0 if every well checks out, 1 otherwise.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]

from planning import example_layout  # noqa: E402,F401  (re-exported for tests)

if __name__ == "__main__":
    from cli.plate import app  # noqa: E402

    app(["check", *sys.argv[1:]])
