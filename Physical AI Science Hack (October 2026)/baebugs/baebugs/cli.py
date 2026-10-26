"""baebugs analyze --image tray.jpg --px-per-mm 40  (or --camera 0 --aruco-mm 10)"""
from __future__ import annotations

import argparse
import json

import cv2

from .measure import annotate, px_per_mm_from_aruco
from .pipeline import analyze


def main(argv=None):
    ap = argparse.ArgumentParser("baebugs")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("analyze")
    src = a.add_mutually_exclusive_group(required=True)
    src.add_argument("--image")
    src.add_argument("--camera", type=int)
    scale = a.add_mutually_exclusive_group(required=True)
    scale.add_argument("--px-per-mm", type=float)
    scale.add_argument("--aruco-mm", type=float, help="side of ArUco marker in view")
    a.add_argument("--yolo", help="YOLO weights (.pt); omit for classical-only")
    a.add_argument("--sieves", default=None)
    a.add_argument("--insects", default=None)
    a.add_argument("--out", default="runs/latest")
    args = ap.parse_args(argv)

    if args.image:
        img = cv2.imread(args.image)
    else:
        from .camera import capture
        img = capture(args.camera)
    ppm = args.px_per_mm or px_per_mm_from_aruco(img, args.aruco_mm)
    if not ppm:
        raise SystemExit("could not find ArUco marker for scale")

    from .sieve import load_yaml
    res = analyze(img, ppm, args.yolo,
                  load_yaml(args.sieves) if args.sieves else None,
                  load_yaml(args.insects) if args.insects else None)
    import os
    os.makedirs(args.out, exist_ok=True)
    cv2.imwrite(f"{args.out}/annotated.jpg", annotate(img, res["measurements"]))
    report = {"px_per_mm": ppm,
              "measurements": [m.to_dict() for m in res["measurements"]],
              "plan": res["plan"].to_dict(),
              "preflight_errors": res["preflight_errors"]}
    with open(f"{args.out}/report.json", "w") as f:
        json.dump(report, f, indent=2)
    print(json.dumps(report["plan"], indent=2))
    if report["preflight_errors"]:
        print("PREFLIGHT ERRORS:", report["preflight_errors"])


if __name__ == "__main__":
    main()
