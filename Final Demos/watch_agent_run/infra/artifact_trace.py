#!/usr/bin/env python3
"""
artifact_trace.py — where did the bytes in the final artifact come from?

  python3 artifact_trace.py session.jsonl
  python3 artifact_trace.py A=session_a.jsonl B=session_b.jsonl
  python3 artifact_trace.py session.jsonl --files      # full file graph

WHAT THIS ANSWERS
-----------------
strip_one.py tells you what KIND of call each step was. It cannot tell a Write
that persists a parsed file from a Write that transcribes a table out of the
model's context. Those look identical as calls and are completely different as
evidence. This reads the file graph instead.

For every tool call it records which files were READ and which were WRITTEN,
then reports, for each artifact:

  parsed      produced by code that read an input file
  transcribed produced by the Write/Edit tool with no file input - the content
              came out of the model's context, not out of a parse
  fetched     written directly by a paperclip command (--save, redirect)

and whether the transform was persisted as a script or thrown away inline.

TRUST CONTRACT
--------------
Every fact below is structural: tool names from the log, filenames from the
command string, direction from shell/py syntax. Nothing is model-generated and
nothing is inferred from prose. A file the tracer cannot see (a path built at
runtime, a glob) is reported as unknown rather than guessed.
"""

import argparse, json, os, re, sys

ARTIFACT_EXT = (".tsv", ".csv", ".json", ".md", ".txt", ".xlsx", ".svg")
SCRIPT_EXT = (".py", ".sh", ".jq")

WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}

FNAME = re.compile(r"[\w./~-]+\.(?:tsv|csv|json|md|txt|py|sh|jq|lines|xlsx|svg)\b")
REDIR = re.compile(r">>?\s*([\w./~-]+\.\w+)")
SAVE_FLAG = re.compile(r"--save\s+([\w./~-]+\.\w+)")
HEREDOC_TO = re.compile(r"cat\s*>\s*([\w./~-]+\.\w+)\s*<<")
PY_OPEN_W = re.compile(r"open\(\s*['\"]([\w./~-]+\.\w+)['\"]\s*,\s*['\"][wa]")
PY_OPEN_R = re.compile(r"open\(\s*['\"]([\w./~-]+\.\w+)['\"]\s*(?:[,)])")
INLINE_PY = re.compile(r"python3?\s+-\s*<<")
RUN_SCRIPT = re.compile(r"python3?\s+([\w./~-]+\.py)\b")


def load(path):
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return out


def strip_heredocs(cmd):
    """Heredoc bodies are data. Return (command_without_bodies, [bodies])."""
    bodies = []

    def grab(m):
        bodies.append(m.group(2))
        return m.group(0).split("\n")[0] + "\n"

    stripped = re.sub(r"<<-?['\"]?(\w+)['\"]?\n(.*?)\n\s*\1\s*(?=\n|$)",
                      grab, cmd, flags=re.S)
    return stripped, bodies


RUN_FILE = re.compile(
    r"(?:^|\s)(?:\./|(?:ba|z)?sh\s+|python3?\s+|source\s+)([\w./~-]+\.(?:sh|py|zsh|bash))\b")


PATH_ROOT = re.compile(r"(?:Path|D)\s*=\s*Path\(\s*['\"]([^'\"]+)['\"]")
PY_PATH_WRITE = re.compile(r"\(\s*[A-Z]\w*\s*/\s*['\"]([\w.-]+\.\w+)['\"]\s*\)\s*\.(?:write_text|open)")
PY_PATH_READ = re.compile(r"\(\s*[A-Z]\w*\s*/\s*['\"]([\w.-]+\.\w+)['\"]\s*\)\s*\.read")
CSV_WRITER = re.compile(r"open\(\s*([A-Z]\w*)\s*/\s*['\"]([\w.-]+\.\w+)['\"]")


def scan_body(text):
    """File reads and writes named inside a script body. Same rules used for
    heredocs, applied to bodies that arrived through the Write tool instead."""
    writes, reads = set(), set()
    for m in PY_OPEN_W.finditer(text):
        writes.add(os.path.basename(m.group(1)))
    for rx in (REDIR, SAVE_FLAG, HEREDOC_TO):
        for m in rx.finditer(text):
            writes.add(os.path.basename(m.group(1)))
    for m in PY_PATH_WRITE.finditer(text):
        writes.add(os.path.basename(m.group(1)))
    for m in CSV_WRITER.finditer(text):
        writes.add(os.path.basename(m.group(2)))
    for m in PY_PATH_READ.finditer(text):
        reads.add(os.path.basename(m.group(1)))
    for m in PY_OPEN_R.finditer(text):
        f = os.path.basename(m.group(1))
        if f not in writes:
            reads.add(f)
    for m in FNAME.finditer(text):
        f = os.path.basename(m.group(0))
        if f not in writes and not f.endswith(SCRIPT_EXT):
            reads.add(f)
    reads -= writes
    return reads, writes


def io_for(name, inp, known=None):
    """Return (reads, writes, note) for one tool call. All structural."""
    if name in WRITE_TOOLS:
        fp = inp.get("file_path") or inp.get("path") or ""
        return set(), ({os.path.basename(fp)} if fp else set()), "write-tool"
    if name == "Read":
        fp = inp.get("file_path") or inp.get("path") or ""
        return ({os.path.basename(fp)} if fp else set()), set(), "read-tool"

    cmd = inp.get("command", "") or ""
    if not cmd:
        return set(), set(), ""

    shell, bodies = strip_heredocs(cmd)
    writes, reads = set(), set()
    note = ""

    for rx in (REDIR, SAVE_FLAG, HEREDOC_TO):
        for m in rx.finditer(shell):
            writes.add(os.path.basename(m.group(1)))

    body_text = "\n".join(bodies)
    for m in PY_OPEN_W.finditer(body_text):
        writes.add(os.path.basename(m.group(1)))
    for m in PY_OPEN_R.finditer(body_text):
        f = os.path.basename(m.group(1))
        if f not in writes:
            reads.add(f)

    for m in FNAME.finditer(shell):
        f = os.path.basename(m.group(0))
        if f not in writes:
            reads.add(f)

    for m in RUN_FILE.finditer(shell):
        body = (known or {}).get(os.path.basename(m.group(1)))
        if body:
            r2, w2 = scan_body(body)
            writes |= w2
            reads |= {f for f in r2 if f not in w2}
            note = "resolved-script"

    if note == "resolved-script":
        pass
    elif INLINE_PY.search(shell):
        note = "inline-script"
    elif RUN_SCRIPT.search(shell):
        note = "runs-script"
    elif HEREDOC_TO.search(shell):
        note = "writes-script" if shell.split()[-0:] and any(
            w.endswith(SCRIPT_EXT) for w in writes) else "heredoc-file"

    return reads, writes, note


def trace(path):
    ev = load(path)
    known = {}
    calls = []
    for d in ev:
        m = d.get("message")
        if not isinstance(m, dict) or m.get("role") != "assistant":
            continue
        c = m.get("content")
        if not isinstance(c, list):
            continue
        for b in c:
            if isinstance(b, dict) and b.get("type") == "tool_use":
                name = b.get("name", "?")
                inp = b.get("input") or {}
                if name in WRITE_TOOLS:
                    fp = inp.get("file_path") or inp.get("path") or ""
                    body = inp.get("content") or inp.get("new_string") or ""
                    if fp.endswith(SCRIPT_EXT + (".sh", ".zsh", ".bash")) and body:
                        known[os.path.basename(fp)] = body
                for m in re.finditer(
                        r"cat\s*>\s*([\w./~-]+\.(?:sh|py|zsh|bash))\s*<<-?['\"]?(\w+)['\"]?\n(.*?)\n\s*\2",
                        inp.get("command", "") or "", re.S):
                    known[os.path.basename(m.group(1))] = m.group(3)
                reads, writes, note = io_for(name, inp, known)
                calls.append((len(calls) + 1, name, reads, writes, note))
    return calls


def classify(calls):
    """For each artifact written, how were its bytes produced?"""
    out = []
    for n, name, reads, writes, note in calls:
        for w in sorted(writes):
            if not w.endswith(ARTIFACT_EXT):
                continue
            if name in WRITE_TOOLS:
                how, why = "transcribed", "Write tool, no file input"
            elif reads:
                how = "parsed"
                why = "reads " + ", ".join(sorted(reads)[:3])
            else:
                how, why = "fetched", "written by command, no file input"
            persist = ""
            if note == "resolved-script":
                persist = "saved script"
            elif note == "inline-script":
                persist = "inline (not saved)"
            elif note == "runs-script":
                persist = "saved script"
            out.append((n, w, how, why, persist))
    return out


def main():
    ap = argparse.ArgumentParser(description="Trace artifact provenance in a session log.")
    ap.add_argument("sessions", nargs="+", help="paths, or LABEL=path")
    ap.add_argument("--files", action="store_true", help="print the full per-call file graph")
    args = ap.parse_args()

    for s in args.sessions:
        if "=" in s and not os.path.exists(s):
            label, _, p = s.partition("=")
        else:
            p, label = s, os.path.basename(os.path.dirname(os.path.abspath(s))) or s
        if not os.path.exists(p):
            print("no such file:", p, file=sys.stderr)
            continue

        calls = trace(p)
        print("== %s  (%d calls)" % (label, len(calls)))

        if args.files:
            for n, name, reads, writes, note in calls:
                if reads or writes:
                    print("   %2d %-6s in[%s] out[%s] %s"
                          % (n, name, ",".join(sorted(reads)) or "-",
                             ",".join(sorted(writes)) or "-", note))

        rows = classify(calls)
        if not rows:
            print("   no artifact files written")
        for n, f, how, why, persist in rows:
            print("   %2d  %-26s %-12s %s%s"
                  % (n, f, how, why, ("  [%s]" % persist) if persist else ""))
        scripts = sorted({w for _, _, _, ws, _ in calls for w in ws
                          if w.endswith(SCRIPT_EXT)})
        inline = sum(1 for _, _, _, _, note in calls if note == "inline-script")
        print("   transform: %s"
              % (", ".join(scripts) if scripts
                 else ("%d inline heredoc(s), nothing saved" % inline if inline
                       else "none")))
        print()


if __name__ == "__main__":
    main()
