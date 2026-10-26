"""Frame holder, rebuilt from the "FRAME HOLDER" drawing in a friend's ChatGPT chat
(Downloads\\frame_holder_preview.png, itself "approximate reconstruction from four
reference photos"). The chat's own files can't be downloaded from a share link.

From the drawing: body 140 x 104 x 25 mm, open centre 122 x 82 mm through the bottom,
a U-shaped finger notch in the middle of each long wall, a 22 mm mounting tab on one
short end with a 6 mm hole. Measured off the drawing (about 0.37 mm per pixel): notch
about 34 mm wide and 21.5 mm deep, tab about 4.5 mm thick, hole centre about 6.5 mm in
from the tab's end at mid-height. WALL and LEDGE_T can't be read from the drawing; the
values below were adopted as the working dimensions on 2026-10-24 (see
WORKING_DIMENSIONS.md). Change them here if a measured part disagrees; the inserts follow.

Prints with the flat base on the bed, no supports.

Run from this folder:  <venv python> frame_holder.py
"""
import json
import cadquery as cq
from cadkit import export_all

L, W, H = 140.0, 104.0, 25.0      # frame body, excluding the tab
OPEN_L, OPEN_W = 122.0, 82.0      # open centre through the bottom
WALL = 4.0                        # working value: side wall thickness
LEDGE_T = 3.0                     # working value: thickness of the inner ledge at the bottom
NOTCH_W, NOTCH_D = 34.0, 21.5     # finger notch width and depth from the top edge
TAB_L, TAB_T = 22.0, 4.5          # mounting tab length (out from the +X end) and thickness
HOLE_D, HOLE_FROM_END = 6.0, 6.5  # mounting hole


def frame():
    body = cq.Workplane("XY").box(L, W, H, centered=(True, True, False))
    body = body.cut(cq.Workplane("XY").box(L - 2 * WALL, W - 2 * WALL, H, centered=(True, True, False))
                    .translate((0, 0, LEDGE_T)))
    body = body.cut(cq.Workplane("XY").box(OPEN_L, OPEN_W, H + 2, centered=(True, True, False))
                    .translate((0, 0, -1)))
    r = NOTCH_W / 2
    z_c = H - NOTCH_D + r   # centre of the notch's round bottom
    notch = (cq.Workplane("XZ").center(0, z_c).circle(r).extrude(W / 2 + 1, both=True)
             .union(cq.Workplane("XY").box(NOTCH_W, W + 2, H - z_c + 1, centered=(True, True, False))
                    .translate((0, 0, z_c))))
    body = body.cut(notch)
    tab = cq.Workplane("XY").box(TAB_L + 1, TAB_T, H, centered=(False, True, False)).translate((L / 2 - 1, 0, 0))
    hole = (cq.Workplane("XZ").center(L / 2 + TAB_L - HOLE_FROM_END, H / 2).circle(HOLE_D / 2)
            .extrude(TAB_T, both=True))
    return body.union(tab).cut(hole)


if __name__ == "__main__":
    print(json.dumps(export_all(frame(), "frame_holder", {
        "cavity_mm": [L - 2 * WALL, W - 2 * WALL], "open_centre_mm": [OPEN_L, OPEN_W],
        "ledge_mm": {"short_ends": (L - 2 * WALL - OPEN_L) / 2, "long_sides": (W - 2 * WALL - OPEN_W) / 2},
        "working_values": ["WALL", "LEDGE_T"]}), indent=2))
