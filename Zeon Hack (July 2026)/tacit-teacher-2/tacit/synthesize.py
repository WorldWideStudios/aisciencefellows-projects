#!/usr/bin/env python3
"""Merge the nine per-clip extractions into two documents.

This is the INTERPRETATION step — everything it emits is derived from
observed.json, and every claim must carry the V-id + timestamp that justifies
it. Disagreements between clips are reported as disagreements, not averaged
away: four estimates of the same angle spanning 45-90 degrees is a finding.
"""

import json
import os
import subprocess
import urllib.request
import urllib.error

PROJECT, LOCATION = "tacit-teacher", "us-central1"
MODEL = os.environ.get("TACIT_MODEL", "gemini-2.5-flash")
#: The agent writes to out/, never into a reviewed directory. A human promotes a
#: checked copy into docs/peel-video/. See docs/runbook.md.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HERE = os.environ.get("TACIT_OUT") or os.path.join(_ROOT, "out", "peel_seal")
os.makedirs(HERE, exist_ok=True)

PROMPT = """Below is structured data extracted from nine video clips of one
operator removing a rubber sealing mat from a 1 mL deep-well plate. V1-V4 show
correct practice. V5-V9 are deliberate errors.

Write TWO markdown documents, separated by a line containing only `---SPLIT---`.

DOCUMENT 1 — "How to remove a sealing mat"
An ordered procedure a robot could be programmed from. For each step give the
action, then the evidence in brackets: [V1@00:37-00:57]. Where clips agree,
cite them all. Include a "Geometry" and a "Timing" section with concrete values.

DOCUMENT 2 — "What not to do"
One section per failure mode. For each: what was done wrong, the visible
symptom and its timestamp, whether a camera could detect it, and the verbatim
quote if there is one.

Hard rules:
- EVERY factual claim carries a [V<n>@MM:SS] citation. No uncited claims.
- Where clips DISAGREE on a value, say so explicitly and give the range and
  each clip's figure. Do not average them.
- Anything the extraction put in cannot_determine goes in a closing
  "Not answerable from video" section. Do not fill these gaps with plausible
  numbers.
- Distinguish what was SEEN from what was SAID. Narration is a claim by the
  operator, not an observation.

DATA:
"""


def main():
    tok = os.environ.get("GCP_TOKEN") or subprocess.check_output(
        ["gcloud", "auth", "print-access-token"], text=True).strip()
    data = open(os.path.join(HERE, "observed.json")).read()

    url = (f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT}"
           f"/locations/{LOCATION}/publishers/google/models/{MODEL}:generateContent")
    body = {"contents": [{"role": "user",
                          "parts": [{"text": PROMPT + data}]}],
            "generationConfig": {"temperature": 0, "maxOutputTokens": 16384}}
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {tok}",
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        d = json.load(r)

    text = "".join(p.get("text", "")
                   for p in d["candidates"][0]["content"]["parts"])

    if "---SPLIT---" in text:
        howto, notdo = text.split("---SPLIT---", 1)
    else:
        howto, notdo = text, ""

    for name, body_ in (("HOW-TO.md", howto), ("WHAT-NOT-TO-DO.md", notdo)):
        p = os.path.join(HERE, name)
        with open(p, "w") as f:
            f.write(body_.strip() + "\n")
        print(f"wrote {p} ({len(body_.split())} words)")


if __name__ == "__main__":
    main()
