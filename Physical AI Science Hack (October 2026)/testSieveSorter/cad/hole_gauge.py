"""Hole-size test coupon: find the real cut sizes before printing a full screen.

Print it flat (short print), then:
1. Check each hole with drill-bit shanks or calipers. FDM holes usually come
   out a little undersized; note how much at each size.
2. Pour each grain type over it and note the smallest hole each one passes.
Design screens from those measured numbers, not the nominal ones.

Run:  ..\\.venv\\Scripts\\python.exe hole_gauge.py
"""
import json
import cadquery as cq
from cadkit import export_all

T = 2.0          # plate thickness, close to a printed screen
GAP = 3.5        # web between holes
LABEL = 2.5      # text height
EMBOSS = 0.6     # raised label height (3 layers at 0.2 mm)
MARGIN = 4.0
ROWS = [
    [1.0 + 0.25 * i for i in range(13)],   # 1.00-4.00 mm in 0.25 steps
    [4.5 + 0.5 * i for i in range(8)],     # 4.5-8.0 mm in 0.5 steps
    [9.0 + 1.0 * i for i in range(4)],     # 9-12 mm in 1 mm steps
]


def gauge():
    pitch = [max(r) + GAP for r in ROWS]
    row_h = [max(r) + LABEL + 2 * GAP for r in ROWS]
    width = max(len(r) * p for r, p in zip(ROWS, pitch)) + 2 * MARGIN
    depth = sum(row_h) + 2 * MARGIN
    body = cq.Workplane("XY").box(width, depth, T, centered=False)
    y = depth - MARGIN
    for r, p, h in zip(ROWS, pitch, row_h):
        cy = y - GAP - max(r) / 2
        for i, d in enumerate(r):
            x = MARGIN + p * (i + 0.5)
            body = body.cut(cq.Workplane("XY").workplane(offset=-1).center(x, cy)
                            .circle(d / 2).extrude(T + 2))
            body = body.union(cq.Workplane("XY").workplane(offset=T)
                              .center(x, cy - max(r) / 2 - GAP / 2 - LABEL / 2)
                              .text(f"{d:g}", LABEL, EMBOSS))
        y -= h
    return body


if __name__ == "__main__":
    print(json.dumps(export_all(gauge(), "hole_gauge",
                                {"holes_mm": [d for r in ROWS for d in r]}), indent=2))
