#!/usr/bin/env python3
"""Generate Run 2 post-run artifacts (timing, reader metadata, plate map, assay summary)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "ml"))

from analysis.run2_artifacts import write_run2_artifacts  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Run 2 post-run artifacts")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print written paths as JSON",
    )
    args = parser.parse_args()

    paths = write_run2_artifacts()
    payload = {k: str(v) for k, v in paths.items()}
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        for name, path in paths.items():
            print(f"Wrote {path} ({name})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
