#!/usr/bin/env python3
"""
extract_skill.py — pull the skill text a run actually loaded, out of its log.

  python3 extract_skill.py session.jsonl                 # report what it finds
  python3 extract_skill.py session.jsonl -o SKILL_run_i.md

The skill file self-updates on `paperclip update` and `paperclip login`, so the
copy on disk is not the copy any past run used. The session log is: the result
of the `paperclip skill` call is the verbatim text that entered that run's
context. This pulls it back out.

Structural only — no interpretation. Finds tool calls whose command contains
`paperclip skill` (or the Skill tool), and prints/writes their result verbatim.
"""

import argparse, json, sys


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


def result_index(events):
    idx = {}
    for d in events:
        m = d.get("message")
        if not isinstance(m, dict) or m.get("role") != "user":
            continue
        c = m.get("content")
        if not isinstance(c, list):
            continue
        for b in c:
            if isinstance(b, dict) and b.get("type") == "tool_result":
                cc = b.get("content")
                txt = ("".join(x.get("text", "") for x in cc
                               if isinstance(x, dict) and x.get("type") == "text")
                       if isinstance(cc, list) else (cc or ""))
                idx[b.get("tool_use_id")] = txt
    return idx


def skill_loads(path):
    ev = load(path)
    idx = result_index(ev)
    hits, n = [], 0
    for d in ev:
        m = d.get("message")
        if not isinstance(m, dict) or m.get("role") != "assistant":
            continue
        c = m.get("content")
        if not isinstance(c, list):
            continue
        for b in c:
            if not (isinstance(b, dict) and b.get("type") == "tool_use"):
                continue
            n += 1
            cmd = (b.get("input") or {}).get("command", "") or ""
            if b.get("name") == "Skill" or "paperclip skill" in cmd:
                hits.append((n, b.get("name"), " ".join(cmd.split()),
                             idx.get(b.get("id"), "")))
    return hits


def main():
    ap = argparse.ArgumentParser(description="Extract loaded skill text from a session log.")
    ap.add_argument("session")
    ap.add_argument("-o", "--out", help="write the longest skill text to this file")
    args = ap.parse_args()

    hits = skill_loads(args.session)
    if not hits:
        print("no skill-loading call found in", args.session, file=sys.stderr)
        return 1

    for n, name, cmd, txt in hits:
        print("call %-3d [%-6s] %-24s %6d chars" % (n, name, cmd[:24], len(txt)))

    if args.out:
        n, name, cmd, txt = max(hits, key=lambda h: len(h[3]))
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(txt)
        print("\nwrote %s  (%d chars, from call %d)" % (args.out, len(txt), n))
    return 0


if __name__ == "__main__":
    sys.exit(main())
