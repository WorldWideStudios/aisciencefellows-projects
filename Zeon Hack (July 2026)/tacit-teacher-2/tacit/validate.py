#!/usr/bin/env python3
"""Check that extracted knowledge is traceable back to where it came from.

The original rule: every parameter carries a `source`. A number with no source is
a guess, and guesses are the thing this project exists to remove — they are
indistinguishable from knowledge once they are sitting in a Python file as
`width_m=0.035`.

Video capture added a second rule, because a source is no longer just a source.
Two kinds now reach this file:

    Q<n>            an answer in 10-transcript.md   — a person said it
    V<n>@MM:SS      a moment in 15-observed.md      — a camera saw it

They are not interchangeable, and treating them as such reintroduces exactly the
failure this script exists to catch. A camera can see where a hand goes and how
long it takes. It cannot see force. So a grip width sourced to a video is a guess
again — a guess with a citation, which is worse than an obvious one.

    python tacit/validate.py                    # every session
    python tacit/validate.py tacit/sessions/x   # one session

Exits non-zero if anything is untraceable, so it can gate a commit.
"""

import glob
import os
import re
import sys

try:
    import yaml
except ImportError:
    sys.exit("needs pyyaml:  pip install pyyaml")

#: Sections whose leaf entries must each cite a source.
PARAMETER_SECTIONS = ("geometry", "force", "timing", "verification",
                      "failure_modes", "variation")

#: Q7 | V1 | V1@00:15 | V1@00:15-00:37
#: A bare V<n> cites a whole clip, which is right for claims about the clip as a
#: whole ("no pauses in any of the four"). A moment gets a timestamp.
SOURCE_RE = re.compile(r"^(Q\d+|V\d+(@\d{1,2}:\d{2}(-\d{1,2}:\d{2})?)?)$")

#: Sections where a video citation alone is not evidence. You cannot see newtons.
FORCE_SECTIONS = ("force",)

#: Values that honestly mean "we have not asked yet". A field left at one of
#: these is fine; a field with a real value needs a real source.
UNSPECIFIED = {None, "", "unknown", "tbd", "pending", "n/a"}


def _sources(node) -> list:
    """Source strings on this node. `source` may be a scalar or a list."""
    if not isinstance(node, dict):
        return []
    s = node.get("source")
    if s in (None, "", []):
        return []
    return [str(x).strip() for x in (s if isinstance(s, list) else [s])]


def _kind(src: str) -> str:
    """'Q' for transcript, 'V' for video, '?' for anything that does not parse."""
    return src[0] if SOURCE_RE.match(src) else "?"


def _cited(node) -> bool:
    """A dict is cited if it has a non-empty `source`, or every child is."""
    if isinstance(node, dict):
        if node.get("source"):
            return True
        children = [v for v in node.values() if isinstance(v, (dict, list))]
        return bool(children) and all(_cited(c) for c in children)
    if isinstance(node, list):
        return bool(node) and all(_cited(c) for c in node)
    return False


def _cited_nodes(node, out: list) -> None:
    """Collect every dict that carries its own `source`.

    Stops descending once a node is cited: an entry-level source covers the
    fields beneath it, which is how the schema is written.
    """
    if isinstance(node, dict):
        if node.get("source"):
            out.append(node)
            return
        for v in node.values():
            _cited_nodes(v, out)
    elif isinstance(node, list):
        for v in node:
            _cited_nodes(v, out)


def check_session(path: str) -> tuple:
    """Return (problems, source_counts). Empty problems means the session is sound."""
    problems = []
    counts = {"Q": 0, "V": 0}
    name = os.path.basename(path.rstrip("/"))

    for required in ("00-brief.md", "10-transcript.md", "20-extracted.yaml",
                     "30-outcome.md"):
        if not os.path.exists(os.path.join(path, required)):
            problems.append(f"{name}: missing {required}")

    extracted = os.path.join(path, "20-extracted.yaml")
    if not os.path.exists(extracted):
        return problems, counts

    with open(extracted) as f:
        data = yaml.safe_load(f) or {}

    for section in PARAMETER_SECTIONS:
        body = data.get(section)
        if not body:
            continue                      # empty is allowed; untraceable is not
        if not _cited(body):
            problems.append(
                f"{name}: '{section}' has a parameter with no `source` — it is a "
                f"guess, not knowledge")

        nodes = []
        _cited_nodes(body, nodes)
        for node in nodes:
            srcs = _sources(node)
            kinds = {_kind(s) for s in srcs}

            # 1. The citation has to be a citation.
            for s in srcs:
                if _kind(s) == "?":
                    problems.append(
                        f"{name}: '{section}' has source {s!r}, which is not a "
                        f"citation — expected Q<n> or V<n>@MM:SS")

            for k in kinds:
                if k in counts:
                    counts[k] += 1

            # 2. Force cannot come from a camera.
            if section in FORCE_SECTIONS and kinds and kinds <= {"V"}:
                label = node.get("stage") or node.get("parameter") or "entry"
                problems.append(
                    f"{name}: force/{label} cites video only ({', '.join(srcs)}) "
                    f"— you cannot see newtons. Ask, or leave it in `unknowns`")

            # 3. A failure's symptom can be filmed. Its recovery cannot.
            if section == "failure_modes":
                for field in ("recovery", "max_retries"):
                    val = node.get(field)
                    if isinstance(val, str):
                        val_norm = val.strip().lower()
                    else:
                        val_norm = val
                    if val_norm in UNSPECIFIED:
                        continue          # honest gap, not a violation
                    if "Q" not in kinds:
                        problems.append(
                            f"{name}: failure_mode "
                            f"{node.get('name', '?')!r} specifies {field}="
                            f"{val!r} but cites video only — nobody filmed what "
                            f"to do about it. Needs a Q source")

    if not data.get("unknowns"):
        problems.append(
            f"{name}: `unknowns` is empty. On a real interview that means nobody "
            f"pushed hard enough — record what you could not extract")

    # A failure you cannot detect is one you cannot recover from.
    if data.get("failure_modes") and not data.get("verification"):
        problems.append(
            f"{name}: has failure_modes but no verification — the robot cannot "
            f"notice these failures, so the recoveries are unreachable")

    # A video citation that points at nothing is not provenance.
    if counts["V"] and not os.path.exists(os.path.join(path, "15-observed.md")):
        problems.append(
            f"{name}: cites video sources but has no 15-observed.md — the "
            f"citations point at nothing")

    return problems, counts


def main(argv) -> int:
    targets = argv[1:] or sorted(
        d for d in glob.glob("tacit/sessions/*") if os.path.isdir(d))
    targets = [t for t in targets if not os.path.basename(t).startswith("_")]

    if not targets:
        print("no sessions yet (templates in tacit/sessions/_TEMPLATE are skipped)")
        return 0

    problems, total = [], {"Q": 0, "V": 0}
    for t in targets:
        p, c = check_session(t)
        problems.extend(p)
        for k in total:
            total[k] += c[k]

    if problems:
        print(f"{len(problems)} problem(s):\n")
        for p in problems:
            print(f"  - {p}")
        return 1

    # Say what the sources actually are. "Traces to a transcript" was a lie the
    # moment a session cited only video, and a validator that overstates its own
    # result is the same bug it exists to catch.
    print(f"{len(targets)} session(s) OK — "
          f"{total['Q']} transcript-cited, {total['V']} video-cited")
    if total["Q"] == 0 and total["V"]:
        print("  note: nothing here was said by a person. Every parameter rests "
              "on video, so force and recovery are necessarily still open.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
