#!/usr/bin/env python3
"""Extraction pass over the peel footage.

Two prompts, because the clips answer different questions:
  GOOD clips -> the how-to: steps, geometry, timing, verification
  BAD  clips -> the what-not-to-do: failure name, visible symptom, stated fix

Structured output on both, so the result lands as data rather than prose, and
every field carries the clip id + MM:SS that justifies it.

No pip dependencies: urllib + a gcloud access token.
"""

import json
import os
import subprocess
import sys
import urllib.request
import urllib.error

PROJECT = "tacit-teacher"
LOCATION = "us-central1"
MODEL = os.environ.get("TACIT_MODEL", "gemini-2.5-flash")
BUCKET = "gs://tacit-teacher-media/media/peel-vids"
#: The agent writes to out/, never into a reviewed directory. A human promotes a
#: checked copy into docs/peel-video/. See docs/runbook.md.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.environ.get("TACIT_OUT") or os.path.join(_ROOT, "out", "peel_seal")
os.makedirs(OUT, exist_ok=True)

#: V-id -> (filename, kind). V-ids are what citations use; IMG numbers are not
#: stable evidence identifiers and mean nothing to a reader.
CLIPS = [
    ("V1", "IMG_0764", "good"),
    ("V2", "IMG_0766", "good"),
    ("V3", "IMG_0767", "good"),
    ("V4", "IMG_0774", "good"),
    ("V5", "IMG_0768", "bad"),
    ("V6", "IMG_0770", "bad"),
    ("V7", "IMG_0771", "bad"),
    ("V8", "IMG_0772", "bad"),
    ("V9", "IMG_0773", "bad"),
]

PRIVACY = ("Never describe identifying physical characteristics of any person "
           "(tattoos, jewellery, skin, hair, clothing). Describe hands only as "
           "hands.")

GOOD_PROMPT = f"""You are extracting a manual laboratory technique from video so a
robot can reproduce it. This clip shows CORRECT practice: removing a rubber
sealing mat from a deep-well plate.

Report only what you can actually see or hear. Where a value cannot be
determined from video, put it in cannot_determine with the reason — do not
estimate it. You cannot see force, torque or grip pressure; those always belong
in cannot_determine.

Quote the narration verbatim where it justifies a step. All timestamps MM:SS.
{PRIVACY}"""

BAD_PROMPT = f"""You are extracting a failure mode from video so a robot can
detect and avoid it. This clip shows an operator DELIBERATELY performing the
technique incorrectly: removing a rubber sealing mat from a deep-well plate.

Report the failure as the camera shows it. Blue dye is used so contamination is
visible — describe what is visibly different from a correct run, and when.

Separate what you SAW from what the operator SAID. Quote narration verbatim.
All timestamps MM:SS.
{PRIVACY}"""

GOOD_SCHEMA = {
    "type": "object",
    "properties": {
        "steps": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "order": {"type": "integer"},
                "action": {"type": "string"},
                "start": {"type": "string"},
                "end": {"type": "string"},
                "narration_quote": {"type": "string"},
            },
            "required": ["order", "action", "start", "end"]}},
        "geometry": {
            "type": "object",
            "properties": {
                "grip_location": {"type": "string"},
                "peel_direction": {"type": "string"},
                "peel_angle_estimate_deg": {"type": "string"},
                "plate_stabilised_how": {"type": "string"},
                "mat_disposal": {"type": "string"},
            },
            "required": ["grip_location", "peel_direction", "plate_stabilised_how"]},
        "timing": {
            "type": "object",
            "properties": {
                "total_peel_seconds": {"type": "string"},
                "pace": {"type": "string"},
                "pauses": {"type": "string"},
            },
            "required": ["total_peel_seconds", "pace"]},
        "verification": {"type": "array", "items": {"type": "string"}},
        "cannot_determine": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["steps", "geometry", "timing", "cannot_determine"],
}

BAD_SCHEMA = {
    "type": "object",
    "properties": {
        "failure_name": {"type": "string"},
        "what_was_done_wrong": {"type": "string"},
        "visible_symptom": {"type": "string"},
        "symptom_timestamp": {"type": "string"},
        "narrated_explanation": {"type": "string"},
        "stated_correct_alternative": {"type": "string"},
        "detectable_by_camera": {"type": "boolean"},
        "cannot_determine": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["failure_name", "what_was_done_wrong", "visible_symptom",
                 "symptom_timestamp", "detectable_by_camera", "cannot_determine"],
}


def token():
    return subprocess.check_output(
        ["gcloud", "auth", "print-access-token"], text=True).strip()


def call(parts, schema, tok):
    url = (f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT}"
           f"/locations/{LOCATION}/publishers/google/models/{MODEL}:generateContent")
    body = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {
            "temperature": 0,
            "responseMimeType": "application/json",
            "responseSchema": schema,
        },
    }
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {tok}",
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            d = json.load(r)
    except urllib.error.HTTPError as e:
        return {"_error": f"{e.code} {e.read().decode()[:300]}"}
    try:
        return json.loads(d["candidates"][0]["content"]["parts"][0]["text"])
    except Exception:
        return {"_error": f"unexpected response: {json.dumps(d)[:300]}"}


def main():
    tok = token()
    results = {}
    for vid, img, kind in CLIPS:
        prompt = GOOD_PROMPT if kind == "good" else BAD_PROMPT
        schema = GOOD_SCHEMA if kind == "good" else BAD_SCHEMA
        print(f"  {vid} ({img}, {kind}) ...", flush=True)
        parts = [
            {"fileData": {"fileUri": f"{BUCKET}/{img}.MOV",
                          "mimeType": "video/quicktime"}},
            {"text": prompt},
        ]
        out = call(parts, schema, tok)
        if "_error" in out:
            print(f"      ERROR: {out['_error']}", flush=True)
        results[vid] = {"clip": img, "kind": kind, "data": out}

    path = os.path.join(OUT, "observed.json")
    with open(path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nwrote {path}")
    return results


if __name__ == "__main__":
    main()
