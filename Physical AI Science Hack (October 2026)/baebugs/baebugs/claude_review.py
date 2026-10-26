"""Optional third opinion: Claude looks at the annotated image + measurements
and flags debris, overlapping bodies, or flagged sizes before the arm moves.
Advisory only - it never changes the plan by itself."""
from __future__ import annotations

import base64
import json
import os

import cv2

PROMPT = """You are QA for an insect sieving robot. The image shows a sample tray
with each detection labelled LENGTHxWIDTH mm (red = the two vision models disagreed).
Measurements JSON follows. Reply with JSON only:
{"debris_indices": [...], "overlapping_indices": [...], "notes": "...",
 "ok_to_sieve": true|false}"""


def review(annotated_bgr, measurements, model=None) -> dict:
    import anthropic  # optional dependency
    _ok, buf = cv2.imencode(".jpg", annotated_bgr)
    b64 = base64.b64encode(buf.tobytes()).decode()
    data = [m.to_dict() for m in measurements]
    msg = anthropic.Anthropic().messages.create(
        model=model or os.environ.get("BAEBUGS_CLAUDE_MODEL", "claude-opus-5-5"),
        max_tokens=800,
        messages=[{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64",
                                         "media_type": "image/jpeg", "data": b64}},
            {"type": "text", "text": PROMPT + "\n" + json.dumps(data)}]}])
    text = msg.content[0].text
    return json.loads(text[text.find("{"): text.rfind("}") + 1])
