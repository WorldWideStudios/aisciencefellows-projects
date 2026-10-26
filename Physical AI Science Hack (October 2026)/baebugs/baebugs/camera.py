"""USB camera / microscope capture."""
from __future__ import annotations

import cv2


def capture(index: int = 0, width: int | None = None, height: int | None = None,
            warmup: int = 5):
    cap = cv2.VideoCapture(index)
    if width:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    if height:
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    try:
        frame = None
        for _ in range(warmup):  # let auto-exposure settle
            _ok, frame = cap.read()
        if frame is None:
            raise RuntimeError(f"no frame from USB camera {index}")
        return frame
    finally:
        cap.release()
