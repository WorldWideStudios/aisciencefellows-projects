"""Local vision-language model via Ollama (offline stand-in for the Claude QA
and label-reading steps). Default model: qwen2.5vl:3b (fits a 32 GB M1 Max).

Same contract as claude_review.review / essig_adapter.read_label_with_claude,
so `get_reviewer("ollama")` and `get_reviewer("claude")` are interchangeable.
Outputs are advisory and tagged 'inferred' when they enter an FCO.
"""
from __future__ import annotations

import base64
import json
import os
import urllib.request

import cv2

from .claude_review import PROMPT as QA_PROMPT

OLLAMA_URL = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
DEFAULT_MODEL = os.environ.get("BAEBUGS_OLLAMA_VLM", "qwen2.5vl:3b")

LABEL_PROMPT = ("Transcribe this insect specimen label. Reply JSON only with keys "
                "locality, lat_long [lat,lon], date, collector, method, elevation, "
                "det_by, specimen_no, scientificName. Use null when unreadable; never guess.")


def _b64(img_bgr, max_side=1024):
    h, w = img_bgr.shape[:2]
    s = min(1.0, max_side / max(h, w))
    if s < 1:
        img_bgr = cv2.resize(img_bgr, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    _ok, buf = cv2.imencode(".jpg", img_bgr, [cv2.IMWRITE_JPEG_QUALITY, 88])
    return base64.b64encode(buf.tobytes()).decode()


def chat_json(prompt: str, img_bgr=None, model=None, timeout=180) -> dict:
    msg = {"role": "user", "content": prompt}
    if img_bgr is not None:
        msg["images"] = [_b64(img_bgr)]
    body = json.dumps({"model": model or DEFAULT_MODEL, "messages": [msg],
                       "format": "json", "stream": False,
                       "options": {"temperature": 0}}).encode()
    req = urllib.request.Request(f"{OLLAMA_URL}/api/chat", body,
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        text = json.loads(r.read())["message"]["content"]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"_raw": text, "_parse_error": True}


def review(annotated_bgr, measurements, context: str = "", model=None) -> dict:
    data = [m.to_dict() for m in measurements]
    prompt = QA_PROMPT + ("\n" + context if context else "") + "\n" + json.dumps(data)[:6000]
    return chat_json(prompt, annotated_bgr, model)


def read_label(image_bgr, model=None) -> dict:
    return chat_json(LABEL_PROMPT, image_bgr, model)


def available(model=None) -> bool:
    try:
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=5) as r:
            names = {m["name"] for m in json.loads(r.read())["models"]}
        return (model or DEFAULT_MODEL) in names
    except Exception:  # noqa: BLE001 - fallback; the failure is recorded or degrades
        return False


def get_reviewer(backend: str = "ollama"):
    if backend == "ollama":
        return review
    from .claude_review import review as claude
    return claude
