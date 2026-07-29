#!/usr/bin/env python3
"""CLI: audit Run 2 data organization and write report under post-run/."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "ml"))

from analysis.run2_data_audit import audit_run2_data, format_audit_markdown, write_audit_report  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit scattered Run 2 data artifacts")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print JSON to stdout instead of markdown summary",
    )
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="Do not write files under data/screens/2/post-run/",
    )
    args = parser.parse_args()

    report = audit_run2_data()
    if args.no_write:
        payload = report.to_dict()
    else:
        md_path = write_audit_report(report)
        payload = report.to_dict()
        payload["report_path"] = str(md_path)
        print(f"Wrote {md_path}", file=sys.stderr)

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(format_audit_markdown(report))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
