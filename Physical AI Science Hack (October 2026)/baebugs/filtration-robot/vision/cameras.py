"""Open a camera by name instead of by number.

Windows renumbers cameras whenever one is plugged in or out, so tools take a name
(any part of it, case-insensitive, e.g. "XWF") or a plain number.

Usage: python cameras.py   # list cameras in the order OpenCV numbers them
"""
import cv2
from pygrabber.dshow_graph import FilterGraph


def camera_names():
    """Camera names in DirectShow order, which is the numbering cv2.CAP_DSHOW uses."""
    return FilterGraph().get_input_devices()


def find_camera(spec):
    """Camera number for `spec`: a number, or part of a camera's name."""
    if str(spec).isdigit():
        return int(spec)
    names = camera_names()
    matches = [i for i, name in enumerate(names) if str(spec).lower() in name.lower()]
    if len(matches) != 1:
        found = ", ".join(f"{i}: {n}" for i, n in enumerate(names)) or "none"
        problem = "no camera matches" if not matches else "more than one camera matches"
        raise SystemExit(f"{problem} '{spec}'. Cameras: {found}")
    return matches[0]


ROTATIONS = {0: None, 90: cv2.ROTATE_90_CLOCKWISE, 180: cv2.ROTATE_180, 270: cv2.ROTATE_90_COUNTERCLOCKWISE}


def rotate(frame, degrees):
    """Turn a frame clockwise by 0, 90, 180 or 270 degrees (for a camera mounted sideways or upside down)."""
    code = ROTATIONS[degrees % 360]
    return frame if code is None else cv2.rotate(frame, code)


def open_camera(spec, width=4000, height=3000):
    """Open a camera at its highest resolution (asking for more than it has gets the most it offers)."""
    index = find_camera(spec)
    cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
    if not cap.isOpened():
        raise SystemExit(f"camera {index} not available (in use by another app?)")
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))  # compressed: full fps at high resolution over USB 2
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    return cap


if __name__ == "__main__":
    for i, name in enumerate(camera_names()):
        print(f"camera {i}: {name}")
