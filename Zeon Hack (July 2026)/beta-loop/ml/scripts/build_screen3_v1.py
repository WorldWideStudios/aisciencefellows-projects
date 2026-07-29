#!/usr/bin/env python3
"""Backward-compatible wrapper — use ml/scripts/build_screen3.py instead."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

if __name__ == "__main__":
    if "--version" not in sys.argv:
        sys.argv[1:1] = ["--version", "1"]
    runpy.run_path(str(Path(__file__).resolve().parent / "build_screen3.py"), run_name="__main__")
