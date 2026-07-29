#!/usr/bin/env python3
"""Render nitrocefin plate map JSON files as PNG images."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "ml"))

from analysis.plate_viz import load_and_render  # noqa: E402


def _collect_all_runs(data_dir: Path, repo_root: Path) -> list[Path]:
    paths: list[Path] = []
    paths.extend(sorted(data_dir.glob("screens/**/plate_map.json")))
    paths.extend(sorted(data_dir.glob("plate_map_r*.json")))
    workflow = repo_root / "ml" / "workflows" / "compound_selection"
    paths.extend(sorted(workflow.glob("plate_map_r*_draft.json")))
    return paths


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Render plate map JSON as PNG with colored wells and labels."
    )
    parser.add_argument(
        "plate_map",
        nargs="?",
        help="Path to plate_map.json or plate_map_r{N}.json",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output PNG path (default: alongside input JSON)",
    )
    parser.add_argument(
        "--by",
        choices=("sample_type", "compound", "concentration"),
        default="sample_type",
        help="Color wells by sample type (default), compound, or concentration labels",
    )
    parser.add_argument(
        "--cols",
        nargs="+",
        help="Deprecated; kept for compatibility",
    )
    parser.add_argument(
        "--all-runs",
        action="store_true",
        help="Render all versioned snapshots, active maps, and drafts under data/ and ml/workflows/",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=REPO_ROOT / "data",
        help="Data directory root (default: repo data/)",
    )
    args = parser.parse_args()

    if args.all_runs:
        paths = _collect_all_runs(args.data_dir, REPO_ROOT)
        if not paths:
            print("No plate map JSON files found.", file=sys.stderr)
            return 1
        for path in paths:
            out = load_and_render(path, cols=args.cols, color_by=args.by)
            print(out)
        return 0

    if not args.plate_map:
        parser.error("plate_map path is required unless --all-runs is set")

    out = load_and_render(args.plate_map, args.output, cols=args.cols, color_by=args.by)
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
